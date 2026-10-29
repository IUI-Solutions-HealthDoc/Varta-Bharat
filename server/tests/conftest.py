import psycopg
import pytest

from tests.helpers import TEST_URL, ensure_db, upgrade


@pytest.fixture(scope="session")
def db_url() -> str:
    ensure_db(TEST_URL)
    upgrade(TEST_URL)
    return TEST_URL


@pytest.fixture
def conn(db_url):
    with psycopg.connect(db_url) as c:
        c.execute("TRUNCATE tenants, users, audit_log RESTART IDENTITY CASCADE")
        c.commit()
        yield c
        c.rollback()
