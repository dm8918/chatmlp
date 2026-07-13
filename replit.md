# ChatMLP — Cerebro

React chat front-end ("Cerebro", Los Pelambres) for a Databricks agent served as
a Databricks Serving Endpoint, with a FastAPI backend.

## Architecture

- `frontend/`: React + Vite + TypeScript single-page app (the Cerebro chat UI).
  - Dev server runs on `0.0.0.0:5000` and proxies `/api/*` to the backend.
  - Conversation history persists in the browser's localStorage.
- `backend/main.py`: FastAPI app (HTTP layer + trace + offline handling).
- `backend/functions/call_agent_functions.py`: Databricks invocation logic.
  - `init_workspace_client()`: builds a `WorkspaceClient` (SDK) or returns
    `None` when auth can't be resolved (e.g. local/Replit).
  - `call_agent(client, endpoint, messages)`: calls the agent via
    `client.api_client.do(POST /serving-endpoints/{endpoint}/invocations,
    body {"input": clean_messages})`. Mirrors the notebook code the user
    verified working.
  - `get_final_message(response)`: returns the LAST assistant message's text
    from the `output` list (ignores intermediate narration / tool calls).
  - `POST /api/chat`: runs the above and returns
    `{role, type, content, trace, isError}` — `trace` is a step-by-step log
    (client init, request, response, parsing) shown in the UI under
    "Ver seguimiento".
  - `GET /api/health`: reports whether the WorkspaceClient could initialise.
  - In production it also serves the built React app from `frontend/dist`.
- `app.yaml`: run command for Databricks Apps (`uvicorn backend.main:app`).
- `requirements.txt`: fastapi, uvicorn, databricks-sdk.

## Auth model

- The backend uses the **Databricks SDK** (`WorkspaceClient`), which resolves
  authentication automatically and refreshes short-lived tokens per request.
  The successfully-created client is cached; a failed init is NOT cached (so a
  transient failure doesn't pin the app offline until restart).
- Optional env var `DATABRICKS_AGENT_ENDPOINT` (defaults to
  `mas-c7a80bc8-endpoint`).
- On **Databricks Apps** the service principal credentials are injected
  automatically — `WorkspaceClient()` needs no extra config.
- On **Replit / local** there are intentionally NO credentials:
  `WorkspaceClient()` fails to init → the chat returns an explicit "sin
  conexión" message (NOT demo data). Real answers only come from Databricks.
- No tokens/secrets are ever sent to the frontend.

## Response parsing

- `get_final_message` walks the `output` array from the end and returns the
  text of the last assistant `message` item, so intermediate narration
  ("Voy a consultar...") and tool calls are naturally skipped.
- If no assistant message with text exists, it returns "No se encontró una
  respuesta final del agente." (surfaced to the UI with `isError: true`).
- Assistant error messages are filtered out of the conversation before it is
  sent back to the agent, so past errors never pollute the context.

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
   built React app. The agent endpoint defaults to `mas-c7a80bc8-endpoint`
   (override with `DATABRICKS_AGENT_ENDPOINT`).
4. Grant the App's service principal permission to query the endpoint
   (*Can Query* on the serving endpoint).

## User preferences

- The user communicates in Spanish; respond in Spanish.
- The user works primarily on the front-end and wants it deployable without a
  live Databricks connection (graceful offline message locally, no demo data).
- The front-end is React (migrated from the original Streamlit version).
