// The trial run: 20 users (10 pairs) chat for 3 minutes, one message each
// about every 5 s (~4 messages/s). Checks that everything works end to end
// before the real scenarios.
import { fakeUser, optionsFor, summaryFor } from "./lib.js";

const plan = { users: 20, chatFrom: 10, chatUntil: 190, gap: () => 5, closeAt: 205 };

export const options = optionsFor(plan);
export default () => fakeUser(plan);
export const handleSummary = summaryFor("trial", plan);
