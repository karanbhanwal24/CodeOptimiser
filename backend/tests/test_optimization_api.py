from __future__ import annotations

import os
from pathlib import Path
import sys
import asyncio

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def create_test_client(tmp_path: Path):
    database_path = tmp_path / "test.db"
    if database_path.exists():
        database_path.unlink()
    os.environ["DATABASE_URL"] = f"sqlite:///{database_path}"
    os.environ["AUTO_MIGRATE"] = "true"
    os.environ["ALLOWED_ORIGINS"] = "http://localhost:5173,http://127.0.0.1:5173"

    for module_name in list(sys.modules):
        if module_name.startswith("backend.fastapi_app") or module_name.startswith("fastapi_app"):
            sys.modules.pop(module_name)

    from backend.fastapi_app.config import get_settings
    get_settings.cache_clear()
    settings = get_settings()

    from backend.fastapi_app.migrations import run_migrations
    run_migrations(settings.database_url)

    from backend.fastapi_app.main import create_app
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


def test_analysis_endpoint(tmp_path: Path) -> None:
    async def run() -> None:
        async with create_test_client(tmp_path) as client:
            response = await client.post("/analysis", json={"code": "x = 1\nprint(x)\n"})
            assert response.status_code == 200
            payload = response.json()
            assert "issues" in payload
            assert "cyclomatic_complexity" in payload

    asyncio.run(run())


def test_optimization_crud_flow(tmp_path: Path) -> None:
    code = "parts = ['a', 'b']\nresult = ''\nfor part in parts:\n    result += part\nprint(result)\n"

    async def run() -> None:
        async with create_test_client(tmp_path) as client:
            create_response = await client.post("/optimize", json={"code": code})
            assert create_response.status_code == 200
            created = create_response.json()
            record_id = created["record_id"]
            assert created["optimized_code"]

            list_response = await client.get("/optimizations")
            assert list_response.status_code == 200
            assert len(list_response.json()["items"]) == 1

            get_response = await client.get(f"/optimizations/{record_id}")
            assert get_response.status_code == 200
            assert get_response.json()["id"] == record_id

            update_response = await client.put(
                f"/optimizations/{record_id}",
                json={"optimized_code": "values = ['a', 'b']\nprint(''.join(values))\n"},
            )
            assert update_response.status_code == 200
            assert "join" in update_response.json()["optimized_code"]

            delete_response = await client.delete(f"/optimizations/{record_id}")
            assert delete_response.status_code == 204

            missing_response = await client.get(f"/optimizations/{record_id}")
            assert missing_response.status_code == 404

    asyncio.run(run())


def test_ai_insights_validates_input_and_is_optional(tmp_path: Path) -> None:
    """A missing Gemini key must not affect the normal analysis API."""
    os.environ.pop("GEMINI_API_KEY", None)

    async def run() -> None:
        async with create_test_client(tmp_path) as client:
            invalid_response = await client.post("/ai/insights", json={"code": " ", "analysis": {}})
            assert invalid_response.status_code == 422

            unavailable_response = await client.post(
                "/ai/insights",
                json={
                    "code": "x = 1\nprint(x)\n",
                    "analysis": {
                        "issues": [],
                        "issue_count": 0,
                        "complexity_estimate": "low",
                        "cyclomatic_complexity": 1,
                    },
                },
            )
            assert unavailable_response.status_code == 503
            assert "GEMINI_API_KEY" in unavailable_response.json()["detail"]

            analysis_response = await client.post("/analysis", json={"code": "x = 1\nprint(x)\n"})
            assert analysis_response.status_code == 200

    asyncio.run(run())
