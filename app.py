import os
import requests
import streamlit as st

ENDPOINT_URL = "https://adb-8849935324384487.7.azuredatabricks.net/serving-endpoints/mas-f80ab72d-endpoint/invocations"

st.set_page_config(page_title="ChatMLP", layout="wide")
st.title("ChatMLP")

token = os.getenv("DATABRICKS_TOKEN")

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
                    {"role": "user", "content": question}
                ]
            }

            headers = {"Content-Type": "application/json"}

            if token:
                headers["Authorization"] = f"Bearer {token}"

            r = requests.post(
                ENDPOINT_URL,
                headers=headers,
                json=payload,
                timeout=120,
            )

            st.write("Status:", r.status_code)

            try:
                result = r.json()
                st.json(result)

                answer = (
                    result.get("output")
                    or result.get("predictions")
                    or result.get("choices")
                    or result
                )
            except Exception:
                st.error("La respuesta del endpoint no es JSON.")
                st.text(r.text[:3000])
                answer = r.text[:3000]

            st.session_state.messages.append(
                {"role": "assistant", "content": str(answer)}
            )