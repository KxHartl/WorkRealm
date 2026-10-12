# Changelog

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
