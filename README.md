# CodeOptimise

CodeOptimise uses a React frontend and a FastAPI backend that now persists optimization runs in PostgreSQL through SQLAlchemy and Alembic.

## Backend architecture

The backend is organized under `backend/fastapi_app`:

- `routers` for HTTP endpoints
- `services` for optimization and persistence workflows
- `repositories` for database access
- `models` for SQLAlchemy entities
- `schemas` for Pydantic request and response models
- `database.py` and `dependencies.py` for engine, session, base, and FastAPI dependencies
- `alembic` for schema migrations

## Local setup

1. Create a Python environment and install backend dependencies:

```bash
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` if you need custom values.

3. Start PostgreSQL, then run the FastAPI API from the project root:

```bash
docker compose up -d postgres
uvicorn main:app --reload
```

If your terminal is already in `backend/`, use that same command there:

```bash
uvicorn main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive API docs are at
`http://127.0.0.1:8000/docs`.

## Deploy the backend to Render

This repository includes a Render Blueprint in `render.yaml`. In the Render
dashboard, select **New +** → **Blueprint**, connect the GitHub repository, and
deploy it. Render will create the `codeoptimise-api` web service and its
PostgreSQL database, apply migrations on startup, and expose `/health` as the
health check.

Before deploying, replace the `ALLOWED_ORIGINS` value in `render.yaml` with
your deployed frontend URL (or add it later in the service's environment
variables). The backend is started with Render's assigned `PORT`.

4. Alternatively, start the complete frontend and backend stack with Docker Compose:

```bash
docker compose up --build
```

The backend runs on `http://localhost:8000` and the frontend runs on `http://localhost:5173`.

When the frontend is deployed to Vercel and the backend is deployed to Render,
set this Vercel environment variable to the public backend URL:

```env
VITE_API_BASE_URL=https://codeoptimiser.onrender.com
```

The frontend uses this Render URL by default in production, but the environment
variable is recommended if the backend hostname changes.

## PostgreSQL configuration

Environment variables are loaded from the project `.env` file and passed into Docker Compose:

- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `POSTGRES_PORT`
- `DATABASE_URL`
- `ALLOWED_ORIGINS`
- `AUTO_MIGRATE`

## Optional Gemini AI Insights

AI Insights is an optional explanation layer. The existing static analyzer and optimizer remain the source of truth; Gemini receives the source code plus the analyzer's current findings only to explain them and suggest possible improvements.

1. Install the updated backend dependencies:

```bash
pip install -r requirements.txt
```

2. Add this value to your local `.env` or your backend host's secret environment settings. Do not use a frontend `VITE_` variable and do not commit `.env`:

```env
GEMINI_API_KEY=your_google_ai_studio_key
# Optional; defaults to gemini-2.5-flash
GEMINI_MODEL=gemini-2.5-flash
```

For Render, set `GEMINI_API_KEY` in the backend service's environment variables
after applying the Blueprint. The `sync: false` setting in `render.yaml` keeps
the secret out of the repository and prompts Render to supply it during setup.

3. Run an analysis or optimizer job, then select **AI Insights** in the UI. The UI sends the existing analyzer results to `POST /ai/insights`, where the backend calls Gemini through Google's official `google-genai` Python SDK.

The feature provides a summary, code and issue explanations, suggestions, and an optional refactored-code suggestion. It has its own loading/error state. If no key is configured or Gemini is unavailable, `/ai/insights` returns `503`; analysis, optimization, metrics, and saved-history workflows continue normally.

The FastAPI app waits for PostgreSQL during startup and runs `alembic upgrade head` automatically, so the schema is created without a manual migration step.

## Backend endpoints

Existing frontend-facing endpoints are unchanged:

- `POST /analysis`
- `POST /metrics`
- `POST /ai/insights` (optional Gemini explanation service)
- `POST /optimize`
- `POST /optimise`
- `POST /optmise`

Persistence CRUD endpoints were added:

- `GET /optimizations`
- `GET /optimizations/{id}`
- `PUT /optimizations/{id}`
- `DELETE /optimizations/{id}`

## Development notes

- `backend/create_tables.py` now waits for the database and applies Alembic migrations.
- The initial migration lives in `backend/alembic/versions/20260713_000001_initial_optimization_records.py`.
- `backend/tests/test_optimization_api.py` covers analysis plus optimization create, read, update, and delete flows.
