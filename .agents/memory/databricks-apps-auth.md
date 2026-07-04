---
name: Databricks Apps serving-endpoint auth
description: How to authenticate a backend to a Databricks serving endpoint so it survives long-running deploys
---

# Databricks Apps → serving endpoint auth

On a Databricks App, auth to a serving endpoint is automatic via the service
principal's OAuth (M2M). `WorkspaceClient()` resolves credentials from the
platform-injected env with no extra config.

## Rule: use the SDK's auto-refreshing OpenAI client
Use `WorkspaceClient().serving_endpoints.get_open_ai_client()` to get the
OpenAI-compatible client. Do NOT extract a bearer token once and build a plain
`OpenAI(api_key=token, ...)`.

**Why:** M2M OAuth tokens are short-lived (~1h). A statically captured token
cached for the process lifetime makes the app work at first, then fail with 401
until restart. `get_open_ai_client()` refreshes the token per request.

## Rule: cache the client, never cache auth failures
Cache only a successfully created client. A transient error during init must not
be cached (avoid `@lru_cache` returning `None`), or the app pins itself into
demo/fallback mode until restart.

**How to apply:** module-level `_client` guarded var; on exception return None
without storing it.

## Notes
- The base URL / workspace host is derived by the SDK automatically on a
  Databricks App — no need to hardcode a `.../serving-endpoints` BASE_URL.
- `responses.create(model=ENDPOINT_NAME, ...)` is the right call for a Mosaic AI
  **Agent** endpoint; a classic model-serving endpoint would need
  `chat.completions.create`. Match the call to the endpoint type.
- Databricks App only serves the SPA if `frontend/dist` is prebuilt and present
  in the uploaded source; `app.yaml` runs uvicorn but does not build the front.
