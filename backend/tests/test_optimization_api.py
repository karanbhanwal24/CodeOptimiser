from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import httpx


# Add the backend directory to Python's import path.
# Structure:
# CodeOptimise/
# └── backend/
#     ├── fastapi_app/
#     └── tests/
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def create_test_client(tmp_path: Path):
    database_path = tmp_path / "test.db"

    if database_path.exists():
        database_path.unlink()

    # Test database configuration
    os.environ["DATABASE_URL"] = f"sqlite:///{database_path}"
    os.environ["AUTO_MIGRATE"] = "true"
    os.environ["ALLOWED_ORIGINS"] = (
        "http://localhost:5173,http://127.0.0.1:5173"
    )

    # Disable Gemini for tests.
    # AI is optional, so tests should work without a Gemini API key.
    os.environ["GEMINI_API_KEY"] = ""

    # Reload application modules so test settings are used.
    for module_name in list(sys.modules):
        if (
            module_name.startswith("backend.fastapi_app")
            or module_name.startswith("fastapi_app")
        ):
            sys.modules.pop(module_name)

    from fastapi_app.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()

    from fastapi_app.migrations import run_migrations

    run_migrations(settings.database_url)

    from fastapi_app.main import create_app

    app = create_app()

    transport = httpx.ASGITransport(app=app)

    return httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    )


def test_analysis_endpoint(tmp_path: Path) -> None:
    async def run() -> None:
        async with create_test_client(tmp_path) as client:
            response = await client.post(
                "/analysis",
                json={"code": "x = 1\nprint(x)\n"},
            )

            assert response.status_code == 200

            payload = response.json()

            assert "issues" in payload
            assert "cyclomatic_complexity" in payload

    asyncio.run(run())


def test_optimization_crud_flow(tmp_path: Path) -> None:
    code = (
        "parts = ['a', 'b']\n"
        "result = ''\n"
        "for part in parts:\n"
        "    result += part\n"
        "print(result)\n"
    )

    async def run() -> None:
        async with create_test_client(tmp_path) as client:

            # Create optimization
            create_response = await client.post(
                "/optimize",
                json={"code": code},
            )

            assert create_response.status_code == 200

            created = create_response.json()

            record_id = created["record_id"]

            assert created["optimized_code"]

            # List optimizations
            list_response = await client.get("/optimizations")

            assert list_response.status_code == 200
            assert len(list_response.json()["items"]) == 1

            # Get optimization
            get_response = await client.get(
                f"/optimizations/{record_id}"
            )

            assert get_response.status_code == 200
            assert get_response.json()["id"] == record_id

            # Update optimization
            update_response = await client.put(
                f"/optimizations/{record_id}",
                json={
                    "optimized_code": (
                        "values = ['a', 'b']\n"
                        "print(''.join(values))\n"
                    )
                },
            )

            assert update_response.status_code == 200
            assert "join" in update_response.json()["optimized_code"]

            # Delete optimization
            delete_response = await client.delete(
                f"/optimizations/{record_id}"
            )

            assert delete_response.status_code == 204

            # Verify deletion
            missing_response = await client.get(
                f"/optimizations/{record_id}"
            )

            assert missing_response.status_code == 404

    asyncio.run(run())


def test_ai_insights_validates_input_and_is_optional(
    tmp_path: Path,
) -> None:
    """
    AI Insights is optional.

    Without a Gemini API key:
    - Invalid input should return 422.
    - Valid AI request should return 503.
    - Normal code analysis should still return 200.
    """

    async def run() -> None:
        async with create_test_client(tmp_path) as client:

            # Invalid request
            invalid_response = await client.post(
                "/ai/insights",
                json={
                    "code": " ",
                    "analysis": {},
                },
            )

            assert invalid_response.status_code == 422

            # Gemini unavailable
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

            assert (
                "GEMINI_API_KEY"
                in unavailable_response.json()["detail"]
            )

            # Existing CodeOptimise analysis must still work
            analysis_response = await client.post(
                "/analysis",
                json={
                    "code": "x = 1\nprint(x)\n",
                },
            )

            assert analysis_response.status_code == 200

    asyncio.run(run())