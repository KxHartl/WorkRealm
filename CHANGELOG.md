# Changelog

## 0.3.0 — 2026-10-12

Claude ergonomics: the right way to do something is one command or one skill.

- `.ai/wr.py` workspace helpers for every tool: `status`, `checkpoint`, `handoff`, `note`,
  `source add`, `decide`, `open-item`, `close-item`, `adr new`, `exp new`, `run new`,
  `prompt new|done`, `release cut`. Each one produces exactly what the policy checks accept.
- Skills that wrap them, per tier: `/checkpoint`, `/handoff`; `/note`, `/source`, `/decide`,
  `/open-item`; `/adr`, `/experiment`, `/release`.
- SessionStart hook: puts STATE.md and the workspace status (branch, uncommitted, unpushed, open
  items) into context, and again after a compaction. PreCompact was not used because its output
  never reaches the model.
- `bash_guard` (PreToolUse on Bash and PowerShell, all tiers): blocks `--no-verify`, moving
  `core.hooksPath`, and shell commands that change or remove write-once files.
- Status line: workspace, tier, branch, uncommitted, unpushed, open items, phase.
- Permissions: secrets are denied to Read; force-push is denied; edits to the guard-rails
  (`.ai/`, `.githooks/`, `.workrealm.json`, `.claude/settings.json`) ask the user first.
  WorkRealm adds its entries and keeps the user's own, and never replaces a status line the user
  set.
- R-STATE is now enforced by Claude (session start). Zone checks exempt `50-release/`, because
  releases are snapshots and hold copies on purpose.

## 0.2.0 — 2026-10-12

Enforcement core: rules bind every tool, not only Claude Code.

- `.ai/policy.py` holds every machine-checked rule once. The Claude hooks, the git hooks and
  `checkpoint.py` all call it.
- Versioned `.githooks/` (`pre-commit`, `commit-msg`, `post-commit`), enabled with
  `core.hooksPath`. These replace the unversioned `.git/hooks/post-commit`.
- New checks: Conventional Commits; English (warning only); sources must be logged and the log is
  append-only; write-once paths also refuse deletions; naming of notes, experiments, prompts,
  ADRs, runs and releases; settled `DECISIONS.md` rows cannot be edited; open items need an owner
  and a trigger; commits touching `30-decisions/` need a body; ADRs need all their sections.
- Every rule in `_RULES.md` has an ID and an enforcement tag. A test checks the tags against
  `policy.ENFORCES` and the checks enabled at each tier.
- `.workrealm.json` gains `checks` and `naming`.
- `wr upgrade` refreshes the tool-owned `.ai/` and `.githooks/` files and installs the git hooks.
- `GEMINI.md` shim (Gemini CLI resolves `@./AGENTS.md` imports).
- Fixes: one decision policy across tiers (rows superseded, ADRs edited with a log row);
  the rules no longer claim that `zone_guard` warns on every crossing; `zone_guard` now also
  checks `notebook_path`.

## 0.1.0 — 2026-10-12

First version.

- `wr new` with three tiers: `quick`, `task` (default, no flag), `project`.
- `wr upgrade --to task|project`: additive only; keeps user files and the project-specific
  section of `AGENTS.md`.
- Hooks: `checkpoint_gate` (all), `protect_paths` (task+), `zone_guard` (project).
- `checkpoint.py` commit helper with a secrets check; `post-commit` auto-push.
- Private GitHub repo by default for task and project.
