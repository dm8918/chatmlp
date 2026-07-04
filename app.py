import streamlit as st

ENDPOINT_NAME = "mas-f80ab72d-endpoint"
BASE_URL = "https://adb-8849935324384487.7.azuredatabricks.net/serving-endpoints"

st.set_page_config(page_title="ChatMLP", layout="wide")
st.title("ChatMLP")


@st.cache_resource(show_spinner=False)
def get_client():
    """Crea el cliente OpenAI apuntando al serving endpoint de Databricks.

    En una Databricks App la autenticación es automática (OAuth M2M del
    service principal). En local / Replit normalmente no hay credenciales,
    en cuyo caso devolvemos None y la app funciona en modo demo.
    """
    try:
        from openai import OpenAI
        from databricks.sdk import WorkspaceClient

        w = WorkspaceClient()
        headers = w.config.authenticate()
        token = headers["Authorization"].replace("Bearer ", "")

        return OpenAI(api_key=token, base_url=BASE_URL)
    except Exception:
        return None


client = get_client()

if client is None:
    st.info(
        "Modo demo: sin conexión a Databricks. El front funciona con "
        "respuestas simuladas. Al desplegar como Databricks App la "
        "autenticación se resuelve automáticamente."
    )


def ask_agent(messages):
    """Consulta al agente. Si no hay cliente, responde en modo demo."""
    if client is None:
        last = messages[-1]["content"] if messages else ""
        return f"(demo) Recibí tu mensaje: {last}"

    try:
        response = client.responses.create(
            model=ENDPOINT_NAME,
            input=messages,
        )

        return " ".join(
            getattr(content, "text", "")
            for output in response.output
            for content in getattr(output, "content", [])
        )
    except Exception as exc:
        return f"Error consultando el agente: {exc}"


if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

question = st.chat_input("Pregunta sobre la operación")

if question:
    st.session_state.messages.append({
        "role": "user",
        "content": question,
    })

    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("Consultando agente..."):
            answer = ask_agent(st.session_state.messages)
            st.write(answer)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
    })
