from functions.call_agent_functions import *

ENDPOINT_NAME = "mas-c7a80bc8-endpoint"

messages=[
    {"role": "user", "content": "¿Cuáles han sido las principales pérdidas del periodo?"},
    {"role": "assistant", "content": "¿Qué área, mina o planta?"},
    {"role": "user", "content": "Área mina"}
]

messages=[{'role':'user','content':'quiero el resumen del día 5 de junio 2026'}]

workspace_client = init_workspace_client()
response= call_agent(workspace_client, ENDPOINT_NAME, messages)
get_final_message(response)