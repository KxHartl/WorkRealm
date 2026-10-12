# {{NAME}}

_What this is, in one sentence._

| Path | Holds |
|---|---|
| `STATE.md` | Phase, focus, blockers — read first |
| `AGENTS.md` | Rules for AI agents (`CLAUDE.md` and `GEMINI.md` import it; Codex and Cursor read it directly) |
| `10-research/` | Notes, experiments, downloaded sources (read-only) |
| `20-prompts/` | Prompts being shaped and already run |
| `30-decisions/` | `DECISIONS.md`, ADRs, `CONSTRAINTS.md`, `OPEN-ITEMS.md` |
| `40-lab/` | Test protocols and write-once run results |
| `50-release/` | Immutable versioned snapshots |
| `90-archive/` | Superseded originals |
| `src/` | Code |
| `.ai/` | `policy.py` (every machine-checked rule), Claude hooks, the `checkpoint.py` commit helper |
| `.githooks/` | Git hooks: run `policy.py` on every commit, from any tool, and push |

Scaffolded with WorkRealm {{WR_VERSION}} at the **{{TIER}}** tier.
