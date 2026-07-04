# ChatMLP — Cerebro

React chat front-end ("Cerebro", Los Pelambres) for a Databricks agent served as
a Databricks Serving Endpoint, with a FastAPI backend.

## Architecture

- `frontend/`: React + Vite + TypeScript single-page app (the Cerebro chat UI).
  - Dev server runs on `0.0.0.0:5000` and proxies `/api/*` to the backend.
- `backend/main.py`: FastAPI app.
  - `POST /api/chat`: sends the conversation to the Databricks serving endpoint.
  - `GET /api/health`: reports whether the app is in demo mode.
  - In production it also serves the built React app from `frontend/dist`.
- `app.yaml`: run command for Databricks Apps (`uvicorn backend.main:app`).
- `requirements.txt`: Python dependencies.

## Auth model

- On **Databricks Apps**, authentication is automatic via the service
  principal's OAuth (M2M). `WorkspaceClient()` resolves credentials with no extra
  config, and the backend calls the serving endpoint.
- On **Replit / local**, there are usually no Databricks credentials. The backend
  detects this and runs in **demo mode** (simulated responses) so the front can be
  developed and deployed without connecting to Databricks.

## Running locally (Replit)

Two workflows run in parallel:

- **Start application** (frontend): `npm run dev --prefix frontend` → port 5000.
- **Backend**: `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload`.

## Deploying to a Databricks App

1. Build the front-end: `npm run build --prefix frontend` (outputs `frontend/dist`).
2. Upload the project files to the workspace folder and select it as the App source.
3. `app.yaml` runs `uvicorn backend.main:app`, which serves both the API and the
   built React app. The serving endpoint and workspace host are configured in
   `backend/main.py` (`ENDPOINT_NAME`, `BASE_URL`).
4. Grant the App's service principal permission to query the endpoint.

## User preferences

- The user works primarily on the front-end and wants it deployable without a
  live Databricks connection. Keep the Databricks connection optional/graceful.
- The front-end is React (migrated from the original Streamlit version).
