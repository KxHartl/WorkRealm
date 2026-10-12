---
name: checkpoint
description: Commit the current logical unit of work with a Conventional Commit message, after the WorkRealm policy checks. Use after finishing any logical unit (a fix, a note, a decision, a source), before switching topic, and before ending a response.
argument-hint: "[type: what changed]"
---

Commit the work done so far as one logical unit (rule R-COMMIT in AGENTS.md).

1. Look at `git status --short` and `git diff --stat` to see what changed.
2. Choose a Conventional Commit subject: `feat|fix|docs|chore|refactor|test: what changed`.
   Use `$ARGUMENTS` as the subject if it was given and fits.
3. Write a one- or two-sentence body that says **why**. A body is required when
   `30-decisions/` changed.
4. Run `python .ai/checkpoint.py "<subject>" "<body>"`.
5. If it is refused, read the rule ID in the message, fix the cause, and run it again.
   Never bypass the check.
