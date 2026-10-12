# STATE — WorkRealm

- **Version:** 0.2.0 · **Repo:** <https://github.com/KxHartl/WorkRealm> (private)
- **Owner:** KxHartl, who picks and approves each release
- **Phase:** 0.2.0 (enforcement core) is done. Waiting for the owner to review it before 0.3.0.

## Goal

A single command that gives AI-agent work a Git-backed workspace with rules, memory and
guard-rails sized to the job. It is the work-oriented sibling of LiteRealm, distilled from
KEV-Ai-Architecture. Rules have to bind every tool the owner uses (Claude Code, Gemini CLI /
Antigravity, Codex / Cursor), not only Claude Code.

## What exists (0.2.0)

- **`wr new NAME`** creates a workspace at one of three tiers: `quick`, `task` (the default) and
  `project`.
- **`wr upgrade --to task|project`** adds files, refreshes the tool-owned `.ai/` and `.githooks/`,
  and installs the git hooks.
- **`.ai/policy.py`** holds every machine-checked rule once. It is called by:
  - the git hooks in `.githooks/` (through `core.hooksPath`), which bind every tool;
  - the Claude hooks `protect_paths` and `zone_guard`;
  - `checkpoint.py`.
- **Rule IDs.** Every rule in `tiers/*/_RULES.md` has an ID and an enforcement tag.
  `TestRuleContract` checks the tags against `policy.ENFORCES` and the checks enabled per tier.
- **Shims:** `GEMINI.md` and `CLAUDE.md` both import `AGENTS.md`.
- **Tests:** 24 end-to-end tests. Every git check is exercised through a plain `git commit`.

## Next: the roadmap, in order (see `docs/PLAN.md`)

1. **0.3.0 Claude ergonomics:**
   - SessionStart hook (injects STATE.md, tier and git status) and PreCompact hook;
   - a Bash write guard and a `permissions` block;
   - a status line;
   - `.ai/wr.py` helpers (`decide`, `open-item`, `source add`, `adr new`, `exp new`, `run new`,
     `release cut`, `handoff`) and the skills that wrap them.
2. **0.4.0 AgentBrain:**
   - In AgentBrain: `sync_agents.py` gains `--tier`, multiple namespaces, `--prune` and per-agent
     `tools`; a new `sync_skills.py`; work agents in `agents/work/`; `min_workrealm_version` in the
     manifest.
   - In WorkRealm: `wr sync` and the AgentBrain pin.
3. **0.5.0:** `wr doctor` and `wr adopt` (try adopt on a copy of KEV).
4. **0.6.0:** `--with github,jira,m365,rag` MCP templates, `--ticket`, and the CI workflow.

## Notes

- **`core.hooksPath` is local config.** A fresh clone must run `git config core.hooksPath .githooks`.
  `wr doctor` (0.5.0) should catch a missing one.
- **Pushes fail silently.** The post-commit push runs in the background with its output thrown
  away, so a failed push makes no noise. To check, compare `git ls-remote origin main` with `HEAD`.
- **Windows consoles.** Hook messages must stay ASCII (cp1252 consoles garble em dashes), and
  stderr is reconfigured so that a non-ASCII path cannot crash a hook.
- **Don't cry wolf.** `TestNew.test_scaffold_passes_its_own_checks_silently` checks that a fresh
  workspace passes every check with no output. Keep it that way: a guard that always fires stops
  being read.
- **This repo is not a workspace.** It has no `.githooks/` of its own, so its commits are checked by
  `AGENTS.md` and the tests only.
