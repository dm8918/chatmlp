import base64
import json
import logging
import os
import threading
import time

import requests
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chatmlp")

app = FastAPI(title="ChatMLP API")

# Databricks Apps inject DATABRICKS_HOST / DATABRICKS_CLIENT_ID /
# DATABRICKS_CLIENT_SECRET automatically for the app's service principal.
# Locally these can be provided as env vars. They are read lazily (never at
# import time) so the app still boots without credentials.
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
    "El agente intentó llamar una herramienta",
    "El agente solo devolvió texto intermedio",
    "El agente no devolvió texto",
)


def is_error_message(msg: dict) -> bool:
    return msg.get("role") == "assistant" and str(msg.get("content", "")).startswith(
        _ERROR_PREFIXES
    )


class NoCredentialsError(Exception):
    """Raised when no Databricks credentials are available (local/offline)."""


# ---------------------------------------------------------------------------
# OAuth M2M (client credentials) with token cache
# ---------------------------------------------------------------------------

_token_cache: dict = {"access_token": None, "expires_at": 0.0, "key": None}
_token_lock = threading.Lock()


def get_databricks_token(trace: list[str]) -> tuple[str, str]:
    """Return (host, access_token) using OAuth M2M client credentials.

    The token is cached until shortly before expiry. Raises NoCredentialsError
    when the required env vars are missing (e.g. running locally on Replit).
    """
    host = os.environ.get("DATABRICKS_HOST", "").strip().rstrip("/")
    if host and not host.startswith(("http://", "https://")):
        host = f"https://{host}"
    client_id = os.environ.get("DATABRICKS_CLIENT_ID", "")
    client_secret = os.environ.get("DATABRICKS_CLIENT_SECRET", "")

    if not host or not client_id or not client_secret:
        missing = [
            name
            for name, val in (
                ("DATABRICKS_HOST", host),
                ("DATABRICKS_CLIENT_ID", client_id),
                ("DATABRICKS_CLIENT_SECRET", client_secret),
            )
            if not val
        ]
        trace.append(f"1. Autenticación FALLÓ: faltan variables {', '.join(missing)}")
        raise NoCredentialsError(f"Faltan variables de entorno: {', '.join(missing)}")

    cache_key = f"{host}|{client_id}"
    with _token_lock:
        now = time.time()
        if (
            _token_cache["access_token"]
            and _token_cache["key"] == cache_key
            and now < _token_cache["expires_at"] - 60
        ):
            trace.append("1. Autenticación OK (token OAuth en caché)")
            return host, _token_cache["access_token"]

        token_url = f"{host}/oidc/v1/token"
        basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

        resp = requests.post(
            token_url,
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials", "scope": "all-apis"},
            timeout=30,
        )
        if resp.status_code != 200:
            trace.append(
                f"1. Autenticación FALLÓ: token endpoint HTTP {resp.status_code}: "
                f"{resp.text[:300]}"
            )
            raise RuntimeError(
                f"No se pudo obtener token OAuth (HTTP {resp.status_code}): "
                f"{resp.text[:300]}"
            )

        token_data = resp.json()
        _token_cache["access_token"] = token_data["access_token"]
        _token_cache["expires_at"] = now + int(token_data.get("expires_in", 3600))
        _token_cache["key"] = cache_key
        trace.append(f"1. Autenticación OK (OAuth M2M, host: {host})")
        return host, _token_cache["access_token"]


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

WEAK_STARTS = [
    "voy a consultar",
    "déjame consultar",
    "dejame consultar",
    "voy a buscar",
    "buscaré",
    "buscare",
    "consultaré",
    "consultare",
]


def is_weak_intermediate_text(text: str) -> bool:
    lower = text.strip().lower()
    return any(lower.startswith(x) for x in WEAK_STARTS)


def looks_like_tool_echo(text: str) -> bool:
    """Detect tool-output echoes that must never count as a final answer:
    XML-like tags (<name>...</name>), raw JSON/array dumps, etc."""
    stripped = text.strip()
    if not stripped:
        return True
    if stripped.startswith("<"):
        return True
    if stripped.startswith(("{", "[")):
        try:
            json.loads(stripped)
            return True
        except ValueError:
            # Even if it isn't valid JSON, a text that both starts and ends
            # with brackets/braces is a structured dump, not an answer.
            if stripped[-1] in ("}", "]"):
                return True
    return False


def parse_sse_error(text: str):
    """Databricks can return HTTP 200 with an SSE error block:
    event: error
    data: {"error_code": "...", "message": "..."}

    Returns a dict with error_code/message when the data block is JSON,
    otherwise the raw data string.
    """
    if "event: error" not in text:
        return None
    for line in text.splitlines():
        if line.startswith("data:"):
            raw = line.replace("data:", "", 1).strip()
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return {
                        "error_code": parsed.get("error_code"),
                        "message": parsed.get("message") or raw,
                    }
            except ValueError:
                pass
            return {"error_code": None, "message": raw}
    return {"error_code": None, "message": text[:400]}


def extract_final_answer(data: dict) -> dict:
    outputs = data.get("output", [])
    texts: list[str] = []
    function_calls = []

    for item in outputs:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        if item_type == "function_call":
            function_calls.append(item)
        if item_type == "message" and item.get("role") == "assistant":
            for content in item.get("content", []):
                if isinstance(content, dict) and content.get("type") in (
                    "output_text",
                    "text",
                ):
                    txt = (content.get("text") or "").strip()
                    if txt:
                        texts.append(txt)

    # Only substantive text counts as a final answer. Weak intermediate
    # snippets ("Voy a consultar...") and tool-output echoes
    # (<name>...</name>, JSON dumps) are NEVER returned as the final answer.
    # The agent narrates progress between tool calls, so the FINAL answer is
    # the LAST substantive text — never the concatenation of every snippet.
    substantive = [
        t
        for t in texts
        if not is_weak_intermediate_text(t) and not looks_like_tool_echo(t)
    ]
    answer = substantive[-1].strip() if substantive else ""
    has_final_answer = bool(answer)

    return {
        "answer": answer,
        "has_final_answer": has_final_answer,
        "function_call_count": len(function_calls),
        "assistant_text_count": len(texts),
        "raw_output_count": len(outputs),
        "texts": texts,
    }


# ---------------------------------------------------------------------------
# Agent call via the serving endpoint invocations API
# ---------------------------------------------------------------------------

def ask_databricks_agent(messages: list[dict], trace: list[str]) -> str:
    host, token = get_databricks_token(trace)

    endpoint = agent_endpoint()
    url = f"{host}/serving-endpoints/{endpoint}/invocations"
    payload = {"input": messages}

    trace.append(f"2. POST {url}")
    trace.append(f"   Enviado: {json.dumps(payload, ensure_ascii=False)[:600]}")

    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "x-mlflow-return-trace-id": "true",
        },
        json=payload,
        timeout=120,
    )

    content_type = resp.headers.get("content-type", "")
    trace_id = resp.headers.get("x-mlflow-trace-id")
    raw_text = resp.text

    trace.append(
        f"3. Respuesta HTTP {resp.status_code} en {resp.elapsed.total_seconds():.1f}s "
        f"(content-type: {content_type}"
        + (f", trace-id: {trace_id})" if trace_id else ")")
    )
    trace.append(f"   Recibido: {raw_text[:1500]}")

    logger.info(
        "invocations API: endpoint=%s status=%s content_type=%s trace_id=%s",
        endpoint,
        resp.status_code,
        content_type,
        trace_id,
    )

    sse_error = parse_sse_error(raw_text)
    if sse_error:
        code = sse_error.get("error_code")
        msg = str(sse_error.get("message", ""))[:400]
        logger.error(
            "invocations API SSE error: endpoint=%s error_code=%s message=%s",
            endpoint,
            code,
            msg,
        )
        detail = f"[{code}] {msg}" if code else msg
        trace.append(f"4. ERROR SSE del endpoint: {detail}")
        raise RuntimeError(f"Databricks devolvió error SSE: {detail}")

    if resp.status_code >= 400:
        trace.append("4. ERROR: el endpoint rechazó la solicitud")
        raise RuntimeError(f"HTTP {resp.status_code}: {raw_text[:400]}")

    try:
        data = resp.json()
    except ValueError:
        trace.append("4. ERROR: el cuerpo no es JSON válido")
        raise RuntimeError(
            f"El endpoint no devolvió JSON (content-type: {content_type}): "
            f"{raw_text[:400]}"
        )

    if data.get("error"):
        err = data["error"]
        trace.append(f"4. ERROR devuelto por el endpoint: {json.dumps(err)[:300]}")
        raise RuntimeError(f"Error del endpoint: {json.dumps(err)[:300]}")

    parsed = extract_final_answer(data)
    trace.append(
        f"4. Análisis: {parsed['raw_output_count']} items, "
        f"{parsed['function_call_count']} function_call, "
        f"{parsed['assistant_text_count']} textos assistant, "
        f"respuesta final: {'sí' if parsed['has_final_answer'] else 'no'}"
    )
    for i, t in enumerate(parsed["texts"], 1):
        marker = " ← ELEGIDO como respuesta final" if t.strip() == parsed["answer"] else ""
        trace.append(f"   Texto {i}: {t[:160]}{'…' if len(t) > 160 else ''}{marker}")

    logger.info(
        "invocations API parsed: endpoint=%s function_calls=%s assistant_texts=%s final=%s",
        endpoint,
        parsed["function_call_count"],
        parsed["assistant_text_count"],
        parsed["has_final_answer"],
    )

    if parsed["function_call_count"] > 0 and not parsed["has_final_answer"]:
        trace.append("5. ERROR: function_call sin respuesta final")
        raise RuntimeError(
            "El agente intentó llamar una herramienta pero no devolvió respuesta "
            "final. Revisa permisos o tool-calling del agente."
        )

    if not parsed["has_final_answer"]:
        if parsed["assistant_text_count"] > 0:
            trace.append("5. ERROR: solo texto intermedio, sin respuesta final")
            raise RuntimeError(
                "El agente solo devolvió texto intermedio ('Voy a consultar...') "
                "sin una respuesta final sustantiva."
            )
        trace.append("5. ERROR: el agente no devolvió texto")
        raise RuntimeError("El agente no devolvió texto en la respuesta.")

    trace.append(
        f"5. Respuesta final extraída correctamente: {parsed['answer'][:200]}"
        + ("…" if len(parsed["answer"]) > 200 else "")
    )
    return parsed["answer"]


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    configured = bool(
        os.environ.get("DATABRICKS_HOST")
        and os.environ.get("DATABRICKS_CLIENT_ID")
        and os.environ.get("DATABRICKS_CLIENT_SECRET")
    )
    return {"status": "ok", "credentials_configured": configured}


@app.post("/api/chat")
def chat(req: ChatRequest):
    payload = [
        msg for msg in (m.model_dump() for m in req.messages) if not is_error_message(msg)
    ]
    trace: list[str] = [f"0. Endpoint destino: {agent_endpoint()} (vía /invocations)"]
    dropped = len(req.messages) - len(payload)
    if dropped:
        trace.append(f"   ({dropped} mensaje(s) de error previos excluidos del contexto)")

    try:
        answer = ask_databricks_agent(payload, trace)
        return {"role": "assistant", "type": "text", "content": answer, "trace": trace}
    except NoCredentialsError as e:
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
            "isError": True,
        }
    except Exception as e:
        logger.exception("Error consultando el endpoint %s", agent_endpoint())
        return {
            "role": "assistant",
            "type": "text",
            "content": f"Error consultando el agente ({agent_endpoint()}): {e}",
            "trace": trace,
            "isError": True,
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
