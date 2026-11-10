"""Write the API's OpenAPI document to a file (plan v2 section 6: server is the source of truth).

Usage: uv run python -m scripts.export_openapi ../packages/protocol/openapi.json
"""

import json
import sys
from pathlib import Path

from app.main import app


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("openapi.json")
    out.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
