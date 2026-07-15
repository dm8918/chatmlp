# ChatMLP — Cerebro

React chat front-end ("Cerebro", Los Pelambres) for a Databricks agent served as
a Databricks Serving Endpoint, with a FastAPI backend.

## Architecture

- `frontend/`: React + Vite + TypeScript single-page app (the Cerebro chat UI).
  - Dev server runs on `0.0.0.0:5000` and proxies `/api/*` to the backend.
  - Conversation history persists in the browser's localStorage.
- `backend/main.py`: FastAPI app (HTTP layer + trace + offline handling).
- `backend/functions/call_agent_functions.py`: Databricks invocation logic.
  - `init_workspace_client(user_access_token)`: builds a `WorkspaceClient` using
    `host=Config().host` and `token=<user's forwarded OAuth token>`. Raises
    `ValueError` if the token is missing.
  - `call_agent(client, endpoint, messages)`: calls the agent via
    `client.api_client.do(POST /serving-endpoints/{endpoint}/invocations,
    body {"input": clean_messages})`. Mirrors the notebook code the user
    verified working.
  - `get_final_message(response)`: returns the LAST assistant message's text
    from the `output` list, skipping tool results (items with a `call_id`) and
    marker payloads like `<name>vector_search_indices</name>`.
  - `POST /api/chat`: reads the `x-forwarded-access-token` header, builds the
    per-user client, runs the above and returns
    `{role, type, content, trace, isError}` — `trace` is a step-by-step log
    (token received, client init, request, FULL response JSON, parsing) shown in
    the UI under "Ver seguimiento".
  - `GET /api/health`: reports `user_token_present` (whether the forwarded token
    header is on the request).
  - In production it also serves the built React app from `frontend/dist`.
- `app.yaml`: run command for Databricks Apps (`uvicorn backend.main:app`).
- `requirements.txt`: fastapi, uvicorn, databricks-sdk.

## Auth model — on-behalf-of-user (OBO)

    Navegador
      ↓
    Databricks Apps reverse proxy
      ├── autentica al usuario
      ├── agrega x-forwarded-access-token
      ↓
    FastAPI (este backend)

- The Databricks App's reverse proxy authenticates the end user and forwards
  their OAuth token in the **`x-forwarded-access-token`** header. The backend
  reads it per request and builds a `WorkspaceClient` with **that user's**
  identity, so the agent (and the Vector Search / catalog its tools touch) runs
  with the *user's own* permissions — not the App's service principal. This is
  what fixes the earlier "no trae nada" symptom (SP lacked read perms).
- Requires enabling **User Authorization** on the App with the right scopes and
  user consent; after changing scopes the App must be restarted.
- Optional env var `DATABRICKS_AGENT_ENDPOINT` (defaults to
  `mas-724bb4d1-endpoint`).
- On **Replit / local** the header is absent → the chat returns an explicit
  "sin conexión" message (NOT demo data). Real answers only come from Databricks.
- The user token is never logged and never sent to the frontend.

## Response parsing

- `get_final_message` walks the `output` array from the end and returns the
  text of the last assistant `message` item; it skips tool results (items with a
  `call_id`) and marker-only payloads (`<name>...</name>`), so intermediate
  narration and tool calls are ignored.
- If no substantive assistant message exists, it returns "El agente no generó
  una respuesta final." (surfaced to the UI with `isError: true`).
- Assistant error messages are filtered out of the conversation before it is
  sent back to the agent, so past errors never pollute the context.
- The trace's step 3 includes the **full** response JSON (pretty-printed) so the
  user can diagnose the agent's raw output in "Ver seguimiento".

## Running locally (Replit)

Two workflows run in parallel:

- **Start application** (frontend): `npm run dev --prefix frontend` → port 5000.
- **Backend**: `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload`.

## Deploying to a Databricks App

1. Build the front-end: `npm run build --prefix frontend` (outputs `frontend/dist`).
2. Upload the project files to the workspace folder and select it as the App source.
   **`frontend/dist` MUST be included** — Databricks Apps only run uvicorn and do
   NOT build the front-end. If `dist` is missing, the backend has no static files
   to serve at `/` and returns `{"detail":"Not Found"}`. For this reason
   `frontend/dist` is intentionally NOT gitignored so it ships with the deploy.
3. `app.yaml` runs `uvicorn backend.main:app`, which serves both the API and the
   built React app. The agent endpoint defaults to `mas-724bb4d1-endpoint`
   (override with `DATABRICKS_AGENT_ENDPOINT`).
4. Grant the App's service principal permission to query the endpoint
   (*Can Query* on the serving endpoint).

## User preferences

- The user communicates in Spanish; respond in Spanish.
- The user works primarily on the front-end and wants it deployable without a
  live Databricks connection (graceful offline message locally, no demo data).
- The front-end is React (migrated from the original Streamlit version).
