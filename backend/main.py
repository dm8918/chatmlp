import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Name of the Databricks serving endpoint (used as the model id). The workspace
# host / base URL is resolved automatically by the SDK: on a Databricks App via
# the service principal's OAuth, and locally via DATABRICKS_HOST / DATABRICKS_TOKEN.
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
    (M2M). Locally, the Databricks SDK reads ``DATABRICKS_HOST`` and
    ``DATABRICKS_TOKEN`` from the environment. In both cases we use the SDK's
    ``get_open_ai_client`` helper, which refreshes the short-lived OAuth token
    automatically on every request so a long-running App does not break when the
    initial token expires.

    The successful client is cached; failures are NOT cached so a transient
    startup error does not pin the app into a broken state forever.
    """
    global _client
    if _client is not None:
        return _client
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()
    # Fail fast (raises) if there are no usable credentials.
    w.config.authenticate()
    _client = w.serving_endpoints.get_open_ai_client()
    return _client


@app.get("/api/health")
def health():
    try:
        get_client()
        return {"status": "ok", "connected": True}
    except Exception as exc:
        return {"status": "ok", "connected": False, "detail": str(exc)}


@app.post("/api/chat")
def chat(req: ChatRequest):
    client = get_client()
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
