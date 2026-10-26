# Changelog

## 0.11.0 — 2026-10-26

Adopting a real repository: its names, its branches and the machines it runs on.

- **`names --style --rewrite-refs`.** `--style` applies the R-NAMES default (lowercase ASCII
  kebab-case) to documents, figures and the folders that hold only those; code, and folders with
  code, keep their language's style. `--rewrite-refs` updates every `[[wikilink]]` (aliases and
  headings kept), Markdown link, canvas path and quoted path, keeps CRLF files CRLF, and refuses the
  whole rename when a link would break (a write-once file that still names it); `--force`
  overrides. `PATH ...` and `--keep GLOB` scope a run, so a large tree goes in batches.
- **A failed automatic push is no longer silent.** The post-commit hook keeps the error in
  `.git/workrealm-push.log`; the status and the session start print it, `wr doctor` warns and
  `--fix` pushes and clears it.
- **R-BRANCH: one short-lived branch per piece of work; parallel work in a worktree under
  `.claude/worktrees/` only** (now ignored). Merging is not finishing: the open steps stay in the
  plan. `wr doctor` lists merged branches (deleting stays the owner's call) and worktrees outside
  that folder or gone from disk (`--fix` prunes those).
- **`wr doctor` knows its machine.** It detects platform (Windows, Linux, WSL, macOS), container and
  host, or takes `WORKREALM_ENV`, and checks the matching entry of the optional `environments` list
  in `.workrealm.json`: the tools it needs on `PATH` and the services it must reach.
- **GitHub Issues as tickets:** issue #42's key is `GH-42` (GitHub links it like `#42`), so
  `ticket start GH-42 "title"` and the `Refs:` trailer work unchanged.

## 0.10.0 — 2026-10-26

Names follow the standard of what they name, instead of one style for everything.

- **R-NAMES** replaces the blanket "names are kebab-case" sentences in R-LANG and R-PLACE, which
  were wrong for code: a kebab-case Python module cannot be imported, and `unittest` never finds a
  `test-x.py`. The first of these decides a name: what a tool requires, the language's or format's
  standard (a table covers Git, Python, JS/TS, Java/Kotlin/C#, Go, Rust, C/C++, R, shell,
  PowerShell, SQL, data columns, notebooks, LaTeX, documents, received and derived data), what the
  project configured, and only then lowercase ASCII kebab-case.
- **Names that break a checkout are refused** at every tier: reserved Windows names, characters
  Windows refuses, a trailing dot or space, paths that differ only in case, paths over 200
  characters.
- **Non-ASCII names and spaces warn** with the ASCII name to use (`č` → `c`, `đ` → `d`), and a
  branch outside `<type>/<short-desc>` warns. The new `python .ai/wr.py names [--fix]` lists them and
  renames them with `git mv`, leaving committed write-once evidence alone and listing the files that
  still mention an old name.
- **Received files get a standard name when they arrive.** `source add` and `source promote` make it
  ASCII, lowercase kebab-case with a lowercase extension, and note the original name in
  `SOURCES_LOG.md`. A derived data file keeps the stem of its raw file. Helper slugs transliterate
  instead of dropping letters (`Čvorište` was `vori-te`, now `cvoriste`).
- **R-BRANCH** uses `<type>/<short-desc>` branches instead of `ai/<feature>`.
- **`.editorconfig`** ships with every tier, with each language's standard indentation; an existing
  one is never overwritten.
- The English check ignores text in `code` spans: a quoted name is not prose.
- `wr doctor --fix` brings an existing workspace's checks up to date.

## 0.9.0 — 2026-10-20

Safe adoption, repository hygiene, and workspaces from a GitHub template.

- **`adopt` overwrites nothing of another tool's.** When `.ai/`, `.githooks/`, `.claude/skills/`
  or the workflow already hold a file that is not WorkRealm's, adopt lists the conflict and stops
  before writing anything (`--dry-run` shows it too).
- **The repository's own git hooks keep running.** `core.hooksPath = .githooks` silences
  `.git/hooks`, so WorkRealm's `pre-commit`, `commit-msg` and `post-commit` now call the local hook
  of the same name, and adopt writes a forwarder in `.githooks/` for any other one (`pre-push`, ...).
- **`doctor` respects another tool's hooks path.** A `core.hooksPath` set by another tool is
  reported, never taken over by `--fix`, and accepted once its hooks call `.githooks/`.
- **Hygiene.** `doctor` (and `adopt`) report tracked virtualenvs, build output and files over
  10 MB, with the command that untracks them; nothing is removed automatically. Adopting a folder
  without Git ignores its virtualenvs and build output before the baseline commit.
- **GitHub template path.** `wr new NAME --template` creates the workspace as a GitHub template
  repository. "Use this template" (or `gh repo create --template`) and then
  `python .ai/wr.py init` in the clone give a new workspace its own name and date and turn the
  hooks on, with no WorkRealm installed. GitHub's "Initial commit" passes the message check.
- **`python .ai/wr.py init`** is also what every fresh clone runs to turn the hooks on; the status
  (and so every session start) says when they are off.

## 0.8.1 — 2026-10-16

- **R-LANG simplified:** final outputs (`reports/`, `releases/`) are always Croatian and everything
  else is English. There is no per-workspace document language any more; `--lang` sets only the
  chat rule again, as before 0.8.0.

## 0.8.0 — 2026-10-16

Language by role. Deliverables are written in the workspace's language; everything else stays English.

- **R-LANG** now separates what the work hands over (`reports/`, `releases/`) from everything else.
  Deliverables are written in the workspace's language; code, comments, commits, notes,
  decisions, plans and `STATE.md` stay English, and file names are ASCII.
- **`--lang`** sets both the chat and the deliverable language. The default (`match`) keeps the chat
  in the user's language and writes deliverables in Croatian; `hr` makes both Croatian; `en`
  makes both English.
- The pre-commit check no longer warns about Croatian text in the deliverables, unless the workspace
  chose English. A workspace picks up the new rule with `wr doctor --fix` or `wr upgrade`.

## 0.7.0 — 2026-10-16

Integrations: the tools a workspace talks to, the ticket it serves, and CI that runs its checks.
Needs AgentBrain 2.6.0 for `--with rag`.

- **`wr new --with github,rag`** and **`wr integrate github,rag`** write `.mcp.json` entries
  (other servers and keys are kept) and add what they need to `.env.example`:
  - `github`: GitHub's remote MCP server, limited to the repos, issues, pull requests and actions
    toolsets; the token is `${GITHUB_PAT}`, read from the environment Claude Code starts in;
  - `rag`: AgentBrain's RAG server over stdio, started by `.ai/rag_server.py` from the workspace
    root, so ingest stays inside the workspace and chunks are tagged with its name.

  `wr doctor` checks the entries (`--fix` restores them) and, locally, that the variables are set
  and the RAG server exists.
- **Tickets (R-TICKET).** `wr new --ticket ABC-123` records the workspace's ticket in
  `.workrealm.json` and `STATE.md`; `python .ai/wr.py ticket start ABC-123 "title"` creates
  `feat/ABC-123-title`. `checkpoint.py` adds a `Refs: ABC-123` trailer, the commit check warns
  (never blocks) when it is missing, and the status and status line show the ticket.
- **CI.** Task and project workspaces get `.github/workflows/workrealm.yml`, a tool file that
  runs `python .ai/policy.py ci` on every push and pull request. It re-checks each pushed commit's
  message and write-once paths, so a commit that skipped the hooks (`--no-verify`, a web editor,
  another machine) still fails, then checks the whole tree for secrets. A new branch is checked
  only for the commits no other branch has.
- **Secrets in config files.** A literal credential in `.mcp.json` or `.claude/settings.json`
  (`Bearer …`, a GitHub token, a `"token": "…"` value) is now refused at commit, not only reported
  by `wr doctor`.

## 0.6.0 — 2026-10-12

Maintenance: keep a workspace's guard-rails working, and bring any existing folder in.

- **`wr doctor [--fix] [--ci]`** reports one line per check:
  - version, tool files, settings and the AGENTS.md rules block and shims;
  - `core.hooksPath`, remote and unpushed commits, work tree, AgentBrain pin;
  - tracked secrets (including literal tokens in `.mcp.json` or settings);
  - a whole-tree policy pass (`policy.tree_findings`) that lists existing violations without
    blocking them.

  `--fix` repairs what is safe and never touches secrets. `--ci` skips local state. Exit 1 on any failure.
- **`wr adopt PATH [--tier] [--dry-run]`** moves nothing:
  - it maps existing folders onto roles; only folders with tracked files count, so ignored build
    output is never a role;
  - it infers naming: it keeps a rule where at least 80% of existing entries already follow it,
    adapts ADR numbering to the existing style, and relaxes the rest;
  - it adds the rules block to an existing `AGENTS.md` (your text kept verbatim), makes `CLAUDE.md`
    and `GEMINI.md` import it, and appends secret patterns to `.gitignore`;
  - it reports misfits: misplaced decision documents, folders that fit no role, and an existing
    `core.hooksPath` such as husky, which it never overrides;
  - a folder without Git first gets a baseline commit (refused if it would include secrets);
  - a dirty repository is refused, so the adoption is one reviewable change.
- **Rules by role.** `PROTECTED`, `ZONES`, `SNAPSHOTS` and `NAMING` are written as `{sources}`,
  `{experiments}/*/results` and so on, and are expanded from each workspace's layout. Templates and
  rule texts are rewritten to the real folder names. `wr upgrade` keeps an adopted layout and its
  naming choices.
- **ADRs:**
  - `adr new` follows the folder's existing numbering (`ADR-003-...`);
  - an ADR that predates the rule may still be edited (it may not lose sections);
  - registers that share a folder with ADRs are not treated as ADRs.

## 0.5.0 — 2026-10-12

A universal design: a familiar layout, held as data, and the owner's decisions kept with the
owner. Workspaces from 0.4.0 keep their old folders: `wr upgrade` adds and never moves, and
`wr adopt` (0.6.0) will map an existing layout. Needs AgentBrain 2.5.0.

- **New layout:**
  - `docs/notes/`, `docs/decisions/` (+ `CONSTRAINTS.md`, `adr/NNNN-title.md`), `docs/plans/`;
  - `references/` (+ `inbox/`), `src/`, `tests/`, `reports/`, `data/raw|processed/`;
  - `experiments/<date-topic>/results/<run>/`, `releases/`, `archive/`.

  Every folder has a README with its one rule. It replaces the numbered zones.
- **Layout as data.** `.workrealm.json` gains `layout`, `zones` and `snapshots`. Write-once
  `protected` entries take globs (`experiments/*/results`) and `!` exceptions. `policy.py` and the
  helpers read all their paths from it.
- **Project-tier inbox (R-INBOX):**
  - agents stage sources in `references/inbox/`;
  - `python .ai/wr.py source promote` moves a file into evidence and logs it, and Claude Code asks
    the user first;
  - direct writes into `references/` are refused at this tier.
- **AI marking for subagent work only.** The bash hook detects a subagent from `agent_id` and
  rewrites its `checkpoint.py` call to add `--agent <name>`. The commit gets the robot tag and an
  `AI-Agent:` trailer.
  - The main agent cannot add the mark.
  - A subagent's raw `git commit` is refused.
  - The commit-msg check refuses a tag without its trailer, or a trailer without its tag.
- **Helpers:** `plan new`; `run new <experiment>` (runs live inside their experiment); `release cut`
  also writes `SUMMARY.md`. `prompt new|done` and the prompts zone are gone (prompts are notes or plans).
- **Skills:** `/plan` added. All skills, rules and agents use the new paths.
- **Write-once fixes:** a folder's `README.md` and the sources log are append-to documents, so
  they no longer count as write-once evidence. `CONSTRAINTS.md` gains a "what flips if this is
  wrong" column.

## 0.4.0 — 2026-10-12

AgentBrain integration: specialists and shared skills sized to the tier. Needs AgentBrain 2.4.0.

- `wr new` and `wr upgrade` sync AgentBrain's work agents (`agents/work/`, filtered by their
  `tiers:`) into `.claude/agents/`, and opted-in brain skills into `.claude/skills/`:
  - task: `researcher`, `reviewer`; skills `diagnose`, `tdd`.
  - project: adds `decision_keeper`, `lab_runner`, `releaser`; skills
    `improve-codebase-architecture`, `grill-with-docs`.
  - quick: none, because agents cost context.
- `wr sync [--check]` re-syncs, prunes generated files whose source is gone, and reports drift
  (exit 1) together with how far the brain has moved since the pinned commit.
- `.workrealm.json` records `agentbrain_version` and `agentbrain_commit`. The brain's
  `min_workrealm_version` is honoured.
- A missing brain is a warning: the workspace is created and works, and `wr sync` fills it in later.
- Edits to generated agents ask the user first (they would be overwritten by the next sync).
- Rules: specialists are changed in AgentBrain, never in place. New R-LEARN (advisory): general
  lessons go back to `~/.agentbrain`.

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
