"""Write the API's OpenAPI schema to api/openapi.json (used by `npm run gen:api` in web/)."""

import json
from pathlib import Path

from cairn.main import create_app

OUTPUT = Path(__file__).resolve().parent.parent / "openapi.json"

if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(create_app().openapi(), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")
