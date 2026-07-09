# ChatMLP — Cerebro

React chat front-end ("Cerebro", Los Pelambres) for a Databricks agent served as
a Databricks Serving Endpoint, with a FastAPI backend.

## Architecture

- `frontend/`: React + Vite + TypeScript single-page app (the Cerebro chat UI).
  - Dev server runs on `0.0.0.0:5000` and proxies `/api/*` to the backend.
  - Conversation history persists in the browser's localStorage.
- `backend/main.py`: FastAPI app.
  - `POST /api/chat`: sends the conversation to the Databricks agent via the
    endpoint's **invocations API**
    (`POST {host}/serving-endpoints/{endpoint}/invocations`, body `{input}`),
    the same call shape verified working from a Databricks notebook.
    (The generic `/serving-endpoints/responses` route did NOT work for this
    agent endpoint.)
    Returns `{role, type, content, trace}` — `trace` is a step-by-step log
    (auth, request sent, HTTP response, parsing) shown in the UI under
    "Ver seguimiento".
  - `GET /api/health`: reports whether Databricks credentials are configured.
  - In production it also serves the built React app from `frontend/dist`.
- `app.yaml`: run command for Databricks Apps (`uvicorn backend.main:app`).
- `requirements.txt`: fastapi, uvicorn, requests (no databricks-sdk / openai).

## Auth model

- OAuth **M2M client credentials**: the backend requests a token from
  `{DATABRICKS_HOST}/oidc/v1/token` (Basic auth, `grant_type=client_credentials`,
  `scope=all-apis`) and caches it until shortly before expiry (thread-safe).
- Env vars used (read lazily, never at import): `DATABRICKS_HOST`,
  `DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET`, and optionally
  `DATABRICKS_AGENT_ENDPOINT` (defaults to `mas-c7a80bc8-endpoint`).
- On **Databricks Apps** these env vars are injected automatically for the
  App's service principal — no manual config needed.
- On **Replit / local** there are intentionally NO credentials: the chat
  returns an explicit "sin conexión" message (NOT demo data). There is no demo
  mode anymore — real answers only come from Databricks.
- Tokens / client_secret are never sent to the frontend (the trace only logs
  host, payload and response snippets).

## Response parsing (agent quirks)

- The agent may return `function_call` items plus weak intermediate text like
  "Voy a consultar..." — those are NEVER treated as the final answer.
- If there is a `function_call` but no substantive final text, the backend
  returns a controlled error about tool-calling/permissions.
- Databricks may return HTTP 200 with an SSE error block
  (`event: error` / `data: {...}`); the backend parses `error_code`/`message`.

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
