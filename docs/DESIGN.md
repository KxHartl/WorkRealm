# WorkRealm design

What WorkRealm is, the problems it is built against, how it solves each one, and what comes next.
This replaces the earlier plan (in Git history at `docs/PLAN.md`).

## The owner's goals

1. **Universal.** Fits any work done with AI agents, not one kind of project.
2. **Rules bind every tool.** Claude Code, Gemini CLI / Antigravity, Codex / Cursor, Claude
   Desktop, and people.
3. **Enforced:** naming, language, decisions, commits, evidence.
4. **Seamless and intuitive.** Familiar layout; the right way is the easy way.
5. **Shared specialists.** Agents and skills in AgentBrain, synced per tier.
6. **Integrations** with the tools the work runs through: GitHub, the shared document corpus
   (RAG), tickets and CI.

## Failure modes it is built against

| Failure | Answer |
|---|---|
| Prose rules are followed only some of the time, and less as context fills | Every rule has an ID and an enforcement tag; anything checkable is checked by `policy.py` |
| Agent harnesses differ; only one has hooks | The binding layer is Git (`.githooks/`, `core.hooksPath`); Claude hooks are a second layer |
| A guard that always fires stops being read | Checks are silent on the happy path; a test proves a fresh workspace passes with no output |
| Work exists only on one disk | `post-commit` pushes every commit; the Stop hook refuses to end with a dirty tree |
| Hooks in `.git/hooks` vanish on clone | Hooks are versioned in `.githooks/`; `wr doctor --fix` restores `core.hooksPath` |
| A background push fails and nobody notices | `wr doctor` reports commits that are not on the remote and pushes them with `--fix` |
| Existing work does not fit a template | `wr adopt` maps the folder's own names onto roles, keeps conventions it already follows, moves nothing |
| Evidence gets edited | Write-once paths, checked at commit time (any tool) and at write time (Claude) |
| Decisions drift silently | Register rows are superseded, never edited; ADRs carry a decision log; commits need a why |
| A rule is described but not enforced | The rule-contract test fails when a tag claims a layer that does not exist |
| Agents mislabel their own work | AI marking is set by the hook from `agent_id`, never by the agent |
| Session context is lost | SessionStart puts `STATE.md` and the status into context, and again after compaction |
| Hooks are skipped (`--no-verify`, a web editor, another machine) | The GitHub workflow re-runs the checks on every pushed commit |
| Credentials end up in shared config | `.mcp.json` references `${VAR}`; a literal token is refused at commit |

## Principles

1. **Layers, strongest first:** Git, then harness hooks, then one-command helpers, then prose.
2. **One policy core.** `.ai/policy.py` holds every check; the git hooks, Claude hooks,
   `checkpoint.py` and the GitHub workflow all call it.
3. **Configuration is data.** Layout, write-once paths, zones and naming live in
   `.workrealm.json`. Tiers add entries and never rename them.
4. **Tiers are strict extensions.** `quick` ⊂ `task` ⊂ `project`; `wr upgrade` only adds.
5. **The owner decides.** Agents propose. Promotion of evidence, decisions and marking are never
   the agent's call.
6. **Verify, don't recall.** Tool behaviour is checked against current documentation before it is
   relied on. Examples so far: Claude Code SessionStart and PreCompact output, hook `agent_id`,
   permission syntax, Gemini `@` imports.

## Layout rationale

- **Conventional names:** `docs/`, `src/`, `tests/`, `data/raw|processed`, `references/`,
  `reports/`, and ADRs as `NNNN-title.md`. A developer or researcher knows where things go without
  reading the manual.
- **Workspace-wide at the root:** `STATE.md`, `AGENTS.md`, `README.md`.
- **Repeated per unit:** each experiment has the same shape (`README.md` plus `results/<run>/`),
  and so does each release (`MANIFEST.md` plus `SUMMARY.md`). Every folder has a README that says
  what it holds and its one rule.
- **No numbered stages:** plain names read better than `30-…`, and plans live in `docs/plans/`
  rather than in folder order.

## Released

- **0.2.0:** policy core, versioned git hooks, rule IDs and the contract test, `GEMINI.md`.
- **0.3.0:** helpers and skills, SessionStart context, `bash_guard`, status line, permissions.
- **0.4.0:** AgentBrain work agents and skills, synced per tier and pinned (`wr sync`).
- **0.5.0:** the universal layout as data; the project-tier inbox with owner promotion;
  subagent-only AI marking; experiments with per-run results; plans.
- **0.6.0:** `wr doctor [--fix] [--ci]` and `wr adopt [--dry-run]`. Write-once paths, zones and
  naming are defined per role, and templates and rule texts follow the workspace's own layout.

- **0.7.0:** integrations as `.mcp.json` entries (`--with github,rag`, `wr integrate`), tickets
  (`--ticket`, `ticket start`, `Refs:` trailers, R-TICKET), and a GitHub workflow that re-runs the
  checks on every pushed commit.

## Integration choices (0.7.0)

- **GitHub:** GitHub's own remote server (`api.githubcopilot.com/mcp/`), toolsets limited to
  repos, issues, pull requests and actions. Claude Code expands `${GITHUB_PAT}` from its
  environment; it does not read `.env`.
- **RAG:** AgentBrain's server, run locally over stdio. The main corpus stays on the server; this
  machine embeds with the model that built it, because that is where the GPU is. The launcher in
  `.ai/` finds AgentBrain the same way `wr sync` does.
- **CI runs the policy core, not `wr doctor`.** A workspace does not carry the generator, and the
  checks that matter on a push are the commit checks a skipped hook did not run.
- **Left out on purpose:** Jira, Confluence, Azure DevOps and Microsoft 365. A ticket key is
  plain text that needs no tracker; Office files are handled locally, without a cloud server.
  Personal mail and calendars belong to account-level connectors, not to a workspace.

## Next

- **Later:**
  - an on-demand `.ai/REFERENCE.md`, so the always-loaded `AGENTS.md` stays short;
  - a devcontainer / GitHub-template path for setup without a local install.
