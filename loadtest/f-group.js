// f. One 50-member group (T35, D37): every member has the group open and sends
// "read" for what arrives (at most once a second, like the app), like scenario
// b's pairs. 2 messages/s for 3 minutes, then 5/s for 3 minutes. Each message
// fans out to 49 people. A read goes to the reader's own tabs, and the whole
// group hears only when its lowest bookmark moves (D20, D37). This measures the
// fan-out: end to end to every member, pushes per second, and CPU
// (docs/load-test.md).
import { fakeUser, optionsFor, summaryFor } from "./lib.js";

const USERS = 50;
const RATES = [2, 5]; // messages per second, the whole group together
const STEP_S = 180;
// 50 users start 10 a second: all connected after ~5 s.
const CHAT_FROM = 20;

const rateAt = (t) => RATES[Math.min(RATES.length - 1, Math.max(0, Math.floor((t - CHAT_FROM) / STEP_S)))];

const plan = {
  users: USERS,
  group: true,
  fanout: USERS - 1,
  // READS=off: nobody sends "read", so no receipts, only the messages' own fan-out.
  reads: __ENV.READS !== "off",
  chatFrom: CHAT_FROM,
  chatUntil: CHAT_FROM + RATES.length * STEP_S,
  // One member's gap: 50 members at 2 messages/s means each sends every 25 s.
  gap: (t) => USERS / rateAt(t),
  stage: (t) => String(rateAt(t)),
  closeAt: CHAT_FROM + RATES.length * STEP_S + 30,
};

export const options = optionsFor(plan, {
  // Each step's numbers on their own, like scenario d (the same 500 ms / 1% limit, D33).
  thresholds: Object.fromEntries(
    RATES.flatMap((rate) => [
      [`e2e_latency{stage:${rate}}`, ["p(95)<500"]],
      [`send_failed{stage:${rate}}`, ["rate<0.01"]],
      [`msgs_sent{stage:${rate}}`, ["count>=0"]],
      [`msgs_received{stage:${rate}}`, ["count>=0"]],
      [`send_time{stage:${rate}}`, ["p(95)>=0"]],
    ]),
  ),
});
export default () => fakeUser(plan);
export const handleSummary = summaryFor(plan.reads ? "f-group" : "f-group-no-reads", plan);
