## Communication

{{CHAT_LANG}} **Documents, code, comments and commit messages:** English.

## Context first

Read `STATE.md` before doing anything — it is the only memory that survives between sessions.
Update it whenever the goal, the next step or a blocker changes.

## Commit every logical unit, immediately

- After each logical unit of work: `python .ai/checkpoint.py "type: what changed"`.
  Do not wait for the end of the task, and do not wait to be asked.
- Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:` …). The body says **why**.
- The `post-commit` hook pushes every commit when a remote exists. A local-only commit is one
  disk failure from gone.
- Before finishing a response, `git status --porcelain` must be empty. The Stop hook enforces it.

## Secrets never enter Git

Secrets live in `.env`, which is gitignored; `.env.example` carries the shape, never the values.
`checkpoint.py` refuses to commit files that look like secrets. If one is committed anyway:
**stop, do not push, rotate the secret.**

## Verify, don't recall

Claims about current tool behaviour — versions, APIs, limits, prices, licences — are checked
against current documentation before they are written down or acted on. Cite where it came from.

## Stay in scope

Do what was asked. If the work turns out bigger than this tier was set up for, say so and suggest
`wr upgrade --to <tier>` instead of growing structure ad hoc.
