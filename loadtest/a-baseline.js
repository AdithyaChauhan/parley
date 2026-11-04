// a. Baseline, the T30 question (D33): is the first request after a quiet
// minute slow, and is that the monitoring stack or the laptop? One user, 5
// rounds: a quiet minute, then 4 health checks and 3 real logins in a row.
// The first of each counts as "first", the rest as "warm" (by then both
// copies have answered). run.sh runs it with the monitoring stack on, then off.
import http from "k6/http";
import { sleep } from "k6";
import { Trend } from "k6/metrics";

const ROUNDS = 5;
const QUIET_S = 60;
// The same for every fake user (seed.py).
const PASSWORD = "load-test-password";
const KINDS = ["health_first", "health_warm", "login_first", "login_warm"];

const timing = new Trend("baseline_time", true);

export const options = {
  scenarios: {
    baseline: { executor: "per-vu-iterations", vus: 1, iterations: 1, maxDuration: `${ROUNDS * (QUIET_S + 15) + 60}s` },
  },
  // A threshold per kind makes the summary keep each kind's own numbers.
  thresholds: Object.fromEntries(KINDS.map((kind) => [`baseline_time{kind:${kind}}`, ["max>=0"]])),
  systemTags: ["scenario", "name", "method", "status", "expected_response", "error_code"],
  summaryTrendStats: ["min", "med", "max", "count"],
};

const health = () => http.get(`${__ENV.BASE_URL}/api/health`, { tags: { name: "health" } });
const login = () =>
  http.post(`${__ENV.BASE_URL}/api/auth/login`, JSON.stringify({ email: "load0001@example.com", password: PASSWORD }), {
    headers: { "Content-Type": "application/json" },
    tags: { name: "login" },
  });

export default function () {
  for (let round = 1; round <= ROUNDS; round++) {
    sleep(QUIET_S);
    for (let n = 0; n < 4; n++) timing.add(health().timings.duration, { kind: n === 0 ? "health_first" : "health_warm" });
    for (let n = 0; n < 3; n++) timing.add(login().timings.duration, { kind: n === 0 ? "login_first" : "login_warm" });
  }
}

export function handleSummary(data) {
  const round = (value) => Math.round(value * 10) / 10;
  const kinds = Object.fromEntries(
    KINDS.map((kind) => {
      const v = data.metrics[`baseline_time{kind:${kind}}`].values;
      return [kind, { n: v.count, min_ms: round(v.min), p50_ms: round(v.med), max_ms: round(v.max) }];
    }),
  );
  const results = {
    run: __ENV.RUN_ID,
    scenario: "a-baseline",
    monitoring: __ENV.MONITORING,
    ended_at: new Date().toISOString(),
    duration_s: Math.round(data.state.testRunDurationMs / 1000),
    kinds,
  };
  const text = KINDS.map((k) => `${k.padEnd(13)} p50 ${kinds[k].p50_ms} · max ${kinds[k].max_ms} ms (n=${kinds[k].n})`).join("\n");
  return {
    [`/results/${__ENV.RUN_ID}.json`]: JSON.stringify(results, null, 2) + "\n",
    stdout: `\nmonitoring ${__ENV.MONITORING}\n${text}\n`,
  };
}
