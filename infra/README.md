# infra

Owner: OPS-1. Plan v2 D-11 and section 11.

- IaC for one India region (RCM's cloud account if any; default AWS Mumbai): managed
  PostgreSQL 18 with point-in-time recovery, S3-compatible object storage, Valkey primary +
  replica + Sentinel, containers behind a load balancer.
- `k6/`: HTTP + WebSocket load scripts (target 3x the modeled peak, section 5).
- `toxiproxy/`: fault-injection scenarios for the invariant checker (section 11).
- CERT-In: logs kept 180 days in-region; clocks synced to NIC/NPL NTP (section 9.2).
