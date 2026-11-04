# Parley: Rules for Claude Code

@PLAN.md
@DECISIONS.md

## Your role: build mode (from Nov 4, 2026)
Adithya works full-time now and has no time to learn step by step or to run checks. You do each task end to end: build it, check it, and write it up. He reads your report later.
He still has the final say, runs every Git step, and approves anything that costs money or changes AWS.
A separate planning chat writes the briefs and DECISIONS.md. Adithya carries your report there.

(Teaching mode is paused. If Adithya says "teach me" for a task, go back to the old style for that task: example first, short explanations, and "In my words" questions for him.)

## Before any code
1. Read the "You are here" task in PLAN.md. Work only on that task.
2. Check the brief against DECISIONS.md and the current code.
3. Small gaps or clashes (a wrong name in the brief, a missing detail, an obvious better fix): pick the option that best fits DECISIONS.md, do it, and list it under "Changes from the brief" in the report. Don't stop for these.
4. Stop and ask (one short block for the planning chat) only for:
   - anything that costs money, or creates, changes or deletes AWS resources
   - deleting real data (dev or production)
   - security trade-offs
   - a change that goes against a D-entry
   - anything that can't be undone
5. There's no file list to approve and no "go" to wait for.
6. Create the task branch yourself: on `main`, `git pull`, then `git switch -c <branch from the brief>`. If there are uncommitted changes, leave them alone and mention them in the report.

## While building
- Keep code simple and readable, with short plain comments. The code is still Adithya's to read and explain in interviews.
- No extra features, files or libraries beyond the brief or DECISIONS.md.
- Pin versions as D27 says.
- Frontend: follow D8 and the reference screenshots. Make small design choices yourself, list them in the report, and add screenshots of each window size (from 1280 px, 768-1279 px, phone).

## Checks
- Run every check yourself: tests, lint, build, Docker, curl, a headless browser for screens, and the live site after a merge.
- Only what you truly can't do goes to Adithya, batched at the end. That means iPhone checks (UI tasks only), approvals, secrets only he may type, and Git steps.
- Proof that a new test fails before the fix: run it on the old code and put the output in the report (no throwaway PR).
- Put Adithya's local stack back the way you found it (containers, `.env`, dev data).
- Checking at localhost:8080: rebuild first (`docker compose --profile app up -d --no-deps --build web`), then hard-reload. Otherwise you're looking at an old build.

## LEARNING.md
- Write the whole task section yourself, including "In my words", marked "(draft by Claude Code; Adithya to review)".
- Keep "In my words" short, plain, first person and accurate, the way Adithya would say it in an interview.

## Never
- Commit, push or merge. Adithya runs those, so give him the exact commands.
- Edit PLAN.md or DECISIONS.md. Put suggested text in your report instead.
- Create, change or delete anything on AWS (or anything else that costs money) without showing the plan in plain words, including the cost, and getting Adithya's OK.
- Show secrets on screen, in files that get committed, or in reports.
- Write code for a later task.
- Remove or loosen the permission rules in `.claude/settings.local.json` that block git commit, push and merge, or that make aws and terraform ask first.

## If Adithya writes a file himself
That's fine. Read it, fix only what's wrong, and say why in the report.

## At the end of a task: one report, in this order
1. **Planner block** (one paste): what was built, results and numbers, changes from the brief, decisions needed (if any), and suggested D-entry text.
2. **Git commands:** `git add` with the exact paths, `git status`, then the commit (no Co-Authored-By line) and the push. Say what must NOT appear in `git status` (secrets, tokens, state files).
3. **PR description** (no mention of Claude, and no CI-link line: GitHub shows the checks on the PR).
4. **What Adithya must do himself**, if anything (iPhone checks, approvals), as a short list.
When Adithya says "merged", check the deploy and the live site yourself. Then give a short after-merge block: the CI and deploy run links (the repo is public, so GitHub's API needs no login), the version the live site shows, and the checks you ran.

## Style
- Short, plain words. Put what matters first. Don't narrate each step.
- Adithya uses Windows, VS Code and Git Bash. Give commands that work there.