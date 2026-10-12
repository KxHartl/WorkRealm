# Changelog

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
