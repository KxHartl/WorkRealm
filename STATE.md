# STATE — WorkRealm

- **Version:** 0.4.0 · **Repo:** <https://github.com/KxHartl/WorkRealm> (private)
- **Owner:** KxHartl, who picks and approves each release
- **Phase:** 0.2.0–0.4.0 done. Waiting for the owner's review before 0.5.0.
- **Pairs with:** AgentBrain 2.4.0 (`228d56c`), which has the work agents and sync scripts.

## Goal

A single command that gives AI-agent work a Git-backed workspace with rules, memory and
guard-rails sized to the job. It is the work-oriented sibling of LiteRealm, distilled from
KEV-Ai-Architecture. Rules have to bind every tool the owner uses (Claude Code, Gemini CLI /
Antigravity, Codex / Cursor), not only Claude Code.

## What exists

- **0.2.0 enforcement core:**
  - `.ai/policy.py` holds every machine-checked rule once;
  - versioned `.githooks/` run it on every commit, from any tool;
  - every rule in `_RULES.md` has an ID and an enforcement tag, and a test keeps tags and checks
    in step;
  - `GEMINI.md` shim.
- **0.3.0 Claude ergonomics:**
  - `.ai/wr.py` helpers and the skills that wrap them;
  - SessionStart puts STATE.md and status into context, also after compaction;
  - `bash_guard`, the status line, and permission entries.
- **0.4.0 AgentBrain:**
  - `wr new` / `wr upgrade` / `wr sync [--check]` sync work agents and skills per tier;
  - the brain version is pinned in `.workrealm.json`;
  - a missing brain only warns.
- **Tests:** 36 end-to-end tests. They exercise every git check through plain `git commit`, plus
  every helper, skill, hook and sync path. AgentBrain has its own `tests/test_sync.py` (5 tests,
  in its CI).

## Next (see `docs/PLAN.md`)

1. **0.5.0 maintenance:**
   - `wr doctor [--ci] [--fix]`: `core.hooksPath`, remote/unpushed, template drift, rule-ID
     contract, AgentBrain pin (`wr sync --check`), and no secrets in `.mcp.json`.
   - `wr adopt`: bring KEV under WorkRealm without moving files. Do a dry run on a copy first.
2. **0.6.0 integrations:**
   - `wr new --with github,jira,m365,rag` MCP templates (verify the server packages against
     current docs);
   - `--ticket`;
   - a CI workflow that runs `wr doctor --ci`.

## Notes

- **`core.hooksPath` is local config.** A fresh clone must run `git config core.hooksPath .githooks`.
- **Pushes fail silently.** The post-commit push runs in the background with its output thrown
  away, so a failed push makes no noise. To check, compare `git ls-remote origin main` with `HEAD`.
- **Windows consoles.** Hook messages stay ASCII, and stderr/stdout are reconfigured so that a
  non-ASCII path cannot crash a hook.
- **Don't cry wolf.** `test_scaffold_passes_its_own_checks_silently` must keep passing. Release
  snapshots are exempt from the zone checks because they hold copies on purpose.
- **Verified Claude Code behaviour (2026-10-12 docs):**
  - SessionStart stdout reaches the model, and the `compact` source fires after compaction;
  - PreCompact output does not reach the model;
  - the status line runs through Git Bash on Windows;
  - deny lists support `!` exceptions.
- **Escaping in shell heredocs.** In this environment, a heredoc mangles backslashes in Python
  code. Write patch scripts to a file instead.
- **Tests and the real brain.** Tests set `AGENTBRAIN_PATH` to a missing path by default, so the
  real `~/.agentbrain` never shapes a result. The sync tests build a fixture brain with the real
  sync scripts.
- **This repo is not a workspace.** It has no `.githooks/` of its own, so its commits are checked by
  `AGENTS.md` and the tests only.
