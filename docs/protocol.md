# Varta Bharat Protocol Specification (v1.0)
**Plan v2: Sections 7.2 – 7.4 (Messaging & Realtime Gateway)**  
**Author:** BE-1 (Ajay) – Messaging & Realtime Lead  
**Date:** 30 Oct 2026 (P0 Day-0 Contract)

---

## 1. Overview & Core Invariants

Varta Bharat provides guaranteed, ordered, gapless messaging with idempotent retries and realtime push delivery via WebSocket.

### Core Invariants Guaranteed by BE-1:
- **Invariant I1 (Idempotency):** Submitting a message with an already processed `client_msg_id` within the same conversation returns the existing message `{seq, id, created_at}` without creating a duplicate.
- **Invariant I2 (Gapless Sequences):** For any conversation, message `seq` strictly increments $1, 2, 3, \dots, N$. Failed or rejected sends roll back and never burn sequence numbers.
- **Invariant I3 (Monotonic Cursors):** Delivery and read cursors (`delivered_seq`, `read_seq`) only move forward. `read_seq` can never exceed `delivered_seq`.
- **Invariant I4 (Visibility Boundary):** A client will never receive messages with `seq < visible_from_seq`, nor can any messages be retrieved for conversations where membership has ended (`left_at IS NOT NULL`).
- **Invariant I5 (Deterministic Realtime Hint):** Messages $\le 4\text{ KB}$ are delivered directly over the WebSocket `msg` frame. Messages $> 4\text{ KB}$ are broadcast as lightweight `msg_hint` frames, prompting the client to fetch via REST.

---

## 2. Authentication & Headers

All REST requests require the standard Bearer authentication header:
```http
Authorization: Bearer <access_token>
```

When changing state, clients SHOULD supply an idempotency header:
```http
X-Idempotency-Key: <uuid>
```

---

## 3. REST API Specifications

Base URL: `/v1`

### 3.1 Send Message
Send a text or media message to a conversation.

- **Endpoint:** `POST /v1/conversations/{conversation_id}/messages`
- **Permissions:** Active conversation member (`cm.left_at IS NULL` and user status `active`). In announcement channels, sender must be an admin.
- **Idempotency:** Driven by `client_msg_id`. Retrying with the same `client_msg_id` returns the previously committed message with `duplicate: true`.

#### Request Body (`SendMessageRequest`)
```json
{
  "client_msg_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "kind": "text",
  "body": "Namaste Bharat! This is our first message.",
  "attachment_id": null,
  "enc_scheme": 0
}
```

Field details:
- `client_msg_id` (UUID, Required): Client-generated UUIDv4 for deduplication.
- `kind` (string, Required): `"text"` or `"media"`. (`"system"`, `"delete"`, `"edit"` are server-only).
- `body` (string, Optional): Message content (max 8000 characters). Automatically normalized to Unicode NFC.
- `attachment_id` (UUID, Optional): Required when `kind = "media"`. Must reference an attachment in `ready` state owned by sender.
- `enc_scheme` (integer, Optional): Encryption scheme version (default `0` = plaintext/server-managed).

#### Response Body (`SendMessageResponse`) – HTTP 201 Created / 200 OK
```json
{
  "seq": 42,
  "id": "0192df78-8bc4-7123-93df-520e5e4860b0",
  "created_at": "2026-10-30T10:15:30.123456Z",
  "duplicate": false
}
```

#### Error Codes:
- `400 Bad Request`: Body exceeds 8000 characters or missing attachment for media.
- `403 Forbidden`: Sender is not an active member, is blocked, or lacks admin privileges in announcement channel.
- `404 Not Found`: Conversation does not exist.
- `422 Unprocessable Entity`: Validation failure on input schema.

---

### 3.2 Sync Active Conversations
Fetch all active conversation memberships and current synchronization cursors.

- **Endpoint:** `GET /v1/sync/conversations`
- **Permissions:** Active authenticated user.

#### Response Body (`SyncConversationsResponse`) – HTTP 200 OK
```json
{
  "conversations": [
    {
      "conversation_id": "c1a2b3c4-d5e6-7f80-91a2-b3c4d5e6f7a8",
      "last_seq": 150,
      "delivered_seq": 148,
      "read_seq": 140,
      "visible_from_seq": 1
    },
    {
      "conversation_id": "d2b3c4d5-e6f7-8091-a2b3-c4d5e6f7a8b9",
      "last_seq": 25,
      "delivered_seq": 25,
      "read_seq": 25,
      "visible_from_seq": 10
    }
  ]
}
```

---

### 3.3 List Messages (Pagination & Sync Catch-up)
Fetch ordered messages within a conversation after a given sequence number.

- **Endpoint:** `GET /v1/conversations/{conversation_id}/messages`
- **Query Parameters:**
  - `after` (integer, Optional, default `0`): Retrieve messages with `seq > after`. Cannot be less than `visible_from_seq - 1`.
  - `limit` (integer, Optional, default `50`, max `200`): Maximum messages to return.

#### Response Body (`GetMessagesResponse`) – HTTP 200 OK
```json
{
  "messages": [
    {
      "conversation_id": "c1a2b3c4-d5e6-7f80-91a2-b3c4d5e6f7a8",
      "seq": 149,
      "id": "0192df78-8bc4-7123-93df-520e5e4860a1",
      "sender_id": "e3c4d5e6-f7a8-8091-a2b3-c4d5e6f7a8c0",
      "client_msg_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
      "kind": "text",
      "target_seq": null,
      "body": "Checking in on the deployment status.",
      "attachment_id": null,
      "enc_scheme": 0,
      "created_at": "2026-10-30T10:14:00.000000Z"
    },
    {
      "conversation_id": "c1a2b3c4-d5e6-7f80-91a2-b3c4d5e6f7a8",
      "seq": 150,
      "id": "0192df78-8bc4-7123-93df-520e5e4860b0",
      "sender_id": "f4d5e6f7-a8b9-8091-a2b3-c4d5e6f7a8d1",
      "client_msg_id": "b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e",
      "kind": "text",
      "target_seq": null,
      "body": "All services healthy on Postgres 18 and Valkey.",
      "attachment_id": null,
      "enc_scheme": 0,
      "created_at": "2026-10-30T10:15:30.123456Z"
    }
  ],
  "has_more": false,
  "last_seq": 150
}
```

---

## 4. WebSocket Gateway Protocol (`/v1/ws`)

### 4.1 Connection Lifecycle
1. **Ticket Request:** Client obtains a single-use, 30-second ticket via `POST /v1/ws-ticket` (Member 2).
2. **Connection:** Client establishes a WebSocket connection to `ws(s)://<host>/v1/ws`.
3. **Handshake:** Client immediately transmits a `hello` frame containing the ticket.
4. **Welcome:** Server validates the ticket, subscribes the connection to Valkey channels for the user's active conversations, and sends a `welcome` frame with heartbeat interval (`heartbeat_s = 25`).
5. **Keepalive:** Both client and server must adhere to standard WebSocket ping/pong frames every 25 seconds.

---

### 4.2 Upstream Frames (Client $\rightarrow$ Server)

#### A. Handshake (`hello`)
Must be the first frame sent after opening the socket.
```json
{
  "type": "hello",
  "ticket": "wstk_8f91a2c3d4e5f67890abcdef"
}
```

#### B. Acknowledgment (`ack`)
Update message delivery and read receipts. Cursors must only move forward.
```json
{
  "type": "ack",
  "conversation_id": "c1a2b3c4-d5e6-7f80-91a2-b3c4d5e6f7a8",
  "delivered_seq": 150,
  "read_seq": 145
}
```

#### C. Typing Indicator (`typing` – P2)
Broadcast typing activity to conversation members.
```json
{
  "type": "typing",
  "conversation_id": "c1a2b3c4-d5e6-7f80-91a2-b3c4d5e6f7a8",
  "is_typing": true
}
```

---

### 4.3 Downstream Frames (Server $\rightarrow$ Client)

#### A. Welcome Frame (`welcome`)
Sent immediately upon successful ticket authentication.
```json
{
  "type": "welcome",
  "heartbeat_s": 25,
  "user_id": "e3c4d5e6-f7a8-8091-a2b3-c4d5e6f7a8c0",
  "device_id": "0192df70-1234-7abc-8def-000000000001"
}
```

#### B. Realtime Message Frame (`msg` – Body $\le 4\text{ KB}$)
Full message payload sent directly to online clients.
```json
{
  "type": "msg",
  "conversation_id": "c1a2b3c4-d5e6-7f80-91a2-b3c4d5e6f7a8",
  "seq": 151,
  "id": "0192df78-8bc4-7123-93df-520e5e4860c2",
  "sender_id": "e3c4d5e6-f7a8-8091-a2b3-c4d5e6f7a8c0",
  "kind": "text",
  "body": "Realtime notification received!",
  "attachment_id": null,
  "created_at": "2026-10-30T10:16:00.000000Z"
}
```

#### C. Message Hint Frame (`msg_hint` – Body $> 4\text{ KB}$ or large media)
Prompts the client to fetch the complete message via REST `GET /v1/conversations/{id}/messages?after=...`.
```json
{
  "type": "msg_hint",
  "conversation_id": "c1a2b3c4-d5e6-7f80-91a2-b3c4d5e6f7a8",
  "seq": 152,
  "id": "0192df78-8bc4-7123-93df-520e5e4860d3",
  "sender_id": "e3c4d5e6-f7a8-8091-a2b3-c4d5e6f7a8c0",
  "kind": "media",
  "created_at": "2026-10-30T10:16:30.000000Z"
}
```

#### D. Receipt Frame (`receipt`)
Informs participants of updated delivery/read cursors from other users.
```json
{
  "type": "receipt",
  "conversation_id": "c1a2b3c4-d5e6-7f80-91a2-b3c4d5e6f7a8",
  "user_id": "f4d5e6f7-a8b9-8091-a2b3-c4d5e6f7a8d1",
  "delivered_seq": 151,
  "read_seq": 151
}
```

#### E. Device Revocation Frame (`revoked` – P2)
Sent if Member 2 revokes the session/device, followed by immediate socket termination.
```json
{
  "type": "revoked",
  "reason": "Session invalidated by device logout or security policy"
}
```

#### F. Error Frame (`error`)
```json
{
  "type": "error",
  "code": "INVALID_FRAME",
  "message": "Malformed JSON payload or unauthenticated ticket"
}
```

---

## 5. Reconnection & Catch-Up Protocol
When a client reconnects after being offline:
1. Client connects to `/v1/ws` and presents a fresh ticket.
2. Client calls `GET /v1/sync/conversations` to get the server's `last_seq` for each conversation.
3. For any conversation where local `highest_seq < last_seq`, client fetches missed messages via `GET /v1/conversations/{id}/messages?after={highest_seq}&limit=200`.
4. Client sends an `ack` frame over WebSocket to advance server-side `delivered_seq` and `read_seq`.
