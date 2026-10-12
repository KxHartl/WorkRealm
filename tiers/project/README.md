# {{NAME}}

_What this is, in one sentence._

| Path | Holds |
|---|---|
| `STATE.md` | Where things stand: goal, focus, next step — read first |
| `AGENTS.md` | Rules for AI agents (`CLAUDE.md` and `GEMINI.md` import it; Codex and Cursor read it directly) |
| `docs/notes/` · `docs/plans/` | Unsettled findings and drafts · plans, phases, exit criteria |
| `docs/decisions/` | `DECISIONS.md`, `OPEN-ITEMS.md`, `CONSTRAINTS.md`, `adr/` |
| `references/` | Evidence (write-once, logged); `inbox/` holds downloads awaiting review |
| `data/` | `raw/` input as received (write-once) · `processed/` derived from it |
| `src/` · `tests/` | Code and its tests |
| `experiments/` | One folder per experiment; `results/` per run, write-once |
| `reports/` | Deliverables being written |
| `releases/` | Immutable versions handed to someone |
| `archive/` | Superseded originals |
| `.ai/` | `wr.py` helpers, `policy.py` (every machine-checked rule), Claude hooks, `checkpoint.py` |
| `.githooks/` | Git hooks: run `policy.py` on every commit, from any tool, and push |

Run `python .ai/wr.py --help` for the helpers. Scaffolded with WorkRealm {{WR_VERSION}} at the **{{TIER}}** tier.
