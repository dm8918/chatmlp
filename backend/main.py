import os
from functools import lru_cache

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ENDPOINT_NAME = "mas-f80ab72d-endpoint"
BASE_URL = "https://adb-8849935324384487.7.azuredatabricks.net/serving-endpoints"

app = FastAPI(title="ChatMLP API")


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


@lru_cache(maxsize=1)
def get_client():
    """Create the OpenAI client pointed at the Databricks serving endpoint.

    On a Databricks App, auth is automatic via the service principal's OAuth
    (M2M). On Replit / local there are usually no credentials, so we return
    None and the API answers in demo mode.
    """
    try:
        from openai import OpenAI
        from databricks.sdk import WorkspaceClient

        w = WorkspaceClient()
        headers = w.config.authenticate()
        token = headers["Authorization"].replace("Bearer ", "")
        return OpenAI(api_key=token, base_url=BASE_URL)
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
_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_DIST):
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="static")
