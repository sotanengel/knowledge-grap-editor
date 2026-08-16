import tempfile

import pytest
from fastapi.testclient import TestClient

from app.deps import reset_services
from app.main import app


@pytest.fixture
def api_client(monkeypatch):
    reset_services()
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setenv("KG_DATA_DIR", tmpdir)
    reset_services()
    with TestClient(app) as c:
        yield c
    reset_services()
