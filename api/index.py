from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.fastapi_app.main import app as fastapi_app

async def app(scope, receive, send):
    path = scope.get("path", "")
    if path.startswith("/api"):
        trimmed_path = path[4:] or "/"
        scope = {
            **scope,
            "root_path": "/api",
            "path": trimmed_path,
        }

    await fastapi_app(scope, receive, send)
