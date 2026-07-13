from databricks.sdk import WorkspaceClient
import json

def init_workspace_client():
    try:
        return WorkspaceClient()
    except Exception as exc:
        return None

def call_agent(workspace_client, ENDPOINT_NAME: str, messages: list[dict[str, str]]) -> dict:
    if workspace_client == None:
        response={"error": "No se pudo inicializar el cliente de la API de Databricks"}
        return response
    else:

        valid_roles = {"user", "assistant", "system"}

        clean_messages = [
            {
                "role": message["role"],
                "content": message["content"],
            }
            for message in messages
            if message.get("role") in valid_roles
            and isinstance(message.get("content"), str)
            and message["content"].strip()
        ]


        response = workspace_client.api_client.do(
            method="POST",
            path=f"/serving-endpoints/{ENDPOINT_NAME}/invocations",
            headers={"Content-Type": "application/json"},
            body={"input": clean_messages}
        )

        return response

def get_final_message(response: dict) -> str:
    output = response.get("output", [])

    # Recorre desde el final para ignorar mensajes intermedios
    for item in reversed(output):
        if (
            item.get("type") == "message"
            and item.get("role") == "assistant"
        ):
            texts = [
                content.get("text", "")
                for content in item.get("content", [])
                if content.get("type") == "output_text"
                and content.get("text")
            ]

            if texts:
                return "\n".join(texts)

    return "No se encontró una respuesta final del agente."