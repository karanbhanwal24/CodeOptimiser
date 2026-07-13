# CodeOptimise

CodeOptimise is a full-stack code optimization app with a React + Vite frontend, a FastAPI backend, PostgreSQL persistence, and Gemini-powered code optimization.

## Architecture

The backend is organized under `backend/fastapi_app`:

- `routers` for HTTP endpoints
- `services` for application workflows
- `services/ai_provider.py` for the provider interface
- `services/gemini_service.py` for Gemini-specific integration
- `services/provider_factory.py` for provider selection
- `repositories` for database access
- `models` for SQLAlchemy entities
- `schemas` for Pydantic request and response contracts
- `database.py` and `dependencies.py` for engine, session, base, and FastAPI dependencies
- `alembic` for schema migrations

This provider split keeps the route layer independent from Gemini so you can swap in OpenAI, Groq, or another provider later without rewriting the API.

## Gemini API key

1. Create a Gemini API key in Google AI Studio:
   `https://aistudio.google.com/`
2. Add it to your environment:

```bash
GEMINI_API_KEY=your-google-ai-api-key
```

Required AI environment variables:

- `AI_PROVIDER=gemini`
- `GEMINI_API_KEY=...`
- `GEMINI_MODEL=gemini-3.5-flash`
- `GEMINI_TIMEOUT_SECONDS=20`
- `GEMINI_MAX_RETRIES=2`

The backend uses the official Google GenAI SDK (`google-genai`) and validates Gemini responses against a strict JSON schema before returning them.

## Local setup

1. Install backend dependencies:

```bash
cd backend
pip install -r requirements.txt
```

2. Install frontend dependencies:

```bash
cd frontend
npm install
```

3. Copy `.env.example` to `.env` and fill in `GEMINI_API_KEY`.

4. Start everything with Docker:

```bash
docker compose up --build
```

Services:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Backend health: `http://localhost:8000/health`

## Docker setup

Docker Compose starts:

- PostgreSQL
- FastAPI backend
- Vite frontend

The backend container receives:

- PostgreSQL connection settings
- CORS settings
- Gemini provider settings

On startup, the backend waits for PostgreSQL and runs Alembic migrations automatically.

## API

### Optimize code

`POST /optimize`

Request:

```json
{
  "language": "python",
  "code": "def sum_values(values):\n    total = 0\n    for value in values:\n        total += value\n    return total"
}
```

Response:

```json
{
  "optimized_code": "def sum_values(values):\n    return sum(values)",
  "explanation": "Replaced the manual loop with Python's built-in sum.",
  "time_complexity_before": "O(n)",
  "time_complexity_after": "O(n)",
  "space_complexity_before": "O(1)",
  "space_complexity_after": "O(1)",
  "suggestions": [
    "Prefer expressive built-ins when they preserve behavior."
  ]
}
```

Additional optimization data returned:

- `performance_issues`
- `better_practices`
- `record_id`
- `provider`

Existing endpoints remain available:

- `POST /analysis`
- `POST /metrics`
- `POST /optimize`
- `POST /optimise`
- `POST /optmise`
- `GET /optimizations`
- `GET /optimizations/{id}`
- `PUT /optimizations/{id}`
- `DELETE /optimizations/{id}`

## Database

Each optimization is stored in PostgreSQL with:

- programming language
- AI provider
- original code
- optimized code
- AI explanation
- time complexity before/after
- space complexity before/after
- suggestions
- timestamp

Schema changes are managed through Alembic migrations.

## Frontend behavior

The React frontend now:

- sends `language` and `code` to the backend
- shows a loading state while optimization runs
- displays optimized code
- shows AI explanation, suggestions, better practices, and performance issues
- shows time and space complexity before and after optimization
- keeps optimization history from PostgreSQL
- surfaces backend errors through the existing error banner

## Testing

Backend tests include:

- API tests for optimization CRUD
- provider failure handling tests
- unsupported language validation tests
- unit tests for the Gemini service with mocked SDK responses

Run backend tests:

```bash
cd backend
pytest
```

Run frontend build validation:

```bash
cd frontend
npm run build
```

## Deployment notes

### Render

Set these backend environment variables in Render:

- `DATABASE_URL`
- `ALLOWED_ORIGINS`
- `ALLOWED_ORIGIN_REGEX`
- `AUTO_MIGRATE=true`
- `AI_PROVIDER=gemini`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `GEMINI_TIMEOUT_SECONDS`
- `GEMINI_MAX_RETRIES`

### Vercel

Set:

- `VITE_API_BASE_URL=https://your-render-backend-url`

If you use preview deployments on Vercel, `ALLOWED_ORIGIN_REGEX=^https://.*\.vercel\.app$` allows those origins for CORS.

## File summary

Created:

- `backend/fastapi_app/services/ai_provider.py`
- `backend/fastapi_app/services/gemini_service.py`
- `backend/fastapi_app/services/provider_factory.py`
- `backend/alembic/versions/20260713_000002_add_ai_optimization_fields.py`
- `backend/tests/test_gemini_service.py`

Modified:

- `backend/fastapi_app/config.py`
- `backend/fastapi_app/exceptions.py`
- `backend/fastapi_app/models/optimization.py`
- `backend/fastapi_app/schemas/optimization.py`
- `backend/fastapi_app/schemas/__init__.py`
- `backend/fastapi_app/services/optimization_service.py`
- `backend/fastapi_app/routers/optimizations.py`
- `frontend/src/App.jsx`
- `backend/requirements.txt`
- `backend/fastapi_app/requirements.txt`
- `requirements.txt`
- `docker-compose.yml`
- `.env`
- `.env.example`
- `.github/workflows/ci.yml`

Why these changes were made:

- Provider abstraction isolates Gemini from route logic and makes future providers swappable.
- Structured schema validation protects the app from malformed model output.
- New DB columns persist AI-specific optimization data.
- Frontend updates surface explanation, complexity comparison, and suggestions directly in the UI.
- Tests mock Gemini so CI does not depend on external API calls.
