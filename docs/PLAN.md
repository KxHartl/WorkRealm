# WorkRealm: what goes in each tier, how rules are enforced, and how AgentBrain plugs in

## Context

WorkRealm v0.1.0 creates a workspace with rules written as prose, three Claude Code hooks, and a
post-commit auto-push. The owner wants it to feel seamless and intuitive, to actually force agents
to follow rules (naming, language, decisions, commits), and to integrate with AgentBrain and work
tools.

Research covered `~/.agentbrain`, KEV-Ai-Architecture, a LiteRealm-bootstrapped project and
WorkRealm itself. The findings that shape this plan:

- **Prose rules don't bind.** KEV and AgentBrain both record agents skipping rules that were only
  written down (see `gotchas/rules-need-enforcement-layers.md`). What works is the strongest layer
  a rule can reach: Git hooks, then harness hooks, then one-shot helpers, then prose.
- **Workspaces must work across tools.** The owner chose Claude Code, Gemini CLI / Antigravity,
  Codex / Cursor and Claude Desktop. Claude hooks bind only Claude Code, so **the Git layer has to
  carry the real enforcement**. Today WorkRealm has no Git-level checks except auto-push.
- **The September disk loss** showed that unversioned hooks (post-commit in `.git/hooks`) disappear
  on clone, and that a rule claiming a backup exists, without a mechanism, is fiction.
- **AgentBrain's only integration point** is `scripts/sync_agents.py --namespace`. It does not sync
  skills, never prunes removed agents, and cannot filter by tier. Its skills are plain markdown,
  not Claude Code `SKILL.md`.
- **Inconsistencies in v0.1.0:**
  1. The rules say `zone_guard` "warns on crossings", but it doesn't.
  2. The task tier says decisions are never edited; the project tier says edit in place. Both end
     up in the same project `AGENTS.md`.
  3. `zone_guard` ignores `notebook_path`.

Decisions taken: tooling is **copied and synced, pinned** (no plugin dependency). The integrations
in scope are **GitHub, M365, Jira / Confluence / Azure DevOps, and local RAG**.

---

## Design principles

1. **Every rule has an ID and a declared enforcement layer.** `_RULES.md` tags each rule, for
   example `[R-COMMIT-1 · git+claude]` or `[R-LANG-1 · advisory]`. A test checks that every
   non-advisory ID has a check that implements it. This is how "rules need enforcement layers"
   becomes something that is itself enforced.
2. **One policy core, several callers.** `.ai/policy.py` (stdlib) holds every check. All of these
   call the same functions, so rule logic lives in one file:
   - the Claude hooks,
   - the Git hooks,
   - `wr doctor`,
   - CI.
3. **Configuration as data.** `.workrealm.json` grows `zones`, `protected`, `naming` (regexes per
   zone) and `checks` (enabled per tier). Higher tiers add entries and never rename them, which
   keeps tiers strict extensions.
4. **Ergonomics beat prohibition.** Every blocked action gets a one-command way to do it right,
   named in the block message. For example, the decision-placement block says "use
   `.ai/wr.py decide`".
5. **Guards must not cry wolf.** They are silent on the happy path, block only on certain
   violations, and treat anything uncertain as a warning. KEV's always-firing Stop hook stopped
   being read.

---

## What goes at which tier

| | **quick** | **task** (adds) | **project** (adds) |
|---|---|---|---|
| **Rules** | language, STATE first, commit discipline, secrets, verify-not-recall, scope | where things go, sources are evidence, decisions carry reasons, branches, long work, naming | zones, write-once evidence, ADRs, constraints, owner decisions, release, backups |
| **Git hooks** (`.githooks/`, versioned, `core.hooksPath`) | pre-commit: secrets; commit-msg: Conventional Commits; post-commit: push | pre-commit: protected paths, naming, English-only check (warn) | pre-commit: zone placement, no cross-zone duplicates, decision-register format; commit-msg: a body is required when `30-decisions/` changes |
| **Claude hooks** | Stop: checkpoint gate; **SessionStart**: inject STATE.md summary, tier and git status | PreToolUse: protect_paths, plus a **Bash matcher** for shell writes to protected paths; **PreCompact**: remind to update STATE | PreToolUse: zone_guard |
| **Claude permissions** (`settings.json`) | deny `Read(.env*)`, deny `git push --force` | deny edits under the protected paths | — |
| **Helpers** (`.ai/wr.py`, ergonomics for every harness) | `checkpoint`, `state` | `source add URL`, `decide`, `open-item` | `adr new`, `exp new`, `run new`, `release cut`, `handoff` |
| **Skills** (`.claude/skills/*/SKILL.md`, thin wrappers over the helpers) | `/checkpoint`, `/handoff` | `/decide`, `/source`, `/open-item` | `/adr`, `/experiment`, `/release` |
| **Agents** (synced from AgentBrain `agents/work/`) | none (they cost context) | `researcher` (fetch + log sources), `reviewer` (read-only) | `decision_keeper`, `lab_runner` (numbers, not verdicts), `releaser` |
| **Shims** | `CLAUDE.md`, `GEMINI.md` → `AGENTS.md`; Codex / Cursor read `AGENTS.md` natively | — | — |
| **Status line** | tier · dirty file count · unpushed commits | + open blockers count | + current phase |
| **CI** (`.github/workflows/workrealm.yml`) | — | runs `wr doctor --ci` on push (binds every harness and every human) | + checks that `50-release/` is immutable |

**What can't be forced, and how it is handled:**
- **Chat language** can't be checked. It is written once in `AGENTS.md` and injected by SessionStart.
- **"Documents in English"** gets a warn-only pre-commit heuristic: Croatian diacritics in `.md` or
  code outside `10-research/sources/` print a warning.

---

## AgentBrain integration

These changes are in the **separate `~/.agentbrain` repo**, committed there.

1. **`sync_agents.py`:**
   - add `--tier T` (filters on an `tiers: [task, project]` frontmatter field),
   - accept multiple namespaces (`--namespace work,shared`),
   - `--prune` deletes outputs whose source is gone (identified by the AUTO-GENERATED header),
   - add per-agent `tools:` in frontmatter (replacing the hardcoded `TOOLS` dict),
   - `lint-agents.py` also checks subfolders.
2. **New `sync_skills.py`:** turns brain skills into `.claude/skills/<name>/SKILL.md` (adds
   `name` / `description`) for skills tagged `tiers:`.
3. **`agents/work/`:** `researcher`, `reviewer`, `decision_keeper`, `lab_runner`, `releaser`.
   They are generalized from KEV's `source_fetcher`, `adr_consolidator` and `conformance_runner`.
   KEV keeps its own namespace.
4. **`manifest.yaml`:** add `min_workrealm_version` and `work_agents`.
   - `wr new` / `wr sync` stamp `agentbrain_version` and `agentbrain_commit` into `.workrealm.json`.
   - If the brain is missing, `wr` still works: it skips the sync with a warning, and `doctor`
     reports it.
5. **Gotchas flow back** under the rule KEV already uses: general lessons go to
   `~/.agentbrain/gotchas/`, workspace-specific ones go to an ADR or `REFERENCE.md`.

---

## Integrations (opt-in flags, never secrets in Git)

- **`wr new --with github,jira,m365,rag`** writes a `.mcp.json` from templates.
  - Credentials only come from environment variables named in `.env.example`.
  - Exact MCP server packages are verified against current docs at implementation time, not
    recalled.
- **GitHub:** private repo (exists), the CI workflow, a PR template, and a `gh` helper skill
  (`/pr`).
- **Jira / Azure DevOps:**
  - `wr new --ticket PROJ-123` records the ticket in `.workrealm.json` and STATE.md, and names
    branches `ai/PROJ-123-<slug>`.
  - A `commit-msg` check adds the ticket key (task tier and up when a ticket is set).
- **M365 / Confluence:** MCP config only. `/source` can save an exported document into
  `10-research/sources/` with a log line.
- **RAG (project tier):** `/search-sources` calls `~/.agentbrain/scripts/rag/{ingest,query}.py`
  with a collection per workspace. This is an opt-in because it needs the homelab Qdrant.

---

## New `wr` commands

- **`wr sync`:** re-runs the agent and skill sync at the workspace's tier, re-renders the
  generated `AGENTS.md` block, and updates the pin.
- **`wr doctor [--ci] [--fix]`:** checks that
  - `core.hooksPath` is set,
  - the remote exists and nothing is unpushed,
  - nothing has drifted from the template version,
  - every rule ID is enforced,
  - the AgentBrain pin is not stale,
  - `.mcp.json` contains no secrets.

  `--fix` reinstalls the hooks. This replaces "copy `POST_COMMIT` by hand after cloning".
- **`wr adopt [--tier T]`:** brings an existing folder (KEV) under WorkRealm without moving files.
  It writes `.workrealm.json` with zones mapped from what exists, puts the rules block into the
  existing `AGENTS.md` between markers, installs the hooks, and reports what doesn't fit instead of
  moving it.

---

## Releases, in order (each one: tests in `tests/test_wr.py`, VERSION + CHANGELOG, commit)

1. **0.2.0 Enforcement core:**
   - `.ai/policy.py`; versioned `.githooks/` with `core.hooksPath` set by `wr new`;
   - pre-commit and commit-msg checks per tier;
   - rule IDs in `_RULES.md` and the test that every non-advisory ID has a check;
   - fix the three v0.1.0 inconsistencies (one decision policy: the register gets superseding
     rows; ADRs are edited in place with a decision log);
   - `GEMINI.md` shim.
2. **0.3.0 Claude ergonomics:** SessionStart and PreCompact hooks, the Bash matcher, permissions,
   status line, the `.ai/wr.py` helpers and the skills that wrap them.
3. **0.4.0 AgentBrain:** the `sync_agents` extensions, `sync_skills`, `agents/work/`, manifest
   fields (in AgentBrain), then `wr sync` and pinning (in WorkRealm).
4. **0.5.0 Maintenance:** `wr doctor` and `wr adopt`, with a dry-run of adopt on a copy of KEV.
5. **0.6.0 Integrations:** `--with` MCP templates, `--ticket`, the CI workflow, the RAG skill.

---

## Critical files

- `wr.py`
  - `write_settings` gains SessionStart / PreCompact / Bash / permissions entries.
  - New: `install_githooks` (replaces `install_post_commit`), `cmd_sync`, `cmd_doctor`,
    `cmd_adopt`.
  - Reuse: `tiers_upto`, `copy_tier`, `render`, `write_agents_md`, `write_meta`.
- `tiers/quick/.ai/`: new `policy.py`, `wr.py` (helpers) and `.githooks/{pre-commit,commit-msg,post-commit}`.
  - Existing hooks become thin wrappers over `policy.py`.
- `tiers/*/_RULES.md`: rule IDs and layer tags, and the fixed decision policy.
- `tiers/*/.claude/skills/`: per-tier skills.
- `~/.agentbrain/scripts/sync_agents.py`, `sync_skills.py` (new), `agents/work/*.md`, `manifest.yaml`.

---

## Verification

- `python -m unittest discover tests` must stay green. New end-to-end tests:
  - a commit containing `.env` is rejected by **git** (not only by Claude);
  - a bad commit message is rejected;
  - editing a protected file via plain `git commit` is rejected;
  - a misnamed file in a zone is rejected;
  - SessionStart prints STATE;
  - every rule ID is enforced;
  - `wr sync --check` detects drift;
  - `wr doctor` flags a missing `core.hooksPath`;
  - `wr adopt` on a fixture folder moves nothing.
- **Manual:** scaffold one workspace per tier and open it in Claude Code to confirm the
  SessionStart context, skills and status line appear. Make a commit from plain Git (simulating
  Gemini / Codex) to confirm the Git hooks bind without Claude.
- **AgentBrain:** `sync_agents.py --check` and the lint pass in that repo's own CI.

**Next step after approval:** implement **0.2.0 only**, then stop for review, as before.
