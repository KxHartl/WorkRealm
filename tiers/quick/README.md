# {{NAME}}

_What this is, in one sentence._

| Path | Holds |
|---|---|
| `STATE.md` | Where things stand: goal, focus, next step — read first |
| `AGENTS.md` | Rules for AI agents (`CLAUDE.md` and `GEMINI.md` import it; Codex and Cursor read it directly) |
| `.ai/` | `wr.py` helpers, `policy.py` (every machine-checked rule), Claude hooks, `checkpoint.py` |
| `.githooks/` | Git hooks: run `policy.py` on every commit, from any tool, and push |

Run `python .ai/wr.py --help` for the helpers. Scaffolded with WorkRealm {{WR_VERSION}} at the **{{TIER}}** tier.
