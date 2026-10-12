# WorkRealm

> A workspace generator for AI-agent work — tasks and projects, not seminars and theses.
> The work-oriented sibling of [LiteRealm](https://github.com/KxHartl/LiteRealm).

One command creates a Git-backed folder with rules, memory and guard-rails sized to the job:

```powershell
python wr.py new MyTask              # task tier — the default, no flag
python wr.py new QuickFix --quick    # quick tier
python wr.py new BigThing --project  # project tier
```

Workspaces are created next to this folder (`C:\Projects\<name>`) unless `--dir` says otherwise.

## The three tiers

Each tier is a **strict extension** of the one below, so `wr upgrade` only ever *adds* files.

| | **quick** | **task** (default) | **project** |
|---|---|---|---|
| For | Hours to a day: a fix, a script, a one-off analysis | Days to weeks: a feature, an evaluation, a report | Weeks to months: architecture, regulated or multi-phase work |
| `AGENTS.md` + `CLAUDE.md` | ✓ | ✓ | ✓ |
| `STATE.md` | Goal · done · next | + focus, waiting-on | + phases, blockers, owner decisions |
| Commit discipline (Stop hook, `checkpoint.py`, auto-push) | ✓ | ✓ | ✓ |
| Secrets check on commit | ✓ | ✓ | ✓ |
| `10-research/` notes + read-only sources + log | | ✓ | ✓ + experiments |
| `30-decisions/` `DECISIONS.md` + `OPEN-ITEMS.md` | | ✓ | ✓ + ADRs, `CONSTRAINTS.md` |
| `src/` | | ✓ | ✓ |
| `20-prompts/`, `40-lab/`, `50-release/`, `90-archive/` | | | ✓ |
| Hooks | `checkpoint_gate` | + `protect_paths` | + `zone_guard` |
| Private GitHub repo by default | no | yes | yes |

The zones are KEV-Ai-Architecture's, distilled: what worked there is the project tier, and the
smaller tiers are what remains when you take away what a short job does not need.

## Commands

```
wr new NAME [--quick | --project] [--dir PARENT] [--lang match|en|hr] [--remote | --no-remote]
wr upgrade --to task|project [--path WORKSPACE]
```

- `--lang` writes the chat-language rule. `match` (default): reply in the user's language.
  Documents, code and commits are always English.
- `upgrade` adds the missing files, rewrites the generated block of `AGENTS.md` (your
  *Project-specific rules* section is kept) and the `hooks` key of `.claude/settings.json`.
  Existing files such as `STATE.md` and `README.md` are never overwritten.

## What every workspace gets

- **`AGENTS.md`** — rules assembled from `tiers/*/_RULES.md`, between markers, plus a
  section that is yours. `CLAUDE.md` imports it.
- **Hooks that bind, not prose that hopes.** The Stop hook will not let an agent finish with
  uncommitted work; `protect_paths` makes evidence folders write-once; `zone_guard` blocks
  decision documents outside `30-decisions/` and copies across zones.
- **A `post-commit` hook that pushes every commit.** Lesson of the September 2026 disk loss:
  a commit that exists only locally is one disk failure from gone. (It lives in `.git/hooks/`,
  so a fresh clone needs it reinstalled — copy it from `wr.py`'s `POST_COMMIT`.)

## Layout of this repo

```
wr.py            the generator (stdlib only, Python ≥ 3.10)
wr.ps1, wr       launchers
tiers/quick/     base files + _RULES.md
tiers/task/      overlay on quick
tiers/project/   overlay on task
tests/           end-to-end: scaffold every tier, exercise every hook
```

Run the tests: `python -m unittest discover tests`

## Roadmap

- Work-oriented specialist agents in `~/.agentbrain/agents/work/`, synced per tier.
- `wr adopt` — bring an existing folder (e.g. KEV) under WorkRealm without moving anything.
- `wr doctor` — check hooks, remote, post-commit and drift from the template.
