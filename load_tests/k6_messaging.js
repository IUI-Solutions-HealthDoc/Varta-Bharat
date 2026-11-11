/**
 * Varta Bharat - K6 Concurrency & Load Stress Test Suite (BE-1: P2)
 *
 * Simulates 100 concurrent Virtual Users (VUs) executing high-throughput messaging
 * workloads against Varta Bharat backend:
 * - Monotonic gapless sequence assignment under high write load.
 * - Idempotent deduplication of retries.
 * - Sync cursors retrieval (/v1/sync/conversations).
 * - High-speed message pagination stream (/v1/conversations/:id/messages?after=...).
 *
 * Run with k6:
 *   k6 run load_tests/k6_messaging.js
 *   k6 run --env BASE_URL=http://localhost:8000 --env CONV_ID=<uuid> load_tests/k6_messaging.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// Custom metrics
const sendDuration = new Trend('varta_send_duration', true);
const retryDuration = new Trend('varta_retry_duration', true);
const syncDuration = new Trend('varta_sync_duration', true);
const fetchDuration = new Trend('varta_fetch_duration', true);
const successfulSends = new Counter('varta_successful_sends');
const successfulRetries = new Counter('varta_successful_retries');
const errorRate = new Rate('varta_error_rate');

export const options = {
  stages: [
    { duration: '15s', target: 25 },   // Ramp-up to 25 VUs
    { duration: '30s', target: 100 },  // Ramp-up to 100 concurrent VUs
    { duration: '45s', target: 100 },  // Sustained load at 100 VUs
    { duration: '15s', target: 0 },    // Ramp-down to 0 VUs
  ],
  thresholds: {
    // 95% of all requests must complete within 50ms (Engineering Plan v2 SLA)
    http_req_duration: ['p(95)<50', 'p(99)<100'],
    // Overall HTTP failure rate must stay under 1%
    varta_error_rate: ['rate<0.01'],
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const DEFAULT_CONV_ID = __ENV.CONV_ID || '0192df78-0000-7000-8000-000000000010';
const TEST_USER_ID = __ENV.USER_ID || '0192df78-0000-7000-8000-000000000001';

function generateUUID() {
  // Simple RFC4122 v4 UUID generator for k6 virtual users
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export default function () {
  const convId = DEFAULT_CONV_ID;
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${TEST_USER_ID}`,
  };

  const clientMsgId = generateUUID();

  // ---------------------------------------------------------------------------
  // 1. POST /v1/conversations/{id}/messages (High-throughput message send)
  // ---------------------------------------------------------------------------
  const sendPayload = JSON.stringify({
    client_msg_id: clientMsgId,
    kind: 'text',
    body: `Load stress test frame from VU ${__VU} iteration ${__ITER}`,
    attachment_id: null,
    enc_scheme: 0,
  });

  const sendStart = new Date();
  const sendRes = http.post(`${BASE_URL}/v1/conversations/${convId}/messages`, sendPayload, { headers });
  sendDuration.add(new Date() - sendStart);

  const sendOk = check(sendRes, {
    'send status is 201 or 200': (r) => r.status === 201 || r.status === 200,
    'send has seq': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body && body.seq >= 1;
      } catch (e) {
        return false;
      }
    },
  });

  if (sendOk) {
    successfulSends.add(1);
    errorRate.add(0);
  } else {
    errorRate.add(1);
  }

  // ---------------------------------------------------------------------------
  // 2. Idempotent Retry: Re-submit same client_msg_id (Deduplication verify)
  // ---------------------------------------------------------------------------
  const retryStart = new Date();
  const retryRes = http.post(`${BASE_URL}/v1/conversations/${convId}/messages`, sendPayload, { headers });
  retryDuration.add(new Date() - retryStart);

  const retryOk = check(retryRes, {
    'retry status is 201': (r) => r.status === 201,
    'retry duplicate flag is true': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body && body.duplicate === true;
      } catch (e) {
        return false;
      }
    },
  });

  if (retryOk) {
    successfulRetries.add(1);
    errorRate.add(0);
  } else {
    errorRate.add(1);
  }

  // ---------------------------------------------------------------------------
  // 3. GET /v1/sync/conversations (Active synchronization status check)
  // ---------------------------------------------------------------------------
  const syncStart = new Date();
  const syncRes = http.get(`${BASE_URL}/v1/sync/conversations`, { headers });
  syncDuration.add(new Date() - syncStart);

  const syncOk = check(syncRes, {
    'sync status is 200': (r) => r.status === 200,
    'sync response has conversations': (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body.conversations);
      } catch (e) {
        return false;
      }
    },
  });

  if (syncOk) {
    errorRate.add(0);
  } else {
    errorRate.add(1);
  }

  // ---------------------------------------------------------------------------
  // 4. GET /v1/conversations/{id}/messages?after=0&limit=50 (Catch-up fetch)
  // ---------------------------------------------------------------------------
  const fetchStart = new Date();
  const fetchRes = http.get(`${BASE_URL}/v1/conversations/${convId}/messages?after=0&limit=50`, { headers });
  fetchDuration.add(new Date() - fetchStart);

  const fetchOk = check(fetchRes, {
    'fetch status is 200': (r) => r.status === 200,
    'fetch has messages list': (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body.messages);
      } catch (e) {
        return false;
      }
    },
  });

  if (fetchOk) {
    errorRate.add(0);
  } else {
    errorRate.add(1);
  }

  // Small pacing sleep between VU loop iterations
  sleep(0.05);
}
