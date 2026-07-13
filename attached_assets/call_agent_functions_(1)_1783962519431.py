from typing import Any

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config


def init_workspace_client(
    user_access_token: str,
) -> WorkspaceClient:
    """
    Crea un cliente Databricks utilizando la identidad
    del usuario que está interactuando con la App.
    """

    if not user_access_token:
        raise ValueError(
            "No se recibió el token OAuth del usuario."
        )

    config = Config()

    return WorkspaceClient(
        host=config.host,
        token=user_access_token,
    )


def call_agent(
    workspace_client: WorkspaceClient,
    endpoint_name: str,
    messages: list[dict[str, str]],
) -> dict[str, Any]:

    valid_roles = {"user", "assistant", "system"}

    clean_messages = [
        {
            "role": message["role"],
            "content": message["content"].strip(),
        }
        for message in messages
        if message.get("role") in valid_roles
        and isinstance(message.get("content"), str)
        and message["content"].strip()
    ]

    if not clean_messages:
        raise ValueError(
            "No hay mensajes válidos para enviar al agente."
        )

    return workspace_client.api_client.do(
        method="POST",
        path=f"/serving-endpoints/{endpoint_name}/invocations",
        headers={
            "Content-Type": "application/json",
        },
        body={
            "input": clean_messages,
        },
    )


def get_final_message(response: dict[str, Any]) -> str:
    output = response.get("output", [])

    for item in reversed(output):
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
            if content.get("type") == "output_text"
            and content.get("text", "").strip()
        ]

        if not texts:
            continue

        text = "\n".join(texts)

        # Ignorar marcadores intermedios como:
        # <name>vector_search_indices</name>
        if text.startswith("<name>") and text.endswith("</name>"):
            continue

        return text

    return "El agente no generó una respuesta final."