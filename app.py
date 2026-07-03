import streamlit as st
from databricks.sdk import WorkspaceClient

ENDPOINT_NAME = "mas-f80ab72d-endpoint"

w = WorkspaceClient()

st.set_page_config(page_title="ChatMLP", layout="wide")
st.title("ChatMLP")

question = st.chat_input("Pregunta sobre la operación")

if question:
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("Consultando agente..."):
            response = w.serving_endpoints.query(
                name=ENDPOINT_NAME,
                dataframe_records=[
                    {
                        "input": [
                            {"role": "user", "content": question}
                        ]
                    }
                ]
            )

            st.write(response.as_dict())