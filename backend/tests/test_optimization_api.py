from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sys
from unittest.mock import patch

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
    os.environ["GEMINI_API_KEY"] = "test-gemini-key"

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
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


def fake_ai_result():
    from backend.fastapi_app.services.ai_provider import AIOptimizationResult

    return AIOptimizationResult(
        optimized_code="def sum_values(values):\n    return sum(values)\n",
        explanation="Replaced the manual loop with Python's built-in sum for clarity and efficiency.",
        time_complexity_before="O(n)",
        time_complexity_after="O(n)",
        space_complexity_before="O(1)",
        space_complexity_after="O(1)",
        suggestions=["Use built-in functions when they preserve readability and behavior."],
        performance_issues=["Manual accumulation loop detected."],
        better_practices=["Prefer expressive built-ins like sum for simple reductions."],
    )


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
    code = "def sum_values(values):\n    total = 0\n    for value in values:\n        total += value\n    return total\n"

    async def run() -> None:
        client = create_test_client(tmp_path)
        from backend.fastapi_app.services import optimization_service as optimization_service_module

        with patch.object(optimization_service_module, "get_ai_provider") as mock_provider:
            mock_provider.return_value.provider_name = "gemini"
            mock_provider.return_value.optimize_code.return_value = fake_ai_result()

            async with client:
                create_response = await client.post("/optimize", json={"language": "python", "code": code})
                assert create_response.status_code == 200
                created = create_response.json()
                record_id = created["record_id"]
                assert created["optimized_code"]
                assert created["time_complexity_before"] == "O(n)"
                assert created["space_complexity_after"] == "O(1)"
                assert created["suggestions"]

                list_response = await client.get("/optimizations")
                assert list_response.status_code == 200
                list_payload = list_response.json()["items"]
                assert len(list_payload) == 1
                assert list_payload[0]["provider"] == "gemini"

                get_response = await client.get(f"/optimizations/{record_id}")
                assert get_response.status_code == 200
                assert get_response.json()["id"] == record_id
                assert get_response.json()["time_complexity_after"] == "O(n)"

                update_response = await client.put(
                    f"/optimizations/{record_id}",
                    json={"optimized_code": "def sum_values(values):\n    return sum(values)\n"},
                )
                assert update_response.status_code == 200
                assert "sum(values)" in update_response.json()["optimized_code"]

                delete_response = await client.delete(f"/optimizations/{record_id}")
                assert delete_response.status_code == 204

                missing_response = await client.get(f"/optimizations/{record_id}")
                assert missing_response.status_code == 404

    asyncio.run(run())


def test_optimization_endpoint_handles_provider_failures(tmp_path: Path) -> None:
    async def run() -> None:
        from backend.fastapi_app.exceptions import AIProviderTimeoutError

        client = create_test_client(tmp_path)
        from backend.fastapi_app.services import optimization_service as optimization_service_module

        with patch.object(optimization_service_module, "get_ai_provider") as mock_provider:
            mock_provider.return_value.provider_name = "gemini"
            mock_provider.return_value.optimize_code.side_effect = AIProviderTimeoutError("Gemini request timed out")

            async with client:
                response = await client.post("/optimize", json={"language": "python", "code": "print('hello')\n"})
                assert response.status_code == 504
                assert response.json()["detail"] == "Gemini request timed out"

    asyncio.run(run())


def test_optimize_rejects_unsupported_language(tmp_path: Path) -> None:
    async def run() -> None:
        async with create_test_client(tmp_path) as client:
            response = await client.post("/optimize", json={"language": "javascript", "code": "console.log('hi');"})
            assert response.status_code == 400
            assert "Only Python optimization is currently supported" in response.json()["detail"]

    asyncio.run(run())
