import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Name of the Databricks serving endpoint (used as the model id). The workspace
# host / base URL is resolved automatically by the SDK on a Databricks App.
ENDPOINT_NAME = "mas-f80ab72d-endpoint"

app = FastAPI(title="ChatMLP API")


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


_client = None


def get_client():
    """Return an OpenAI client pointed at the Databricks serving endpoint.

    On a Databricks App, auth is automatic via the service principal's OAuth
    (M2M). We use the SDK's ``get_open_ai_client`` helper, which refreshes the
    short-lived OAuth token automatically on every request, so a long-running
    App does not break when the initial token expires.

    The successful client is cached, but failures are NOT cached: a transient
    error on startup must not pin the app into demo mode forever. On Replit /
    local there are usually no credentials, so this returns None and the API
    answers in demo mode.
    """
    global _client
    if _client is not None:
        return _client
    try:
        from databricks.sdk import WorkspaceClient

        w = WorkspaceClient()
        # Fail fast if there are no usable credentials (local/demo).
        w.config.authenticate()
        _client = w.serving_endpoints.get_open_ai_client()
        return _client
    except Exception:
        return None


def demo_reply(question: str) -> dict:
    """Simulated response so the front works without a Databricks connection."""
    q = question.lower()
    if "caex" in q or "utiliz" in q:
        return {
            "role": "assistant",
            "type": "structured",
            "content": {
                "badge": "Datos estructurados + Asesor de operaciones",
                "title": "Utilización CAEX – Flota productiva (demo)",
                "subtitle": "Utilización global de flota productiva: 86,1%",
                "table": {
                    "columns": ["CAEX", "Utilización"],
                    "rows": [
                        ["EX324", "98,0%"],
                        ["EX371", "97,4%"],
                        ["EX363", "96,7%"],
                        ["EX364", "92,5%"],
                        ["CA101", "91,6%"],
                        ["CA111", "90,7%"],
                    ],
                },
            },
        }
    return {
        "role": "assistant",
        "type": "text",
        "content": (
            "Modo demo: sin conexión a Databricks. Al desplegar como Databricks "
            f'App responderé con datos reales. Tu pregunta fue: "{question}"'
        ),
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "demo": get_client() is None}


@app.post("/api/chat")
def chat(req: ChatRequest):
    question = req.messages[-1].content if req.messages else ""
    client = get_client()

    if client is None:
        return demo_reply(question)

    try:
        response = client.responses.create(
            model=ENDPOINT_NAME,
            input=[m.model_dump() for m in req.messages],
        )
        answer = " ".join(
            getattr(content, "text", "")
            for output in response.output
            for content in getattr(output, "content", [])
        )
        return {"role": "assistant", "type": "text", "content": answer}
    except Exception as exc:
        return {
            "role": "assistant",
            "type": "text",
            "content": f"Error consultando el agente: {exc}",
        }


# Serve the built React app in production (e.g. on a Databricks App).
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
