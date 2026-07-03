# chatmlp - Databricks App MVP

App Streamlit mínima para conversar con un agente desplegado como Databricks Serving Endpoint.

## Archivos

- `app.py`: interfaz de chat.
- `app.yaml`: comando de ejecución para Databricks Apps.
- `requirements.txt`: dependencias Python.

## Cómo usar

1. Sube estos archivos a tu folder del workspace:

```text
/Workspace/Users/ntagle@pelambres.cl/chatmlp
```

2. En la Databricks App, selecciona ese folder como source code.

3. Configura la variable de entorno:

```text
AGENT_ENDPOINT=nombre_del_endpoint_del_agente
```

4. Da permisos al service principal de la App para consultar el endpoint.

5. Deploy.

## Flujo esperado

```text
Databricks App
  -> Agent endpoint
  -> Tools del agente
  -> Genie / SQL / Python tools
  -> Respuesta en chat
```
