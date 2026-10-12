## How these rules bind

Each rule carries an ID and says what enforces it. **git** means `.githooks/` refuses a commit
that breaks it, whichever tool or person makes the commit; **claude** means a Claude Code hook
acts on it as it happens (stops the write or command, or loads the context); **advisory** means
only this text holds it, so it
depends on you. The checks live in `.ai/policy.py`; their messages quote the rule ID.
Never bypass a check with `--no-verify`. If a check is wrong, say so and fix the check.

**Use the helpers.** `python .ai/wr.py` does each common step the way the checks accept it:
`status`, `checkpoint`, `handoff`, and at higher tiers `note`, `source add`, `decide`, `open-item`,
`adr new`, `exp new`, `run new`, `release cut` (`--help` lists them). Prefer them to doing it by hand.

## Communication

> **R-LANG** · enforced by: git

{{CHAT_LANG}} **Documents, code, comments and commit messages:** English. The pre-commit check
warns (never blocks) when non-English text is added outside `references/` and `data/raw/`; quoting a
source verbatim is fine.

## Context first

> **R-STATE** · enforced by: claude

Read `STATE.md` before doing anything — it is the only memory that survives between sessions.
In Claude Code the session-start hook prints it with the workspace status, and again after a
context compaction; in other tools, run `python .ai/wr.py status` first.
Update it whenever the goal, the next step or a blocker changes, and before ending a session
(`python .ai/wr.py handoff`).

## Commit every logical unit, immediately

> **R-COMMIT** · enforced by: git, claude

- After each logical unit of work: `python .ai/checkpoint.py "type: what changed"`.
  Do not wait for the end of the task, and do not wait to be asked.
- Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:` …), checked on every commit.
  The body says **why**.
- **AI marking is for work a subagent did on its own.** Its commits get the robot tag in the
  subject and an `AI-Agent: <name>` trailer, added automatically in Claude Code. Work done at the
  user's prompt, by the main agent, is committed unmarked. Never add or remove the mark by hand;
  the two parts must appear together, and a commit with only one is refused.
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
