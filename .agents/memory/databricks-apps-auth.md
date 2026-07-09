---
name: Databricks Apps serving-endpoint auth
description: How to authenticate and call a Databricks agent serving endpoint (OAuth M2M, per-endpoint /invocations API) so it survives long-running deploys
---

# Databricks Apps → agent serving endpoint

This project talks to a Mosaic AI **Agent** endpoint via the endpoint's
**invocations API** (`POST {host}/serving-endpoints/{endpoint}/invocations`,
body `{"input": [...]}`) using `requests`, NOT the databricks-sdk / openai
clients (dropped deliberately to keep deps minimal and control parsing).

**Why:** the generic `POST {host}/serving-endpoints/responses` route (with
`model` in the body) did NOT work for this agent endpoint; the per-endpoint
`/invocations` URL is what works (verified from a Databricks notebook). The
response body still has the Responses-API shape (`output` array with
`message`/`function_call` items).

## Rule: OAuth M2M with expiry-aware, keyed, locked cache
Request tokens from `{DATABRICKS_HOST}/oidc/v1/token` (Basic auth with
client_id:client_secret, `grant_type=client_credentials`, `scope=all-apis`).
Cache the token but refresh ~60s before expiry, key the cache by
host|client_id, and guard with a threading lock.

**Why:** M2M tokens are short-lived (~1h). A statically captured token makes
the app work at first, then fail with 401 until restart. An unkeyed cache
serves a stale token if credentials change; an unlocked cache races under
concurrent requests.

## Rule: agent responses need defensive parsing
- The agent can emit `function_call` items plus weak intermediate text
  ("Voy a consultar...") — never treat weak text as the final answer; return a
  controlled error if there is no substantive final text.
- Databricks can return HTTP 200 whose body is an SSE error block
  (`event: error` / `data: {json}`) — check for it before assuming success and
  extract `error_code`/`message` from the data JSON.

## Notes
- On a Databricks App, `DATABRICKS_HOST` / `DATABRICKS_CLIENT_ID` /
  `DATABRICKS_CLIENT_SECRET` are injected automatically for the App's service
  principal. Read them lazily (per request), never at import, so the app can
  boot without credentials (Replit/local shows an offline message).
- The App's service principal needs *Can Query* on the serving endpoint.
- Databricks App only serves the SPA if `frontend/dist` is prebuilt and present
  in the uploaded source; `app.yaml` runs uvicorn but does not build the front.
