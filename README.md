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
cd backend
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` if you need custom values.

3. Start PostgreSQL and the app stack with Docker Compose:

```bash
docker compose up --build
```

The backend runs on `http://localhost:8000` and the frontend runs on `http://localhost:5173`.

## PostgreSQL configuration

Environment variables are loaded from the project `.env` file and passed into Docker Compose:

- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `POSTGRES_PORT`
- `DATABASE_URL`
- `ALLOWED_ORIGINS`
- `AUTO_MIGRATE`

The FastAPI app waits for PostgreSQL during startup and runs `alembic upgrade head` automatically, so the schema is created without a manual migration step.

## Backend endpoints

Existing frontend-facing endpoints are unchanged:

- `POST /analysis`
- `POST /metrics`
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
