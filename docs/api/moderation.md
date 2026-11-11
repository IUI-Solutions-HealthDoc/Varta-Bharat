# Block and report

All endpoints need an authenticated user and are scoped to the user's tenant.

| Endpoint | Behaviour |
| --- | --- |
| `POST /v1/blocks` `{user_id}` | Block a user in your tenant. Idempotent. 404 if not in your tenant, 422 if yourself. |
| `GET /v1/blocks` | Users you have blocked (`id`, `display_name`). |
| `DELETE /v1/blocks/{user_id}` | Unblock. Idempotent, always 204. |
| `POST /v1/reports` `{conversation_id, seq, reason}` | Report a message you can see (not your own). Reason is 1 to 2000 characters. Repeating an open report returns the same report. |

Blocks work both ways: `blocked_between(conn, a, b)` in `app.moderation.blocks` is true if either user
blocked the other. `send_message` and DM creation must call it. Report text is stored in
`reports.reason` and never logged; the audit entry holds only the report, conversation and seq.