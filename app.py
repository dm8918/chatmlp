import streamlit as st
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

ENDPOINT_NAME = "mas-f80ab72d-endpoint"

w = WorkspaceClient()

st.title("ChatMLP")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

question = st.chat_input("Pregunta sobre la operación")

if question:
    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user"):
        st.write(question)

    sdk_messages = [
        ChatMessage(
            role=ChatMessageRole.USER if m["role"] == "user" else ChatMessageRole.ASSISTANT,
            content=m["content"]
        )
        for m in st.session_state.messages
    ]

    with st.chat_message("assistant"):
        with st.spinner("Consultando agente..."):
            response = w.serving_endpoints.query(
                name=ENDPOINT_NAME,
                messages=sdk_messages
            )

            answer = response.choices[0].message.content
            st.write(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})