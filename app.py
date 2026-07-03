import streamlit as st
from databricks.sdk import WorkspaceClient

ENDPOINT_NAME = "mas-f80ab72d-endpoint"

w = WorkspaceClient()

st.set_page_config(page_title="ChatMLP", layout="wide")
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

    with st.chat_message("assistant"):
        with st.spinner("Consultando agente..."):
            payload = {
                "input": [
                    {
                        "role": "user",
                        "content": question
                    }
                ]
            }

            result = w.api_client.do(
                method="POST",
                path=f"/api/2.0/serving-endpoints/{ENDPOINT_NAME}/invocations",
                body=payload,
            )

            answer = (
                result.get("output")
                or result.get("predictions")
                or result.get("choices")
                or result
            )

            st.write(answer)

    st.session_state.messages.append(
        {"role": "assistant", "content": str(answer)}
    )