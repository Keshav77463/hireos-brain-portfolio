import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app import db
from app.config import get_settings
from app.main import app


@pytest.fixture(autouse=True)
def single_connection_pool(monkeypatch, request):
    if request.node.get_closest_marker("unit"):

        def forbidden_database_access():
            raise AssertionError("A unit test attempted to access the database.")

        monkeypatch.setattr(db, "get_engine", forbidden_database_access)
        yield None
        return
    # A one-connection pool forces the next request to reuse the same connection.
    engine = create_engine(
        get_settings().database_url, pool_size=1, max_overflow=0, hide_parameters=True
    )
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    yield engine
    engine.dispose()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
