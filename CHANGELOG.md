# Changelog

## 0.1.0 — 2026-10-12

First version.

- `wr new` with three tiers: `quick`, `task` (default, no flag), `project`.
- `wr upgrade --to task|project`: additive only; keeps user files and the project-specific
  section of `AGENTS.md`.
- Hooks: `checkpoint_gate` (all), `protect_paths` (task+), `zone_guard` (project).
- `checkpoint.py` commit helper with a secrets check; `post-commit` auto-push.
- Private GitHub repo by default for task and project.
