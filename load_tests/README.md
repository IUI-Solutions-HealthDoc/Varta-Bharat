# Varta Bharat - Load & Stress Testing Guide (BE-1: P2)

This directory contains load and stress testing scripts using [k6](https://k6.io/) to validate throughput, latency SLAs, and core invariants under high concurrent load (100 Virtual Users).

---

## 1. Prerequisites

Install `k6`:
- **Windows (winget):** `winget install k6 --source winget`
- **macOS (brew):** `brew install k6`
- **Linux (deb):** `sudo apt install k6`
- Or use the official Docker image: `docker run --rm -i grafana/k6 run - <load_tests/k6_messaging.js`

Ensure the backend server is running:
```bash
make up
cd server && uv run uvicorn app.main:app --port 8000
```

---

## 2. Running Load Tests

### Standard Load Test (100 VUs, Ramping Profile):
```bash
k6 run load_tests/k6_messaging.js
```

### Running Against Custom Host / Conversation:
```bash
k6 run --env BASE_URL=http://localhost:8000 \
       --env CONV_ID=<conversation-uuid> \
       --env USER_ID=<user-uuid> \
       load_tests/k6_messaging.js
```

---

## 3. SLA Thresholds & Invariants Verified

| Metric | Target SLA | Description |
|---|---|---|
| `http_req_duration` (p95) | $< 50\text{ ms}$ | 95% of send, sync, and fetch requests complete in < 50ms |
| `http_req_duration` (p99) | $< 100\text{ ms}$ | 99% of requests complete in < 100ms |
| `varta_error_rate` | $< 1.0\%$ | Error rate under peak 100 VU concurrent load |
| **Idempotency** | $100\%$ | Identical `client_msg_id` retries return `duplicate: true` |
| **Gapless `seq`** | Monotonic $1..N$ | No sequence gaps even under 100 concurrent writers |

---

## 4. Fault-Injection Tests

Fault-injection tests verify system resilience under mid-transaction crashes, Valkey outages, and push failures:
```bash
cd server
uv run pytest -v tests/conformance/test_fault_injection.py
```
