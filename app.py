import os
import streamlit as st

try:
    from databricks.sdk import WorkspaceClient
except Exception:
    WorkspaceClient = None

st.set_page_config(page_title="Mining Copilot", layout="wide")
st.title("Mining Copilot")
st.caption("Interfaz MVP para consultar un agente Databricks")

AGENT_ENDPOINT = os.getenv("AGENT_ENDPOINT", "")

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.header("Configuración")
    st.write("Define AGENT_ENDPOINT en las variables de entorno de la Databricks App.")
    st.code("AGENT_ENDPOINT=nombre_del_endpoint", language="bash")
    st.divider()
    st.write("Estado:")
    st.write("✅ App cargada")
    st.write("✅ Chat activo")
    st.write("⚠️ Agente conectado" if AGENT_ENDPOINT else "⛔ Falta AGENT_ENDPOINT")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

question = st.chat_input("Pregunta sobre la operación")


def call_agent(messages):
    """Llama a un Agent/Serving Endpoint de Databricks.

    Requiere que la Databricks App tenga permisos para consultar el endpoint.
    """
    if not AGENT_ENDPOINT:
        return (
            "La app funciona, pero aún falta configurar la variable de entorno "
            "AGENT_ENDPOINT con el nombre del endpoint del agente."
        )

    if WorkspaceClient is None:
        return "No se pudo importar databricks-sdk. Revisa requirements.txt."

    w = WorkspaceClient()
    response = w.serving_endpoints.query(
        name=AGENT_ENDPOINT,
        messages=messages,
    )

    try:
        return response.choices[0].message.content
    except Exception:
        return str(response)


if question:
    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("Consultando agente..."):
            answer = call_agent(st.session_state.messages)
            st.write(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
