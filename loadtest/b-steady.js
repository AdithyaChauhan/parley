// b. Steady chat (D33): 1,000 users (500 pairs) connected, each sending one
// message about every 20 s (~50 messages/s) for 10 minutes. Measures send and
// end-to-end p50/p95/p99, errors, and lost messages.
import { fakeUser, optionsFor, summaryFor } from "./lib.js";

// Everyone is connected ~100 s after the start (10 a second), so chat from 120 s.
const plan = { users: 1000, chatFrom: 120, chatUntil: 720, gap: () => 20, closeAt: 750 };

export const options = optionsFor(plan);
export default () => fakeUser(plan);
export const handleSummary = summaryFor("b-steady", plan);
