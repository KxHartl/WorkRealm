# WorkRealm

> A workspace generator for AI-agent work — tasks and projects, not seminars and theses.
> The work-oriented sibling of [LiteRealm](https://github.com/KxHartl/LiteRealm).

Repository: <https://github.com/KxHartl/WorkRealm> (private)

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
| `AGENTS.md` + `CLAUDE.md` + `GEMINI.md` | ✓ | ✓ | ✓ |
| `STATE.md` | Goal · done · next | + focus, waiting-on | + phases, blockers, owner decisions |
| Commit discipline (Stop hook, `checkpoint.py`, auto-push) | ✓ | ✓ | ✓ |
| Git checks, any tool (`.githooks/` → `.ai/policy.py`) | secrets, Conventional Commits, English (warn) | + write-once sources, sources logged, naming, decision register, why-body on decisions | + zone placement, no cross-zone copies, ADR sections |
| `10-research/` notes + read-only sources + log | | ✓ | ✓ + experiments |
| `30-decisions/` `DECISIONS.md` + `OPEN-ITEMS.md` | | ✓ | ✓ + ADRs, `CONSTRAINTS.md` |
| `src/` | | ✓ | ✓ |
| `20-prompts/`, `40-lab/`, `50-release/`, `90-archive/` | | | ✓ |
| Claude Code hooks | `session_start`, `checkpoint_gate`, `bash_guard` | + `protect_paths` | + `zone_guard` |
| Helpers (`python .ai/wr.py …`) and skills | `status`, `checkpoint`, `handoff` | + `note`, `source add`, `decide`, `open-item` | + `adr new`, `exp new`, `run new`, `prompt`, `release cut` |
| Status line, permissions (secrets unreadable, guard-rail edits ask) | ✓ | ✓ | ✓ |
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
  *Project-specific rules* section is kept), the `hooks` key of `.claude/settings.json`, and the
  tool-owned files in `.ai/` and `.githooks/`, so the workspace runs the current checks.
  Your files, such as `STATE.md` and `README.md`, are never overwritten.

## What every workspace gets

- **`AGENTS.md`**: rules assembled from `tiers/*/_RULES.md`, between markers, plus a
  section that is yours. `CLAUDE.md` and `GEMINI.md` import it; Codex and Cursor read it directly.
- **Every rule says what enforces it.** Each rule carries an ID (`R-COMMIT`, `R-SOURCES`, …) and
  a tag: `enforced by: git`, `git, claude`, or `advisory`. A test in this repo fails if a rule
  claims a layer that does not exist at its tier, or if a rule has no tag.
- **Checks that bind every tool.** `.ai/policy.py` holds every machine-checked rule once. The git
  hooks in `.githooks/` (wired up with `core.hooksPath`) run it on every commit, whether it comes
  from Claude Code, Gemini, Codex, Cursor or a person. Refusals quote the rule ID and say how to fix it.
- **Claude Code hooks on top.** Every session starts with `STATE.md` and the workspace status
  already in context. The Stop hook will not let an agent finish with uncommitted work.
  `protect_paths`, `zone_guard` and `bash_guard` stop a bad write or shell command before it
  happens, using the same `policy.py`.
- **The right way is the easy way.** `python .ai/wr.py` helpers (and the Claude skills that wrap
  them) create correctly named notes, logged sources, complete decision rows, ADRs, runs and
  releases, so following the rules takes one command.
- **A `post-commit` hook that pushes every commit.** This is the lesson of the September 2026 disk
  loss: a commit that exists only locally is one disk failure from gone.

**After cloning a workspace**, run `git config core.hooksPath .githooks` once. The hooks are
versioned, but git does not turn on a hooks path by itself. `wr doctor` will check this.

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

The agreed plan is in [`docs/PLAN.md`](docs/PLAN.md). Releases, in order:

- **0.2.0, enforcement core** (done): `policy.py`, versioned git hooks, rule IDs, `GEMINI.md`.
- **0.3.0, Claude ergonomics** (done): SessionStart hook, a Bash write guard, permissions,
  a status line, `.ai/wr.py` helpers (`decide`, `source add`, `adr new` …) and skills that wrap them.
- **0.4.0, AgentBrain**: work agents in `~/.agentbrain/agents/work/`, synced per tier and pinned.
- **0.5.0, maintenance**: `wr doctor`, `wr adopt`.
- **0.6.0, integrations**: `--with github,jira,m365,rag`, `--ticket`, CI.
