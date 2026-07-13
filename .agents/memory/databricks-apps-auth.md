---
name: Databricks Apps serving-endpoint auth
description: How to authenticate and call a Databricks agent serving endpoint from a backend (SDK WorkspaceClient + /invocations) so it survives long-running deploys
---

# Databricks Apps → agent serving endpoint

This project calls a Mosaic AI **Agent** endpoint through the **Databricks SDK**
`WorkspaceClient`, using its low-level `api_client.do()` to POST to the
per-endpoint invocations route:
`POST /serving-endpoints/{endpoint}/invocations` with body `{"input": [...]}`.

**Why the SDK (not manual OAuth):** an earlier version did manual OAuth M2M
(`{host}/oidc/v1/token`, client credentials) and hit two problems worth
remembering: (1) `DATABRICKS_HOST` injected by Databricks Apps has NO scheme, so
a raw manual URL needs `https://` prepended; (2) statically-cached M2M tokens
are short-lived (~1h) and expire mid-deploy. `WorkspaceClient()` resolves the
service principal's credentials automatically on a Databricks App and refreshes
tokens per request, avoiding both. The user also verified this exact SDK call
shape works from a Databricks notebook.

**Why per-endpoint /invocations (not the generic /responses route):** the
generic `POST {host}/serving-endpoints/responses` route (with `model` in the
body) did NOT work for this agent endpoint. The response body still has the
Responses-API shape (`output` array with `message` / `function_call` items).

## Rule: cache only a successful client, never a failed init
Module-level `_client` guarded var; on init failure return `None` WITHOUT
storing it. Caching `None` would pin the app into the offline/error state until
a restart. This also gives the clean local/offline behavior: no creds →
`WorkspaceClient()` raises → `None` → controlled "sin conexión" message (never
demo data).

## Rule: extract the LAST assistant message as the answer
The agent narrates progress between tool calls. Walk the `output` list from the
end and return the text of the last assistant `message` item; intermediate
narration and tool-call items are naturally skipped. Filter prior assistant
*error* messages out of the conversation before resending, or they pollute the
agent's context.

## Notes
- The App's service principal needs *Can Query* on the serving endpoint, AND
  read access to whatever the agent's tools touch (e.g. Vector Search index /
  catalog+schema). Symptom of missing tool perms: agent runs a function_call
  but the search returns empty (`<name>vector_search_indices</name>` + `[]`) and
  "no trae nada" even though the same query works in a user's notebook (the
  notebook runs as the USER, the App as the service principal).
- Databricks App only serves the SPA if `frontend/dist` is prebuilt and present
  in the uploaded source; `app.yaml` runs uvicorn but does not build the front.
