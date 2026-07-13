"""Databricks agent invocation helpers.

This mirrors the code that the user verified working inside a Databricks
notebook: it relies on the Databricks SDK's ``WorkspaceClient`` to resolve
authentication automatically (on a Databricks App the service principal's
credentials are injected; the SDK also refreshes short-lived tokens per
request). The agent is called through the serving endpoint's ``/invocations``
route and the final assistant message is extracted from the response.
"""

from databricks.sdk import WorkspaceClient

VALID_ROLES = {"user", "assistant", "system"}


def init_workspace_client():
    """Return a WorkspaceClient, or None when credentials cannot be resolved
    (e.g. running locally on Replit without Databricks auth configured)."""
    try:
        return WorkspaceClient()
    except Exception:
        return None


def clean_conversation(messages: list[dict]) -> list[dict]:
    """Keep only well-formed messages with a valid role and non-empty text."""
    return [
        {"role": message["role"], "content": message["content"]}
        for message in messages
        if message.get("role") in VALID_ROLES
        and isinstance(message.get("content"), str)
        and message["content"].strip()
    ]


def call_agent(
    workspace_client, endpoint_name: str, messages: list[dict]
) -> dict:
    """Send the conversation to the agent serving endpoint via /invocations.

    Returns the parsed response dict, or ``{"error": ...}`` when the client
    could not be initialised.
    """
    if workspace_client is None:
        return {"error": "No se pudo inicializar el cliente de la API de Databricks"}

    clean_messages = clean_conversation(messages)

    return workspace_client.api_client.do(
        method="POST",
        path=f"/serving-endpoints/{endpoint_name}/invocations",
        headers={"Content-Type": "application/json"},
        body={"input": clean_messages},
    )


def get_final_message(response: dict) -> str:
    """Return the last substantive assistant message text from the response.

    Iterates the ``output`` list from the end so intermediate narration and
    tool calls are ignored, returning the text of the last assistant message.
    """
    output = response.get("output", []) if isinstance(response, dict) else []

    for item in reversed(output):
        if not isinstance(item, dict):
            continue
        if item.get("type") == "message" and item.get("role") == "assistant":
            texts = [
                content.get("text", "")
                for content in item.get("content", [])
                if isinstance(content, dict)
                and content.get("type") == "output_text"
                and content.get("text")
            ]
            if texts:
                return "\n".join(texts)

    return "No se encontró una respuesta final del agente."
