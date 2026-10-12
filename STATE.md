# STATE — WorkRealm

- **Version:** 0.5.0 · **Repo:** <https://github.com/KxHartl/WorkRealm> (private)
- **Owner:** KxHartl, who picks and approves each release
- **Phase:** 0.5.0 (universal layout) is done. Waiting for the owner's review before 0.6.0.
- **Pairs with:** AgentBrain 2.5.0 (`b652b10`), whose work agents use the 0.5.0 layout.

## Goal

A universal generator for workspaces where AI agents do real work. Rules bind every tool through
Git, the layout is familiar, the right way is one command, and the specialists are shared through
AgentBrain. The goals and the design are in `docs/DESIGN.md`.

## What exists

- **Commands:** `wr new` (quick / task / project), `wr upgrade` (additive), `wr sync [--check]`
  (AgentBrain).
- **Layout:** `docs/{notes,decisions,plans}`, `references/` (+ `inbox/`), `src/`, `tests/`,
  `reports/`, `data/{raw,processed}`, `experiments/<date-topic>/results/<run>/`, `releases/`,
  `archive/`. It is stored as data in `.workrealm.json`.
- **Policy core:** `.ai/policy.py`, run by the git hooks (every tool) and by the Claude hooks
  `session_start`, `checkpoint_gate`, `bash_guard`, `protect_paths` and `zone_guard`.
- **Helpers:** `.ai/wr.py` (`note`, `source add|promote`, `decide`, `open-item`, `close-item`,
  `plan new`, `adr new`, `exp new`, `run new`, `release cut`, `status`, `handoff`) and 10 skills
  that wrap them.
- **AI marking:** applied to subagent work only, set by the hook from `agent_id`.
- **Tests:** 41 end-to-end tests. AgentBrain has `tests/test_sync.py` (5 tests, in its CI).

## Next (see `docs/DESIGN.md`)

1. **0.6.0:** `wr doctor [--ci] [--fix]`, and `wr adopt [--dry-run]` for any existing folder,
   tested on generic fixtures.
2. **0.7.0:** `--with github,jira,m365,rag` MCP templates (verify the packages first), `--ticket`,
   and a GitHub workflow that runs `wr doctor --ci`.

## Notes

- **`core.hooksPath` is local config.** A fresh clone must run `git config core.hooksPath .githooks`.
- **Pushes fail silently.** The post-commit push runs in the background with its output thrown
  away, so a failed push makes no noise. To check, compare `git ls-remote origin main` with `HEAD`.
- **Keep tool files ASCII-safe.** Hook messages stay ASCII, and the Croatian letters in `policy.py`
  must stay `\u` escapes. The file-writing tool has turned them into literal letters twice;
  `test_scaffold_passes_its_own_checks_silently` catches it.
- **Escaping in shell heredocs.** In this environment, a heredoc mangles backslashes in Python
  code. Write patch scripts to a file instead.
- **Verified Claude Code behaviour (2026-10-12 docs):**
  - SessionStart stdout reaches the model, and the `compact` source fires after compaction;
  - PreCompact output does not;
  - hooks run inside a subagent get `agent_id` and `agent_type`;
  - PreToolUse `updatedInput` replaces the whole input;
  - deny lists support `!` exceptions.
- **Tests and the real brain.** Tests set `AGENTBRAIN_PATH` to a missing path by default, so the
  real `~/.agentbrain` never shapes a result. The sync tests build a fixture brain with the real
  scripts.
- **This repo is not a workspace.** It has no `.githooks/` of its own, so its commits are checked by
  `AGENTS.md` and the tests only.
