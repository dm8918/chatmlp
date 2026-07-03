import streamlit as st
from databricks.sdk import WorkspaceClient

ENDPOINT_NAME = "mas-f80ab72d-endpoint"

w = WorkspaceClient()
client = w.serving_endpoints.get_open_ai_client()

st.set_page_config(page_title="ChatMLP", layout="wide")
st.title("ChatMLP")

question = st.chat_input("Pregunta sobre la operación")

if question:
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("Consultando agente..."):
            response = client.chat.completions.create(
                model=ENDPOINT_NAME,
                messages=[{"role": "user", "content": question}]
            )
            st.write(response.choices[0].message.content)