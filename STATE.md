# STATE — WorkRealm

- **Version:** 0.7.0 · **Repo:** <https://github.com/KxHartl/WorkRealm> (private)
- **Owner:** KxHartl, who picks and approves each release
- **Phase:** 0.7.0 (integrations, tickets, CI) is done. Waiting for the owner's review.
- **Pairs with:** AgentBrain 2.6.0 (`15c62be`): work agents for the 0.5.0 layout, and the RAG MCP
  server that `--with rag` starts.

## Goal

A universal generator for workspaces where AI agents do real work. Rules bind every tool through
Git, the layout is familiar, the right way is one command, and the specialists are shared through
AgentBrain. The goals and the design are in `docs/DESIGN.md`.

## What exists

- **Commands:** `wr new` (quick / task / project, `--with`, `--ticket`), `wr integrate`,
  `wr upgrade` (additive), `wr sync [--check]` (AgentBrain), `wr doctor [--fix] [--ci]`, and
  `wr adopt PATH [--dry-run]` (any folder, moves nothing).
- **Integrations:** `.mcp.json` entries for `github` (remote server, `${GITHUB_PAT}`) and `rag`
  (AgentBrain over stdio via `.ai/rag_server.py`). Tickets: `ticket start`, `Refs:` trailers,
  R-TICKET (warns). CI: `.github/workflows/workrealm.yml` runs `policy.py ci` (task and up).
- **Layout:** `docs/{notes,decisions,plans}`, `references/` (+ `inbox/`), `src/`, `tests/`,
  `reports/`, `data/{raw,processed}`, `experiments/<date-topic>/results/<run>/`, `releases/`,
  `archive/`. It is stored as data in `.workrealm.json`. Rules are defined per role and expanded per
  workspace, so adopted folders keep their own names.
- **Policy core:** `.ai/policy.py`, run by the git hooks (every tool) and by the Claude hooks
  `session_start`, `checkpoint_gate`, `bash_guard`, `protect_paths` and `zone_guard`.
- **Helpers:** `.ai/wr.py` (`ticket start`, `note`, `source add|promote`, `decide`, `open-item`, `close-item`,
  `plan new`, `adr new`, `exp new`, `run new`, `release cut`, `status`, `handoff`) and 10 skills
  that wrap them.
- **AI marking:** applied to subagent work only, set by the hook from `agent_id`.
- **Tests:** 61 end-to-end tests, with generic adopt fixtures (a code repo, a research folder). AgentBrain has `tests/test_sync.py` and `tests/test_rag_mcp.py` (in its CI).

## Next (see `docs/DESIGN.md`)

1. The owner reviews 0.7.0. Then, in an order the owner picks:
   - an on-demand `.ai/REFERENCE.md`;
   - a devcontainer / GitHub-template path;
   - the RAG server over HTTP for other devices (AgentBrain already has `--http`; the laptop
     needs autostart, a firewall rule and a token), when the owner's other project needs it.

## Notes

- **`core.hooksPath` is local config.** A fresh clone needs `wr doctor --fix` (or `git config core.hooksPath .githooks`).
- **Pushes fail silently.** The post-commit push runs in the background with its output thrown
  away, so a failed push makes no noise. `wr doctor` reports unpushed commits, and `--fix` pushes them.
- **Keep tool files ASCII-safe.** Hook messages stay ASCII, and the Croatian letters in `policy.py`
  must stay `\u` escapes. The file-writing tool has turned them into literal letters twice;
  `test_scaffold_passes_its_own_checks_silently` catches it.
- **Escaping in shell heredocs.** In this environment, a heredoc mangles backslashes in Python
  code. Write patch scripts to a file instead.
- **Verified for 0.7.0 (2026-10-16 docs):** `.mcp.json` expands `${VAR}` and `${VAR:-default}`
  in `command`, `args`, `env`, `url` and `headers`; an unset variable stays literal with a warning.
  Claude Code sets `CLAUDE_PROJECT_DIR` in a spawned stdio server's environment (not in its own,
  so `args` cannot use it without a default), and asks before using project servers. GitHub's
  remote server takes a PAT in `Authorization` and `X-MCP-Toolsets` (comma-separated).
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
