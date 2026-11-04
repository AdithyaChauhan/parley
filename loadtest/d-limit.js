// d. Find the limit (D33): 1,000 users raise the message rate step by step,
// 100 s per step. "The limit" is the first step where p95 end to end goes
// over 500 ms or failed sends go over 1%. The steps after it show what
// happens past it.
import { fakeUser, optionsFor, summaryFor } from "./lib.js";

const USERS = 1000;
// Messages per second, all users together. It starts at 10, because b
// showed 50 a second already freezes both copies on this laptop.
const RATES = [10, 20, 30, 40, 50];
const STEP_S = 100;
// Everyone is connected ~100 s after the start (10 a second).
const CHAT_FROM = 120;

// The step running at time t.
const rateAt = (t) => RATES[Math.min(RATES.length - 1, Math.max(0, Math.floor((t - CHAT_FROM) / STEP_S)))];

const plan = {
  users: USERS,
  chatFrom: CHAT_FROM,
  chatUntil: CHAT_FROM + RATES.length * STEP_S,
  // One user's gap: 1,000 users at 100 messages/s means each sends every 10 s.
  gap: (t) => USERS / rateAt(t),
  stage: (t) => String(rateAt(t)),
  closeAt: CHAT_FROM + RATES.length * STEP_S + 30,
};

export const options = optionsFor(plan, {
  // The limit, checked for each step on its own. A failed step doesn't stop
  // the test. msgs_sent per step gives the rate really reached.
  thresholds: Object.fromEntries(
    RATES.flatMap((rate) => [
      [`e2e_latency{stage:${rate}}`, ["p(95)<500"]],
      [`send_failed{stage:${rate}}`, ["rate<0.01"]],
      [`msgs_sent{stage:${rate}}`, ["count>=0"]],
    ]),
  ),
});
export default () => fakeUser(plan);
export const handleSummary = summaryFor("d-limit", plan);
