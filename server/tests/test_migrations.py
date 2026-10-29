import psycopg

from tests.helpers import TEST_URL, downgrade, ensure_db, upgrade
from psycopg.conninfo import conninfo_to_dict, make_conninfo

EXPECTED = {
    "tenants", "users", "tenant_members", "communities", "conversations",
    "conversation_members", "attachments", "messages", "invitations",
    "contact_nicknames", "user_blocks", "reports", "devices", "audit_log",
}


def _tables(url):
    with psycopg.connect(url) as c:
        rows = c.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        ).fetchall()
    return {r[0] for r in rows}


def test_upgrade_downgrade_upgrade_on_fresh_db():
    info = conninfo_to_dict(TEST_URL)
    info["dbname"] = "varta_migtest"
    url = make_conninfo(**info)
    ensure_db(url, drop=True)

    upgrade(url)
    assert EXPECTED <= _tables(url)

    downgrade(url, "base")
    assert not (EXPECTED & _tables(url))

    upgrade(url)
    assert EXPECTED <= _tables(url)
