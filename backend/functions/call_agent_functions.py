"""Databricks agent invocation helpers (on-behalf-of-user auth).

Authentication flow::

    Navegador
      ↓
    Databricks Apps reverse proxy
      ├── autentica al usuario
      ├── agrega x-forwarded-access-token
      ↓
    FastAPI (este backend)

The Databricks App's reverse proxy authenticates the end user and forwards
their OAuth access token in the ``x-forwarded-access-token`` header. The backend
reads that header and builds a ``WorkspaceClient`` with the *user's* identity, so
the agent (and any Vector Search / catalog it touches) runs with the user's own
permissions instead of the App's service principal.
"""

from typing import Any

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config

VALID_ROLES = {"user", "assistant", "system"}


def init_workspace_client(user_access_token: str) -> WorkspaceClient:
    """Create a Databricks client using the identity of the user interacting
    with the App (on-behalf-of-user).

    Raises ``ValueError`` if the forwarded user token is missing.
    """
    if not user_access_token:
        raise ValueError("No se recibió el token OAuth del usuario.")

    config = Config()

    # auth_type="pat" fuerza el uso del token del usuario e ignora las
    # credenciales OAuth del service principal que Databricks Apps inyecta en el
    # entorno (DATABRICKS_CLIENT_ID / DATABRICKS_CLIENT_SECRET). Sin esto el SDK
    # detecta dos métodos de auth (oauth + pat) y falla la validación.
    return WorkspaceClient(
        host=config.host,
        token=user_access_token,
        auth_type="pat",
    )


def clean_conversation(messages: list[dict]) -> list[dict[str, str]]:
    """Keep only well-formed messages with a valid role and non-empty text."""
    return [
        {
            "role": message["role"],
            "content": message["content"].strip(),
        }
        for message in messages
        if message.get("role") in VALID_ROLES
        and isinstance(message.get("content"), str)
        and message["content"].strip()
    ]


def call_agent(
    workspace_client: WorkspaceClient,
    endpoint_name: str,
    messages: list[dict[str, str]],
) -> dict[str, Any]:
    """Send the conversation to the agent serving endpoint via /invocations."""
    clean_messages = clean_conversation(messages)

    if not clean_messages:
        raise ValueError("No hay mensajes válidos para enviar al agente.")

    return workspace_client.api_client.do(
        method="POST",
        path=f"/serving-endpoints/{endpoint_name}/invocations",
        headers={"Content-Type": "application/json"},
        body={"input": clean_messages},
    )


def get_final_message(response: dict[str, Any]) -> str:
    """Return the last substantive assistant message text from the response.

    Iterates the ``output`` list from the end so intermediate narration, tool
    results (items with a ``call_id``) and marker payloads such as
    ``<name>vector_search_indices</name>`` are ignored.
    """
    output = response.get("output", []) if isinstance(response, dict) else []

    for item in reversed(output):
        if not isinstance(item, dict):
            continue

        if item.get("type") != "message":
            continue

        if item.get("role") != "assistant":
            continue

        # Ignorar resultados intermedios de tools.
        if item.get("call_id"):
            continue

        texts = [
            content.get("text", "").strip()
            for content in item.get("content", [])
            if isinstance(content, dict)
            and content.get("type") == "output_text"
            and content.get("text", "").strip()
        ]

        if not texts:
            continue

        text = "\n".join(texts)

        # Ignorar marcadores intermedios como
        # <name>vector_search_indices</name>.
        if text.startswith("<name>") and text.endswith("</name>"):
            continue

        return text

    return "El agente no generó una respuesta final."
