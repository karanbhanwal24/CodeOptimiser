from fastapi_app.config import get_settings
from fastapi_app.migrations import run_migrations, wait_for_database


if __name__ == "__main__":
    settings = get_settings()
    wait_for_database(settings.database_url)
    run_migrations(settings.database_url)
