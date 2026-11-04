// c. Connection storm (D33): 1,000 users get their access tokens first (10 a
// second), then all open their live lines within 10 s (ticket, line, hello),
// stay connected for a minute (pings), and hang up. No messages. Measures the
// time to connect, errors, and line open → hello, where each copy's
// subscribe lock sits (D23). The spread between A and B is read from the
// dashboard's "Open live lines per copy".
import { fakeUser, optionsFor, summaryFor } from "./lib.js";

const STORM_AT = 120;
const plan = {
  users: 1000,
  connectAt: () => STORM_AT + Math.random() * 10,
  // No sending: the chat window is empty.
  chatFrom: 190,
  chatUntil: 190,
  gap: () => 20,
  closeAt: 190,
};

export const options = optionsFor(plan);
export default () => fakeUser(plan);
export const handleSummary = summaryFor("c-storm", plan);
