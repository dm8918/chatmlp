import os
import streamlit as st
from openai import OpenAI

ENDPOINT_NAME = "mas-f80ab72d-endpoint"
BASE_URL = "https://adb-8849935324384487.7.azuredatabricks.net/serving-endpoints"

st.set_page_config(page_title="ChatMLP", layout="wide")
st.title("ChatMLP")

token = os.environ.get("DATABRICKS_TOKEN")

if not token:
    st.error("Falta configurar la variable DATABRICKS_TOKEN en la Databricks App.")
    st.stop()

client = OpenAI(
    api_key=token,
    base_url=BASE_URL
)

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

question = st.chat_input("Pregunta sobre la operación")

if question:
    st.session_state.messages.append({
        "role": "user",
        "content": question
    })

    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("Consultando agente..."):
            response = client.responses.create(
                model=ENDPOINT_NAME,
                input=st.session_state.messages
            )

            answer = " ".join(
                getattr(content, "text", "")
                for output in response.output
                for content in getattr(output, "content", [])
            )

            st.write(answer)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })