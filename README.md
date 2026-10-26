# WorkRealm

> A workspace generator for work done with AI agents: tasks, analyses, features, evaluations,
> long projects. One command, a Git-backed folder, rules that actually bind.

Repository: <https://github.com/KxHartl/WorkRealm> (private)

```powershell
python wr.py new MyTask              # task tier — the default, no flag
python wr.py new QuickFix --quick    # quick tier
python wr.py new BigThing --project  # project tier
python wr.py new Fix --with github,rag --ticket ABC-123   # integrations, the ticket it serves
```

Workspaces are created next to this folder (`C:\Projects\<name>`) unless `--dir` says otherwise.

## What it is for

AI agents are good at doing work and bad at keeping a workspace honest over weeks: they forget
the plan, edit the evidence, re-decide settled questions, name files at random and leave work
uncommitted. WorkRealm makes the right behaviour the default:

- **One memory that survives sessions.** `STATE.md` is loaded into every session automatically.
- **Rules that bind every tool, not prose that hopes.** Git hooks run the same checks whether the
  commit comes from Claude Code, Gemini, Codex, Cursor or a person.
- **Evidence stays evidence.** Sources, raw data, run results and releases are write-once.
- **Decisions carry their reason.** Every decision names the alternative that lost and why; a
  settled decision is superseded, never silently edited.
- **The right way is one command.** Helpers and skills create correctly named, complete files, so
  following the rules is easier than not.
- **Specialists are shared.** Agents and skills come from one place (AgentBrain), sized to the tier.

## Layout

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

- Language (R-LANG): final outputs (`reports/`, `releases/`: a report, a seminar paper, a
  presentation) are Croatian; everything else (code, comments, commits, notes, decisions, plans,
  `STATE.md`) is English. `--lang` only sets the chat rule; `match` (the default) replies in the
  language the user writes in.
- Names (R-NAMES): a tool's required name first, then the standard of the language or format
  (PEP 8 for Python, `PascalCase` files for Java and C#, Conventional Branch for branches ...),
  then the project's own configuration, else lowercase ASCII kebab-case. Every name is ASCII
  (`č` → `c`, `đ` → `d`); received files are renamed to the standard when they arrive, with the
  original name logged. Names that break a checkout on Windows or macOS are refused; non-ASCII
  names, spaces and off-convention branches warn, and `python .ai/wr.py names --fix` renames them.
  Adopting a repository with its own style (snake_case notes, an Obsidian vault):
  `python .ai/wr.py names notes --style --rewrite-refs` lists what the default style renames and
  how many files' links change; add `--fix` to do it. Code and folders with code keep their
  style, `--keep GLOB` keeps a name a tool's config uses, and a rename that would break a
  `[[wikilink]]` is refused as a whole.
- `upgrade` adds the missing files, rewrites the generated block of `AGENTS.md` (your
  *Project-specific rules* section is kept), the `hooks` key of `.claude/settings.json` and the
  tool-owned files in `.ai/`, `.githooks/` and `.claude/skills/`. Your own files are never overwritten.
- `sync` re-syncs the work agents and skills from AgentBrain (`~/.agentbrain`, or
  `AGENTBRAIN_PATH`) for the workspace's tier, prunes the ones whose source is gone, and records
  the brain version and commit. `--check` reports drift and writes nothing. `new` and `upgrade`
  sync automatically; without a brain they warn and carry on.

- `doctor` checks that the guard-rails still work:
  - version, tool files, settings and rules block;
  - `core.hooksPath` (after a fresh clone, commits are not checked until it is set);
  - remote and unpushed commits; a failed background push is kept in `.git/workrealm-push.log`
    and shown here, in the status and at session start until a push lands;
  - branches already merged and worktrees outside `.claude/worktrees/` or gone from disk (R-BRANCH);
  - the environment: platform, container and host (or `WORKREALM_ENV`) matched against the
    optional `environments` in `.workrealm.json`, each with the `tools` it needs, the `services`
    it must reach and its `setup` command, e.g.
    `{"name": "lab-pc", "host": "lab-*", "tools": ["git", "git-lfs"], "services": [{"name": "qdrant", "url": "http://qdrant.lan:6333"}]}`;
  - work tree, the AgentBrain pin, tracked secrets (including literal tokens in `.mcp.json`);
  - hygiene: tracked virtualenvs, build output (`node_modules/`, `__pycache__/`, `build/`, ...)
    and files over 10 MB, with the command that untracks them;
  - a whole-tree policy pass that lists existing violations without blocking them.

  `--fix` repairs what is safe to repair: hooks path, tool files, settings, rules block, sync, and
  pushing a branch that has no upstream or whose last push failed, pruning vanished worktrees. It never touches secrets (they need rotating), never
  untracks files, and never takes over a `core.hooksPath` another tool set: that is reported
  until its hooks call `.githooks/pre-commit` and `.githooks/commit-msg`. `--ci` skips the checks
  of local state and exits 1 on a failure.
- `adopt` brings an existing folder under WorkRealm and **moves nothing**:
  - it maps the folder's own names onto the roles (`literature/` as sources, `dist/` as releases,
    ADRs kept in `decisions/`, and so on); a folder counts only if it holds tracked files, so
    ignored build output is never a role;
  - it keeps each naming rule only where the folder already follows it, adapts ADR numbering to
    the existing style, and relaxes the rest;
  - it adds the rules block to an existing `AGENTS.md` without touching your text;
  - it makes `CLAUDE.md` and `GEMINI.md` import it;
  - it reports what doesn't fit, including tracked virtualenvs, build output and large files;
  - it **overwrites nothing of another tool's**: if `.ai/`, `.githooks/`, `.claude/skills/` or the
    workflow already hold a file that is not WorkRealm's, it lists the conflict and stops before
    writing anything;
  - the repository's own hooks in `.git/hooks` keep running: WorkRealm's hooks call the one of the
    same name, and any other gets a forwarder in `.githooks/`.

  `--role ROLE=PATH` (repeatable) overrides a wrong guess, e.g. `--role inbox=data/staging`.
  `--dry-run` shows all of this and writes nothing. A folder without Git first gets a baseline
  commit of what is already there; its virtualenvs and build output are ignored before that.

- `--with` / `integrate` add MCP servers to `.mcp.json` (your own servers are kept):

  | Name | Server | Needs |
  |---|---|---|
  | `github` | GitHub's remote server: repos, issues, pull requests, actions | `GITHUB_PAT` in the environment |
  | `rag` | AgentBrain's RAG server (search and ingest the shared corpus), started by `.ai/rag_server.py` | AgentBrain 2.6.0 |

  Claude Code reads `${VAR}` from the environment it starts in, not from `.env`, and asks once
  whether to trust the servers. `doctor` checks the entries and, locally, the variables.
- `--ticket KEY` records the ticket the workspace serves. Inside any workspace,
  `python .ai/wr.py ticket start KEY "title"` creates `feat/KEY-title`; `checkpoint.py` adds
  `Refs: KEY` to every commit on it, and the commit check warns when it is missing. With GitHub
  Issues, issue #42's key is `GH-42`, which GitHub links like `#42`.
- Task and project workspaces get `.github/workflows/workrealm.yml`: on every push and pull
  request it runs `python .ai/policy.py ci`, which re-checks the pushed commits (a commit made
  with `--no-verify` fails there) and the whole tree for secrets. It needs no secrets.

- `--template` makes the new workspace a GitHub template repository. A new workspace then needs
  no WorkRealm on the machine: "Use this template" on GitHub (or
  `gh repo create NAME --template OWNER/REPO --private --clone`), then, in the clone,
  `python .ai/wr.py init`. It names the workspace after its folder (or `--name`), dates it, turns
  the git hooks on and commits. One template per tier is enough; keep it current with
  `wr doctor --fix` in the template repo.

**After cloning a workspace**, run `python .ai/wr.py init` once. The hooks are versioned, but Git
does not turn on a hooks path by itself; the session status says when they are off.

## Layout of this repo

```
wr.py            the generator (stdlib only, Python >= 3.10)
wr.ps1, wr       launchers
tiers/quick/     base files + _RULES.md
tiers/task/      overlay on quick
tiers/project/   overlay on task
tests/           end-to-end: scaffold every tier, exercise every check, hook, helper and sync
docs/DESIGN.md   the design and the roadmap
```

Run the tests: `python -m unittest discover tests`

## Roadmap

See [`docs/DESIGN.md`](docs/DESIGN.md). Next up:

- an on-demand `.ai/REFERENCE.md`, so the always-loaded `AGENTS.md` stays short;
- a devcontainer, for setup in a browser (Codespaces) on top of the template path.
