# WorkRealm

> A workspace generator for work done with AI agents: tasks, analyses, features, evaluations,
> long projects. One command, a Git-backed folder, rules that actually bind.

![Version](https://img.shields.io/badge/version-0.11.0-6f42c1)
[![Python](https://img.shields.io/badge/Python-3.10%2B%20%C2%B7%20stdlib%20only-3776AB)](https://www.python.org/)
![Tests](https://img.shields.io/badge/tests-86%20end--to--end-2ea44f)
![Works with](https://img.shields.io/badge/works%20with-Claude%20Code%20%C2%B7%20Gemini%20%C2%B7%20Codex%20%C2%B7%20Cursor-lightgrey)

---

## The problem

AI agents are good at doing work and bad at keeping a workspace honest over weeks: they forget
the plan, edit the evidence, re-decide settled questions, name files at random and leave work
uncommitted. Rules written in a prompt are followed only some of the time, and less as the context
fills up.

WorkRealm makes the right behaviour the default:

- **One memory that survives sessions.** `STATE.md` is loaded into every session automatically.
- **Rules that bind every tool, not prose that hopes.** Git hooks run the same checks whether the
  commit comes from Claude Code, Gemini, Codex, Cursor or a person.
- **Evidence stays evidence.** Sources, raw data, run results and releases are write-once.
- **Decisions carry their reason.** Every decision names the alternative that lost and why; a
  settled decision is superseded, never silently edited.
- **The right way is one command.** Helpers and skills create correctly named, complete files, so
  following the rules is easier than not.
- **Specialists are shared.** Agents and skills come from one place
  ([AgentBrain](https://github.com/KxHartl/AgentBrain)), sized to the tier.

The failure modes it is built against, and the answer to each, are in
[`docs/DESIGN.md`](docs/DESIGN.md).

## Quick start

```powershell
python wr.py new MyTask              # task tier — the default, no flag
python wr.py new QuickFix --quick    # quick tier
python wr.py new BigThing --project  # project tier
python wr.py new Fix --with github,rag --ticket ABC-123   # integrations, the ticket it serves
python wr.py adopt C:\Projects\existing-repo --dry-run    # bring an existing folder under WorkRealm
```

Workspaces are created next to this folder (`C:\Projects\<name>`) unless `--dir` says otherwise.
**After cloning a workspace**, run `python .ai/wr.py init` once. The hooks are versioned, but Git
does not turn on a hooks path by itself; the session status says when they are off.

---

## Status

| | |
| --- | --- |
| Version | **0.11.0**, see [`CHANGELOG.md`](CHANGELOG.md) |
| Tests | 86 end-to-end tests: scaffold every tier, exercise every check, hook, helper and sync |
| In use | Four active workspaces, including a master's thesis repository brought in with `wr adopt` |
| Runtime | Python 3.10 or newer, standard library only |
| Next | See [Roadmap](#roadmap) |

---

## The three tiers

| | **quick** | **task** (default) | **project** |
|---|---|---|---|
| For | Hours to a day: a fix, a script, a one-off | Days to weeks: a feature, an evaluation, a report | Weeks to months: multi-phase, regulated or high-stakes work |
| Rules (`AGENTS.md`) | language, names, STATE first, commits, secrets, verify-don't-recall, scope | + where things go, sources, decisions, branches, specialists, lessons | + project layout, write-once evidence, inbox, ADRs, backups |
| Git checks, any tool | secrets, Conventional Commits, AI marking, names safe on every system, English and ASCII names (warn) | + write-once paths, sources logged, naming, decision register, why-body | + one home per document, ADR sections |
| Claude Code hooks | `session_start`, `checkpoint_gate`, `bash_guard` | + `protect_paths` | + `zone_guard`, inbox gate |
| Helpers and skills | `status`, `checkpoint`, `handoff` | + `note`, `source add`, `decide`, `open-item` | + `source promote`, `plan new`, `adr new`, `exp new`, `run new`, `release cut` |
| AgentBrain agents | — | `researcher`, `reviewer` | + `decision_keeper`, `lab_runner`, `releaser` |
| AgentBrain skills | — | `diagnose`, `tdd` | + `improve-codebase-architecture`, `grill-with-docs` |
| Private GitHub repo by default | no | yes | yes |

Every tier also gets the status line, the permission entries (secrets unreadable, force-push
denied, guard-rail edits ask first) and auto-push on every commit.

## How rules bind

Each rule in `AGENTS.md` has an ID and says what enforces it:

| Tag | Meaning |
|---|---|
| `enforced by: git` | `.githooks/` runs `.ai/policy.py` on every commit and refuses a violation, from any tool |
| `enforced by: claude` | a Claude Code hook acts as it happens: blocks the write or command, or loads context |
| `advisory` | only the text holds it |

A test in this repo fails if a rule claims a layer that does not exist at its tier, or if a rule
has no tag. Refusals quote the rule ID and say how to fix the problem.

**AI marking.** A commit is marked as AI work only when a subagent did that work on its own. The
subject gets the robot tag and the message gets an `AI-Agent: <name>` trailer. The Claude Code hook
adds both automatically, from the `agent_id` that Claude Code passes to hooks run inside a
subagent. Work the main agent does at your prompt is committed unmarked, and the main agent cannot
add the mark. The git check refuses a commit that has only one of the two.

**Sources at the project tier** go into `references/inbox/`. Promoting one into evidence
(`python .ai/wr.py source promote <file>`) is your decision, and Claude Code asks before running it.

## Layout of a workspace

Familiar names, one home for each kind of thing. Each tier adds folders and never renames one,
so `wr upgrade` is a pure addition.

```
README.md  STATE.md  AGENTS.md (+ CLAUDE.md, GEMINI.md)   workspace-wide, every tier
docs/
  notes/          findings, comparisons, drafts: YYYY-MM-DD-topic.md         task
  decisions/      DECISIONS.md, OPEN-ITEMS.md                                task
                  CONSTRAINTS.md, adr/NNNN-title.md                          project
  plans/          plans, phases, exit criteria                               project
references/       evidence: write-once, logged in SOURCES_LOG.md             task
  inbox/          downloads awaiting the owner's review                      project
src/  tests/      code and its tests                                         task
reports/          deliverables being written                                 task
data/raw/         input data as received, write-once                         project
data/processed/   derived from raw/, reproducible                            project
experiments/YYYY-MM-DD-topic/                                                project
  README.md       question, method, conclusion
  results/YYYY-MM-DD[-NN]/   one folder per run, write-once
releases/vX.Y.Z/  immutable hand-overs with MANIFEST.md and SUMMARY.md       project
archive/          superseded originals                                       project
```

The layout is data in `.workrealm.json` (`layout`, `protected`, `zones`, `naming`), and the checks
read it from there. The rules are written per role, so an adopted folder with its own names gets
rules and checks that name its real folders.

## Commands

```
wr new NAME [--quick | --project] [--dir PARENT] [--lang match|en|hr] [--remote | --no-remote]
           [--with github,rag] [--ticket KEY] [--template]
wr integrate github,rag [--path WORKSPACE]
wr upgrade --to task|project [--path WORKSPACE]
wr sync [--check] [--path WORKSPACE]
wr doctor [--fix] [--ci] [--path WORKSPACE]
wr adopt PATH [--tier quick|task|project] [--dry-run]
```

| Command | Does |
| --- | --- |
| `new` | Creates a workspace of the chosen tier, with rules, hooks, helpers, agents and skills |
| `upgrade` | Moves a workspace to a higher tier; adds files, never overwrites yours |
| `sync` | Re-syncs agents and skills from AgentBrain for the workspace's tier |
| `doctor` | Checks that the guard-rails still work; `--fix` repairs what is safe to repair |
| `adopt` | Brings an existing folder under WorkRealm and moves nothing |
| `integrate` | Adds MCP servers (GitHub, RAG) to `.mcp.json` |

Every option, the language and naming rules, tickets, CI and template repositories:
**[`docs/COMMANDS.md`](docs/COMMANDS.md)**.

---

## Layout of this repo

```
wr.py            the generator (stdlib only, Python >= 3.10)
wr.ps1, wr       launchers
tiers/quick/     base files + _RULES.md
tiers/task/      overlay on quick
tiers/project/   overlay on task
tests/           end-to-end: scaffold every tier, exercise every check, hook, helper and sync
docs/DESIGN.md   the design and the roadmap
docs/COMMANDS.md full command reference
```

Run the tests: `python -m unittest discover tests`

## Roadmap

See [`docs/DESIGN.md`](docs/DESIGN.md). Next up:

- an on-demand `.ai/REFERENCE.md`, so the always-loaded `AGENTS.md` stays short;
- a devcontainer, for setup in a browser (Codespaces) on top of the template path.

## Related projects

WorkRealm is the third generation of the same idea:

| Project | What it is |
| --- | --- |
| [AgentRealm](https://github.com/KxHartl/AgentRealm) | First generation (Apr–Jun 2026): project template with a clean root and an `.ai/` engine room |
| [LiteRealm](https://github.com/KxHartl/LiteRealm) | Second generation (May–Sep 2026): template for academic LaTeX work, seminars and theses |
| [AgentBrain](https://github.com/KxHartl/AgentBrain) | The shared brain: agents, skills, templates and RAG scripts, synced into every workspace |

## License

[Apache-2.0](LICENSE). It covers the author's own work in this repository. Third-party parts keep their own licences.
