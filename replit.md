# ChatMLP

Streamlit chat front-end for a Databricks agent served as a Databricks Serving Endpoint.

## Overview

- `app.py`: Streamlit chat UI.
- `app.yaml`: run command for Databricks Apps.
- `requirements.txt`: Python dependencies.
- `.streamlit/config.toml`: Streamlit server config for the Replit proxy (port 5000, all hosts).

## Auth model

- On **Databricks Apps**, authentication is automatic via the service principal's OAuth (M2M). `WorkspaceClient()` resolves credentials with no extra config.
- On **Replit / local**, there are usually no Databricks credentials. The app detects this and runs in **demo mode** (simulated responses) so the front can be developed and deployed without connecting to Databricks.

## Running locally (Replit)

The "Start application" workflow runs:

```
streamlit run app.py --server.port 5000 --server.address 0.0.0.0
```

## Deploying to a Databricks App

Upload the project files to the workspace folder, select it as the App source,
and deploy. The serving endpoint and workspace host are configured in `app.py`
(`ENDPOINT_NAME`, `BASE_URL`). Grant the App's service principal permission to
query the endpoint.

## User preferences

- The user works primarily on the front-end and wants it deployable without a
  live Databricks connection. Keep the Databricks connection optional/graceful.
