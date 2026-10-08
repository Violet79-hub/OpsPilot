import os
import tempfile
from pathlib import Path
import pytest

_test_dir = tempfile.TemporaryDirectory(prefix="opspilot-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_test_dir.name) / "test.db")
os.environ["DEMO_WRITES"] = "true"
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("OPSPILOT_ADMIN_TOKEN", None)


@pytest.fixture(scope="session", autouse=True)
def database():
    from app.db.repository import init_db
    from app.db.seed import seed

    init_db()
    seed()


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        yield c
