import os

import psycopg
import pytest
from psycopg.conninfo import make_conninfo
from psycopg.errors import InsufficientPrivilege


@pytest.fixture
def app_conn(db_url):
    password = os.environ.get("APP_DB_PASSWORD", "varta_api")
    url = make_conninfo(db_url, user="varta_api", password=password)
    with psycopg.connect(url, autocommit=True) as c:
        yield c


def test_app_login_is_restricted_role(app_conn):
    assert app_conn.execute("SELECT current_user").fetchone()[0] == "varta_api"
    is_super = app_conn.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
    assert is_super.fetchone()[0] is False


def test_app_login_cannot_modify_audit_log(app_conn):
    app_conn.execute(
        "INSERT INTO audit_log (tenant_id, action, target) "
        "VALUES (gen_random_uuid(), 'test', '{}')"
    )
    with pytest.raises(InsufficientPrivilege):
        app_conn.execute("UPDATE audit_log SET action = 'changed'")
    with pytest.raises(InsufficientPrivilege):
        app_conn.execute("DELETE FROM audit_log")


def test_new_tables_get_app_grants(conn):
    conn.execute("CREATE TABLE tmp_default_priv_check (id int)")
    ok = conn.execute(
        "SELECT has_table_privilege('varta_api', 'tmp_default_priv_check', 'INSERT')"
    ).fetchone()[0]
    assert ok is True  # fixture rolls back, so the table is not kept


def test_indexes_and_checks_exist(conn):
    idx = {r[0] for r in conn.execute(
        "SELECT indexname FROM pg_indexes WHERE indexname IN "
        "('tenant_members_user_id_idx', 'devices_user_id_idx')"
    )}
    assert idx == {"tenant_members_user_id_idx", "devices_user_id_idx"}
    chk = {r[0] for r in conn.execute(
        "SELECT conname FROM pg_constraint WHERE conname IN "
        "('messages_text_has_body', 'messages_media_has_attachment')"
    )}
    assert chk == {"messages_text_has_body", "messages_media_has_attachment"}
