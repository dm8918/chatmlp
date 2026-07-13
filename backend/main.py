import json
import logging
import os
import re

from fastapi import FastAPI, Request
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

# On-behalf-of-user auth: the Databricks App reverse proxy authenticates the end
# user and forwards their OAuth token in the "x-forwarded-access-token" header.
# The backend builds a per-request WorkspaceClient with THAT token, so the agent
# runs with the user's own permissions. Locally (Replit) the header is absent, so
# the chat returns an explicit offline message (no demo data).
USER_TOKEN_HEADER = "x-forwarded-access-token"
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
    "El agente no generó una respuesta final",
    "No se encontró una respuesta final del agente",
)

_NO_FINAL_ANSWER = "El agente no generó una respuesta final."

# The Databricks SDK includes the full request log — with the
# "Authorization: Bearer <user token>" header and any JWT — in its exception
# messages. Never surface that to the UI trace. Redact both the Bearer header and
# any standalone JWT (eyJ...) before displaying an error.
_BEARER_RE = re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]+", re.IGNORECASE)
_JWT_RE = re.compile(r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+")


def redact_secrets(text) -> str:
    text = _BEARER_RE.sub(r"\1***", str(text))
    return _JWT_RE.sub("***", text)


def is_error_message(msg: dict) -> bool:
    return msg.get("role") == "assistant" and str(msg.get("content", "")).startswith(
        _ERROR_PREFIXES
    )


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health(request: Request):
    return {
        "status": "ok",
        "auth": "on-behalf-of-user",
        "user_token_present": bool(request.headers.get(USER_TOKEN_HEADER)),
    }


@app.post("/api/chat")
def chat(req: ChatRequest, request: Request):
    endpoint = agent_endpoint()
    incoming = [m.model_dump() for m in req.messages]
    messages = [m for m in incoming if not is_error_message(m)]

    trace: list[str] = [f"0. Endpoint destino: {endpoint} (vía SDK /invocations)"]
    dropped = len(incoming) - len(messages)
    if dropped:
        trace.append(f"   ({dropped} mensaje(s) de error previos excluidos del contexto)")

    user_access_token = request.headers.get(USER_TOKEN_HEADER)
    if not user_access_token:
        trace.append(
            f"1. Falta el header '{USER_TOKEN_HEADER}' (usuario no autenticado)"
        )
        logger.warning("Sin %s: petición no autenticada por Databricks Apps", USER_TOKEN_HEADER)
        return {
            "role": "assistant",
            "type": "text",
            "content": (
                "Sin conexión al agente de Databricks. Cerebro responde con datos "
                "reales al desplegarse como Databricks App, que autentica al usuario "
                "y reenvía su token en el header 'x-forwarded-access-token'."
            ),
            "trace": trace,
            "isError": True,
        }

    trace.append("1. Token de usuario recibido (x-forwarded-access-token)")

    try:
        client = init_workspace_client(user_access_token)
    except Exception as e:  # noqa: BLE001 - surface auth/config errors to the UI
        logger.exception("No se pudo inicializar el WorkspaceClient del usuario")
        msg = redact_secrets(e)
        trace.append(f"   ERROR al inicializar el cliente del usuario: {msg}")
        return {
            "role": "assistant",
            "type": "text",
            "content": f"Error consultando el agente ({endpoint}): {msg}",
            "trace": trace,
            "isError": True,
        }

    trace.append("   Cliente Databricks inicializado con la identidad del usuario")

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
        msg = redact_secrets(e)
        trace.append(f"3. ERROR al invocar el endpoint: {msg}")
        return {
            "role": "assistant",
            "type": "text",
            "content": f"Error consultando el agente ({endpoint}): {msg}",
            "trace": trace,
            "isError": True,
        }

    raw = (
        json.dumps(response, ensure_ascii=False, indent=2)
        if isinstance(response, dict)
        else str(response)
    )
    trace.append(f"3. Respuesta recibida (completa):\n{raw}")

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

    no_final = answer == _NO_FINAL_ANSWER
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
