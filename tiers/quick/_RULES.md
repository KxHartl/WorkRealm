## How these rules bind

Each rule carries an ID and says what enforces it. **git** means `.githooks/` refuses a commit
that breaks it, whichever tool or person makes the commit; **claude** means a Claude Code hook
also stops it before the file is written; **advisory** means only this text holds it, so it
depends on you. The checks live in `.ai/policy.py`; their messages quote the rule ID.
Never bypass a check with `--no-verify`. If a check is wrong, say so and fix the check.

## Communication

> **R-LANG** · enforced by: git

{{CHAT_LANG}} **Documents, code, comments and commit messages:** English. The pre-commit check
warns (never blocks) when non-English text is added outside `10-research/sources/`; quoting a
source verbatim is fine.

## Context first

> **R-STATE** · advisory

Read `STATE.md` before doing anything — it is the only memory that survives between sessions.
Update it whenever the goal, the next step or a blocker changes.

## Commit every logical unit, immediately

> **R-COMMIT** · enforced by: git, claude

- After each logical unit of work: `python .ai/checkpoint.py "type: what changed"`.
  Do not wait for the end of the task, and do not wait to be asked.
- Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:` …), checked on every commit.
  The body says **why**.
- The `post-commit` hook pushes every commit when a remote exists. A local-only commit is one
  disk failure from gone.
- Before finishing a response, `git status --porcelain` must be empty. The Claude Stop hook
  enforces it; in other tools it is on you.

## Secrets never enter Git

> **R-SECRETS** · enforced by: git

Secrets live in `.env`, which is gitignored; `.env.example` carries the shape, never the values.
Commits containing files that look like secrets are refused. If one is committed anyway:
**stop, do not push, rotate the secret.**

## Verify, don't recall

> **R-VERIFY** · advisory

Claims about current tool behaviour — versions, APIs, limits, prices, licences — are checked
against current documentation before they are written down or acted on. Cite where it came from.

## Stay in scope

> **R-SCOPE** · advisory

Do what was asked. If the work turns out bigger than this tier was set up for, say so and suggest
`wr upgrade --to <tier>` instead of growing structure ad hoc.
