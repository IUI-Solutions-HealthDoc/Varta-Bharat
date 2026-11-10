import pytest
import valkey
from psycopg.pq import TransactionStatus

from app.config import settings
from app.core import db
from app.core.valkey import get_valkey


@pytest.fixture
def pool(db_url, monkeypatch):
    monkeypatch.setattr(settings, "database_url", db_url)
    db.close_pool()
    yield
    db.close_pool()


def test_get_conn_has_no_open_transaction(pool):
    with db.get_conn() as conn:
        assert conn.info.transaction_status == TransactionStatus.IDLE
        with conn.transaction():
            assert conn.info.transaction_status == TransactionStatus.INTRANS
        assert conn.info.transaction_status == TransactionStatus.IDLE


def test_valkey_roundtrip():
    client = get_valkey()
    try:
        client.ping()
    except valkey.ConnectionError:
        pytest.skip("valkey not running")
    client.set("test:core", "ok", ex=5)
    assert client.get("test:core") == "ok"
