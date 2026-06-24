from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend" / "fastapi_app"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app as fastapi_app


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
