from openai import OpenAI
from databricks.sdk import WorkspaceClient
import os
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Name of the Databricks serving endpoint (used as the model id). The workspace
# host / base URL is resolved automatically by the SDK: on a Databricks App via
# the service principal's OAuth, and locally via DATABRICKS_HOST / DATABRICKS_TOKEN.

logger = logging.getLogger("chatmlp")

app = FastAPI(title="ChatMLP API")

ENDPOINT_NAME = "mas-c7a80bc8-endpoint"


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


def get_client():
    # WorkspaceClient resuelve host/credenciales solo (OAuth en App, env vars local).
    # El token OAuth expira (~1h), por eso se crea per-request y no se cachea.
    w = WorkspaceClient()

    headers = w.config.authenticate()
    token = headers["Authorization"].replace("Bearer ", "")

    client = OpenAI(
        api_key=token,
        base_url=f"{w.config.host}/serving-endpoints",  # derivado, no hardcodeado
    )
    return client


def get_response(client, input_msg):
    response = client.responses.create(
        model=ENDPOINT_NAME,
        input=input_msg,
    )
    return response  # FIX: faltaba el return


# API

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat")
def chat(req: ChatRequest):
    try:
        client = get_client()
    except Exception as e:
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
        }

    response = get_response(client, [m.model_dump() for m in req.messages])

    answer = " ".join(
        getattr(content, "text", "")
        for output in response.output
        for content in getattr(output, "content", [])
    )
    return {"role": "assistant", "type": "text", "content": answer}


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


