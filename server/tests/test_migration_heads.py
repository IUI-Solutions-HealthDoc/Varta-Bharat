from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

SERVER_DIR = Path(__file__).resolve().parent.parent


def test_alembic_has_a_single_head():
    cfg = Config(str(SERVER_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(SERVER_DIR / "migrations"))
    heads = ScriptDirectory.from_config(cfg).get_heads()
    assert len(heads) == 1, (
        f"Multiple Alembic heads: {sorted(heads)}. Two migrations share the same "
        "down_revision. Rebase one onto the other (claim the next number in the "
        "pinned migrations issue)."
    )
