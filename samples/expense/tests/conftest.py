from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import bootstrap, deps
from app.main import app
from app.repository import db


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = str(tmp_path / "test.sqlite3")
    monkeypatch.setattr(db, "DEFAULT_DB_PATH", path)
    bootstrap.ensure_database(path)
    return path


@pytest.fixture
def conn(db_path):
    connection = db.connect(db_path)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def client(db_path):
    # 本番と同じく deps.get_conn がリクエストごとに接続を開く。db_path が
    # DEFAULT_DB_PATH を差し替えているので、向き先だけが一時DBになる。
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def as_user(client):
    def _switch(user_id: int):
        client.cookies.set(deps.SESSION_COOKIE, str(user_id))
        return client

    return _switch
