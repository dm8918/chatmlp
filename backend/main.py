import json
import logging
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.functions.call_agent_functions import (
    call_agent,
    clean_conversation,
    get_final_message,
    init_workspace_client,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chatmlp")

app = FastAPI(title="ChatMLP API")

# On a Databricks App the service principal credentials are injected
# automatically and the Databricks SDK resolves them with no extra config.
# Locally (Replit) there are intentionally no credentials, so the client fails
# to initialise and the chat returns an explicit offline message (no demo data).
DEFAULT_AGENT_ENDPOINT = "mas-c7a80bc8-endpoint"


def agent_endpoint() -> str:
    return os.environ.get("DATABRICKS_AGENT_ENDPOINT", DEFAULT_AGENT_ENDPOINT)


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


# Error messages produced by this backend / the frontend. They must never be
# echoed back to the agent as conversation history (they pollute the context).
_ERROR_PREFIXES = (
    "Error consultando el agente",
    "No se pudo obtener respuesta",
    "Sin conexión al agente de Databricks",
    "El agente no devolvió",
    "No se encontró una respuesta final del agente",
)


def is_error_message(msg: dict) -> bool:
    return msg.get("role") == "assistant" and str(msg.get("content", "")).startswith(
        _ERROR_PREFIXES
    )


# ---------------------------------------------------------------------------
# WorkspaceClient cache
# ---------------------------------------------------------------------------
# Cache only a successfully created client. A transient failure to initialise
# must NOT be cached, or the app would pin itself into the offline state until
# a restart.
_client = None


def get_workspace_client():
    global _client
    if _client is None:
        _client = init_workspace_client()
    return _client


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "credentials_configured": get_workspace_client() is not None,
    }


@app.post("/api/chat")
def chat(req: ChatRequest):
    endpoint = agent_endpoint()
    incoming = [m.model_dump() for m in req.messages]
    messages = [m for m in incoming if not is_error_message(m)]

    trace: list[str] = [f"0. Endpoint destino: {endpoint} (vía SDK /invocations)"]
    dropped = len(incoming) - len(messages)
    if dropped:
        trace.append(f"   ({dropped} mensaje(s) de error previos excluidos del contexto)")

    client = get_workspace_client()
    if client is None:
        trace.append("1. Cliente Databricks NO inicializado (sin credenciales)")
        logger.warning("WorkspaceClient no disponible: sin credenciales Databricks")
        return {
            "role": "assistant",
            "type": "text",
            "content": (
                "Sin conexión al agente de Databricks. Cerebro responde con datos "
                "reales al desplegarse como Databricks App (autenticación automática "
                "del service principal)."
            ),
            "trace": trace,
            "isError": True,
        }

    trace.append("1. Cliente Databricks inicializado (SDK, auth automática)")

    clean = clean_conversation(messages)
    trace.append(
        f"2. POST /serving-endpoints/{endpoint}/invocations "
        f"({len(clean)} mensaje(s))"
    )
    trace.append(f"   Enviado: {json.dumps({'input': clean}, ensure_ascii=False)[:600]}")

    try:
        response = call_agent(client, endpoint, messages)
    except Exception as e:  # noqa: BLE001 - surface any SDK/HTTP error to the UI
        logger.exception("Error consultando el endpoint %s", endpoint)
        trace.append(f"3. ERROR al invocar el endpoint: {e}")
        return {
            "role": "assistant",
            "type": "text",
            "content": f"Error consultando el agente ({endpoint}): {e}",
            "trace": trace,
            "isError": True,
        }

    if isinstance(response, dict) and response.get("error"):
        err = response["error"]
        trace.append(f"3. ERROR devuelto por el endpoint: {json.dumps(err, ensure_ascii=False)[:300]}")
        return {
            "role": "assistant",
            "type": "text",
            "content": f"Error consultando el agente ({endpoint}): {err}",
            "trace": trace,
            "isError": True,
        }

    raw = json.dumps(response, ensure_ascii=False) if isinstance(response, dict) else str(response)
    trace.append(f"3. Respuesta recibida: {raw[:1500]}")

    output = response.get("output", []) if isinstance(response, dict) else []
    assistant_msgs = sum(
        1
        for it in output
        if isinstance(it, dict) and it.get("type") == "message" and it.get("role") == "assistant"
    )
    fn_calls = sum(
        1 for it in output if isinstance(it, dict) and it.get("type") == "function_call"
    )
    trace.append(
        f"4. Análisis: {len(output)} items, {fn_calls} function_call, "
        f"{assistant_msgs} mensajes assistant"
    )

    answer = get_final_message(response)
    logger.info(
        "invocations parsed: endpoint=%s items=%s function_calls=%s assistant_msgs=%s",
        endpoint,
        len(output),
        fn_calls,
        assistant_msgs,
    )

    no_final = answer == "No se encontró una respuesta final del agente."
    trace.append(
        f"5. Respuesta final: {answer[:200]}" + ("…" if len(answer) > 200 else "")
    )
    return {
        "role": "assistant",
        "type": "text",
        "content": answer,
        "trace": trace,
        "isError": no_final,
    }


# NOTE: the frontend must be built (`npm run build --prefix frontend`) and the
# resulting `frontend/dist` folder must be included in what is uploaded to the
# App. Databricks Apps only run uvicorn; they do NOT build the front-end.
_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_DIST):
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="static")
else:
    @app.get("/")
    def _missing_frontend():
        return {
            "detail": (
                "Frontend build not found. Run 'npm run build --prefix frontend' "
                "and make sure the 'frontend/dist' folder is deployed alongside "
                "the backend. The API itself is running: try /api/health."
            )
        }
