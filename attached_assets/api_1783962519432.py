from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from functions.call_agent_functions import (
    call_agent,
    get_final_message,
    init_workspace_client,
)


app = FastAPI()

ENDPOINT_NAME = "mas-c7a80bc8-endpoint"


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class AgentRequest(BaseModel):
    messages: list[ChatMessage]


class AgentResponse(BaseModel):
    answer: str


@app.post(
    "/api/agent",
    response_model=AgentResponse,
)
async def ask_agent(
    payload: AgentRequest,
    request: Request,
) -> AgentResponse:

    # Este header lo agrega Databricks Apps al request
    # que llega desde el frontend.
    user_access_token = request.headers.get(
        "x-forwarded-access-token"
    )

    if not user_access_token:
        raise HTTPException(
            status_code=401,
            detail=(
                "No se recibió x-forwarded-access-token. "
                "Revisa User Authorization, scopes, consentimiento "
                "y reinicio de la App."
            ),
        )

    messages = [
        message.model_dump()
        for message in payload.messages
    ]

    try:
        workspace_client = init_workspace_client(
            user_access_token=user_access_token,
        )

        response = call_agent(
            workspace_client=workspace_client,
            endpoint_name=ENDPOINT_NAME,
            messages=messages,
        )

        answer = get_final_message(response)

        return AgentResponse(answer=answer)

    except Exception as exc:
        # No registres el token del usuario.
        raise HTTPException(
            status_code=500,
            detail=f"Error consultando agente: {type(exc).__name__}: {exc}",
        ) from exc