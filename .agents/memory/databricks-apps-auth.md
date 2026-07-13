---
name: Databricks Apps serving-endpoint auth
description: How to authenticate and call a Databricks agent serving endpoint from a backend (on-behalf-of-user via x-forwarded-access-token) and why SP auth was abandoned
---

# Databricks Apps → agent serving endpoint

This project calls a Mosaic AI **Agent** endpoint through the Databricks SDK
`WorkspaceClient`, using its low-level `api_client.do()` to POST to the
per-endpoint invocations route:
`POST /serving-endpoints/{endpoint}/invocations` with body `{"input": [...]}`.

## Auth: on-behalf-of-user (OBO), NOT the service principal
The Databricks App reverse proxy authenticates the end user and forwards their
OAuth token in the **`x-forwarded-access-token`** header. The backend reads that
header per request and builds `WorkspaceClient(host=Config().host,
token=<user_token>)`, so the agent runs with the *user's own* permissions.

**Why OBO instead of the App's service principal:** the agent's tools read a
Vector Search index / catalog. The App's service principal did NOT have read
access there, so the agent ran a `function_call` but the search returned empty
(`<name>vector_search_indices</name>` + `[]`) and "no trae nada" — even though
the exact same query worked in the user's notebook (the notebook runs as the
USER). Running as the user via OBO fixes this without granting the SP broad data
access. Requires enabling **User Authorization** on the App with the right
scopes + user consent, and restarting the App after scope changes.

## Rule: force `auth_type="pat"` when building the user client
On a deployed App the env has the SP's OAuth creds (`DATABRICKS_CLIENT_ID` /
`DATABRICKS_CLIENT_SECRET`). If you build `WorkspaceClient(host=..., token=...)`
without pinning the auth method, the SDK sees BOTH oauth (env) and pat (token)
and fails: `validate: more than one authorization method configured: oauth and
pat`. Pass `auth_type="pat"` so it uses only the user's forwarded token.

## Rule: declare `oauth_scopes` in app.yaml (least privilege)
The forwarded user token is **downscoped** to only the scopes the App declares.
To invoke a serving endpoint the App must declare `serving.serving-endpoints` in
`app.yaml` under `oauth_scopes:`. Missing it → the invocation returns
`403 Forbidden — Invalid scope, required scopes: model-serving` even though the
user has endpoint access. The workspace admin must also have enabled User
Authorization (Public Preview) and the user must consent; restart the App after
changing scopes (internal caches can take ~5 min).

**Local/Replit behavior:** the header is absent, so the backend returns a
controlled "sin conexión" message (never demo data). Even with a fake token
locally it fails at `Config()` because there is no `DATABRICKS_HOST` — expected;
real answers only come from the deployed App.

## Prior approaches that did NOT work (do not resurrect)
- **Manual OAuth M2M** (`{host}/oidc/v1/token`, client credentials): tokens are
  short-lived (~1h) and expired mid-deploy; also `DATABRICKS_HOST` injected by
  Apps has NO scheme so a raw URL needs `https://` prepended.
- **Generic `/serving-endpoints/responses` route** (with `model` in body): did
  NOT work for this agent endpoint. Use the per-endpoint `/invocations` route.
  The response body still has the Responses-API shape (`output` array with
  `message` / `function_call` items).
- **Auto SP auth (`WorkspaceClient()` with no token)**: worked technically but
  hit the Vector Search permission wall above — hence the move to OBO.

## Rule: extract the LAST assistant message as the answer
Walk the `output` list from the end; return the text of the last assistant
`message` item. SKIP tool results (items carrying a `call_id`) and marker-only
payloads whose text is `<name>...</name>`. Filter prior assistant *error*
messages out of the conversation before resending, or they pollute the agent's
context. Never log the user token.

## Deploy note
Databricks Apps only serve the SPA if `frontend/dist` is prebuilt and present in
the uploaded source; `app.yaml` runs uvicorn but does not build the front.
