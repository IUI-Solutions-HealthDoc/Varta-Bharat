# @varta/sync

Platform-agnostic sync engine shared by mobile and web. Owner: MOB-1 (protocol changes need
BE-1 + MOB-1 sign-off).

Implements plan v2 section 7.4 once, for every client:
outbox with retries on the same `client_msg_id`, delivered/read cursors, reconnect and gap
repair, buffered live frames applied in `seq` order.

Storage adapters: op-sqlite + SQLCipher (React Native), IndexedDB (web).
Tested with Vitest and fast-check against a scripted fake server (section 11); invariants
I1 to I6 from section 7.1 must hold.
