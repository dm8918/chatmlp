import json
import logging
import os

import requests
from databricks.sdk import WorkspaceClient
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Name of the Databricks serving endpoint. The workspace host is resolved
# automatically by the SDK: on a Databricks App via the service principal's
# OAuth, and locally via DATABRICKS_HOST / DATABRICKS_TOKEN.
ENDPOINT_NAME = "mas-c7a80bc8-endpoint"

logger = logging.getLogger("chatmlp")

app = FastAPI(title="ChatMLP API")


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


def _extract_answer(data: dict) -> str:
    """Extract the assistant text from the possible agent response shapes."""
    # Responses API shape: {"output": [{"content": [{"type": "output_text", "text": ...}]}]}
    if isinstance(data.get("output"), list):
        parts = []
        for output in data["output"]:
            for content in output.get("content", []) if isinstance(output, dict) else []:
                if isinstance(content, dict) and content.get("text"):
                    parts.append(content["text"])
        if parts:
            return " ".join(parts)

    # ChatAgent shape: {"messages": [..., {"role": "assistant", "content": ...}]}
    if isinstance(data.get("messages"), list):
        for msg in reversed(data["messages"]):
            if isinstance(msg, dict) and msg.get("role") == "assistant" and msg.get("content"):
                return str(msg["content"])

    # Chat completions shape: {"choices": [{"message": {"content": ...}}]}
    if isinstance(data.get("choices"), list) and data["choices"]:
        message = data["choices"][0].get("message", {})
        if message.get("content"):
            return str(message["content"])

    raise RuntimeError(
        f"Formato de respuesta no reconocido: {json.dumps(data)[:400]}"
    )


class NoCredentialsError(Exception):
    """Raised when no Databricks credentials are available (local/offline)."""


def query_agent(messages: list[dict], trace: list[str]) -> str:
    """POST directly to the serving endpoint's /invocations URL.

    Auth is handled by the Databricks SDK (OAuth on a Databricks App, env vars
    locally). The OAuth token expires (~1h), so credentials are resolved
    per-request and never cached.

    Agent Bricks (mas-*) endpoints expect the Responses API schema
    ``{"input": [...]}``; other agents expect ``{"messages": [...]}``. We try
    ``input`` first and fall back to ``messages`` if the endpoint rejects it.

    ``trace`` is mutated with a human-readable log of each stage so the
    front-end can show what was sent and received.
    """
    try:
        w = WorkspaceClient()
        auth_headers = w.config.authenticate()
        trace.append(
            f"1. Autenticación OK (método: {w.config.auth_type}, host: {w.config.host})"
        )
    except Exception as e:
        trace.append(f"1. Autenticación FALLÓ: {str(e)[:300]}")
        raise NoCredentialsError(str(e)) from e

    url = f"{w.config.host.rstrip('/')}/serving-endpoints/{ENDPOINT_NAME}/invocations"
    headers = {**auth_headers, "Content-Type": "application/json"}

    last_error = None
    for schema, payload in (("input", {"input": messages}), ("messages", {"messages": messages})):
        body = json.dumps(payload, ensure_ascii=False)
        trace.append(f"2. POST {url}")
        trace.append(f"   Enviado (esquema '{schema}'): {body[:600]}")
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        trace.append(
            f"3. Respuesta HTTP {resp.status_code} en {resp.elapsed.total_seconds():.1f}s"
        )
        trace.append(f"   Recibido: {resp.text[:600]}")
        if resp.status_code == 200:
            try:
                data = resp.json()
            except ValueError:
                trace.append("4. ERROR: el cuerpo no es JSON válido")
                raise RuntimeError(
                    f"El endpoint no devolvió JSON (HTTP {resp.status_code}): "
                    f"{resp.text[:400]}"
                )
            answer = _extract_answer(data)
            trace.append("4. Texto extraído correctamente")
            return answer
        last_error = f"HTTP {resp.status_code}: {resp.text[:400]}"
        # Only retry with the alternate schema on client-side schema errors.
        if resp.status_code not in (400, 422):
            break
        if schema == "input":
            trace.append(
                f"   Esquema '{schema}' rechazado; reintentando con el otro esquema…"
            )
    trace.append("4. ERROR: el endpoint no aceptó la solicitud")
    raise RuntimeError(last_error)


# API

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat")
def chat(req: ChatRequest):
    payload = [m.model_dump() for m in req.messages]
    trace: list[str] = [f"0. Endpoint destino: {ENDPOINT_NAME}"]

    try:
        answer = query_agent(payload, trace)
        return {"role": "assistant", "type": "text", "content": answer, "trace": trace}
    except NoCredentialsError as e:
        # No Databricks credentials (e.g. running locally on Replit). The agent
        # only answers when deployed as a Databricks App, where OAuth is
        # automatic. This is NOT a demo response — it is an explicit offline state.
        logger.warning("Sin credenciales Databricks: %s", e)
        return {
            "role": "assistant",
            "type": "text",
            "content": (
                "Sin conexión al agente de Databricks. Cerebro responde con datos "
                "reales al desplegarse como Databricks App (autenticación automática "
                "del service principal)."
            ),
            "trace": trace,
        }
    except Exception as e:
        # Surface the real error (HTTP status + body from the endpoint) instead
        # of an opaque 500, so problems like missing permissions are visible.
        logger.exception("Error consultando el endpoint %s", ENDPOINT_NAME)
        return {
            "role": "assistant",
            "type": "text",
            "content": f"Error consultando el agente ({ENDPOINT_NAME}): {e}",
            "trace": trace,
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
