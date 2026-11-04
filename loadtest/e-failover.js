// e. Failover under load (D33): 1,000 users chat for 6 minutes while run.sh
// stops backend_a about 2 minutes in. Its ~500 lines close (1012) and
// reconnect to backend_b. Measures how long until every line is back
// (reconnect), how many messages were late or came by catch-up, and that none
// were lost. At ~10 messages/s (each user every ~100 s), not b's 50: at 50
// both copies already freeze without any failover.
import { fakeUser, optionsFor, summaryFor } from "./lib.js";

const plan = { users: 1000, chatFrom: 120, chatUntil: 480, gap: () => 100, closeAt: 510 };

export const options = optionsFor(plan);
export default () => fakeUser(plan);
export const handleSummary = summaryFor("e-failover", plan);
