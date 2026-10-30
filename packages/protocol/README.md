# @varta/protocol

TypeScript types generated from the server. Do not edit by hand.

Plan v2 section 6: Pydantic models in `server/` are the single source of truth. They are
exported as OpenAPI (REST) and JSON Schema (WebSocket frames, section 7.3), and the TS types
here are generated from those files. CI fails if the generated types are stale.

Export the OpenAPI document from the server:

```bash
cd server && uv run python -m scripts.export_openapi ../packages/protocol/openapi.json
```
