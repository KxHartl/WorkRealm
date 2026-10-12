## The project layout

> **R-ZONES** · enforced by: git, claude

The task-tier folders, plus:

| Path | Holds | Rule |
|---|---|---|
| `docs/plans/` | Plans, roadmaps, phases with exit criteria | Free to edit; `python .ai/wr.py plan new` |
| `docs/decisions/adr/` | One ADR per expensive-to-reverse decision: `NNNN-title.md` | See R-ADR |
| `docs/decisions/CONSTRAINTS.md` | Confirmed inputs: budgets, deadlines, mandates, and what flips if one is wrong | Cite who confirmed it |
| `references/inbox/` | Downloads waiting for review | See R-INBOX |
| `data/raw/` · `data/processed/` | Input data as received · anything derived from it | `raw/` is write-once; `processed/` is reproducible |
| `experiments/YYYY-MM-DD-topic/` | `README.md` (question, method, conclusion) and `results/` | One folder per experiment |
| `experiments/*/results/YYYY-MM-DD[-NN]/` | One folder per run: commit, environment, raw output | Write-once; a re-run is a new folder |
| `releases/vX.Y.Z/` | What was handed to someone, with `MANIFEST.md` and `SUMMARY.md` | Immutable |
| `archive/` | Superseded originals, moved with `git mv` | Write-once |

A decision document (`DECISIONS.md`, `OPEN-ITEMS.md`, `CONSTRAINTS.md`, an ADR) outside
`docs/decisions/` is refused, and so is a copy of a file from one folder into another: move it
with `git mv`. Releases are the one exception: a release is a snapshot and holds copies on purpose.
Helpers create each of these with the right name: `plan new`, `adr new`, `exp new`,
`run new <experiment>`, `release cut`.

## Read-only evidence

> **R-EVIDENCE** · enforced by: git, claude

`references/` (apart from the inbox), `data/raw/`, every `experiments/*/results/`, `releases/` and
`archive/` are write-once: new files yes, edits and deletions no. Results record numbers, not
verdicts; a correction to a release is a new version.

## Evidence goes through the inbox

> **R-INBOX** · enforced by: claude

Agents never add to `references/` directly at this tier. New material goes to
`references/inbox/` (`python .ai/wr.py source add <URL> --desc "..."`). The owner decides what
becomes evidence: `python .ai/wr.py source promote <file>` moves it in and logs it, and Claude Code
asks the user before running it. Delete what is not worth keeping.

## Decisions are argued, not asserted

> **R-ADR** · enforced by: git

A decision that is expensive to reverse gets an ADR (`python .ai/wr.py adr new "<title>"`): the
recommendation, the two strongest alternatives and why they lost, what would change my mind, and
the cost of reversal. An ADR missing a section is refused. `DECISIONS.md` gets a row pointing at it.
Changing an ADR means editing it in place **and** adding a row to its decision log with the old
position and the reason (a change without one draws a warning).

Read `STATE.md`, `DECISIONS.md` and `CONSTRAINTS.md` before proposing anything.

## Backups

> **R-BACKUP** · advisory

The remote is one copy. Periodically also: `git bundle create ../{{NAME}}-backup.bundle --all`.
