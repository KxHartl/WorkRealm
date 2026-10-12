# STATE — WorkRealm

- **Version:** 0.1.0 · **Repo:** <https://github.com/KxHartl/WorkRealm> (private)
- **Owner:** KxHartl, who picks the next roadmap item
- **Phase:** v0.1.0 shipped; waiting for the owner to pick the next item

## Goal

A single command that gives AI-agent work a Git-backed workspace with rules, memory and
guard-rails sized to the job. It is the work-oriented sibling of LiteRealm, distilled from
KEV-Ai-Architecture.

## What v0.1.0 contains

- **`wr new NAME`** with three tiers. `quick` uses `--quick`, `task` is the default and takes
  no flag, and `project` uses `--project`. Other options: `--dir`, `--lang match|en|hr`,
  `--remote` / `--no-remote` (task and project default to a private GitHub repo).
- **`wr upgrade --to task|project`** only adds files. It rewrites the generated rules block of
  `AGENTS.md` and the `hooks` key of `.claude/settings.json`. It never overwrites user files and
  refuses to downgrade.
- **Tiers** live in `tiers/{quick,task,project}/`, and each is an overlay on the tier below.
  The rules come from each tier's `_RULES.md` and are joined into `AGENTS.md` between markers.
- **Hooks:**
  - `checkpoint_gate` runs as the Stop hook in every tier.
  - `protect_paths` keeps evidence folders write-once (task and up).
  - `zone_guard` keeps decision documents in `30-decisions/` and blocks copies across zones
    (project tier).
- **Commit tooling:** `checkpoint.py` commits with a secrets check. A `post-commit` hook pushes
  every commit and does nothing when there is no remote.
- **Tests:** `tests/test_wr.py` has 13 end-to-end tests. They scaffold every tier, run upgrade
  and its preservation guarantees, and exercise every hook.

## Roadmap (not started; the owner picks the order)

1. **Work agents:** specialist agents for work, kept in `~/.agentbrain/agents/work/` and synced
   into each workspace according to its tier.
2. **`wr adopt`:** bring an existing folder (for example KEV) under WorkRealm without moving
   anything.
3. **`wr doctor`:** check hooks, the remote, the post-commit hook, and drift from the template.

## Notes

- The `post-commit` hook lives in `.git/hooks/`, so a fresh clone does not have it. Reinstall
  it from `POST_COMMIT` in `wr.py`. `wr doctor` should eventually catch this.
- The hook pushes in the background and discards all output, so a failed push makes no noise.
  To check, compare `git ls-remote origin main` with `HEAD`. Verified working on 2026-10-12
  (commit `cec5234`).
