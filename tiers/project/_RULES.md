## Zones — a document lives in exactly one

The numbered folders are the workflow; sorting them alphabetically sorts them by stage of work.

| Zone | Holds | Enters when | Leaves when |
|---|---|---|---|
| `10-research/` | Anything unsettled: notes, sources, experiments | You start looking into something | It concludes → a decision or a prompt |
| `20-prompts/` | Prompts being shaped (`active/`) and already run (`archive/`) | You are shaping how to attack a problem | Run → `archive/`; output lands elsewhere |
| `30-decisions/` | Only what is settled | A decision is actually made | Never. Edited in place; Git holds history |
| `40-lab/` | Protocols and run results | There is something to test | Results feed `30-decisions/` |
| `50-release/` | Versioned snapshots handed to someone | You hand something over | Never. Immutable once cut |
| `90-archive/` | Superseded originals | A document is dissolved | Never |

**Moving a document between zones is a deliberate, committed act** (`git mv`). Never keep the
same content in two zones. `zone_guard` warns on crossings and blocks copies.

Where new work goes by default:

- A question you cannot answer yet → `10-research/notes/`
- Something to try → `10-research/experiments/EXP-<YYYYMMDD>-<topic>/`
- A prompt about to be run → `20-prompts/active/`, then `archive/`
- A test result → `40-lab/results/RUN-<YYYYMMDD>/`, **write-once**
- A conclusion → a row in `DECISIONS.md`, and an ADR if it needs the full argument

## Read-only evidence

`10-research/sources/`, `40-lab/results/`, `50-release/` and `90-archive/` are write-once:
new files yes, edits no. Enforced by `.ai/hooks/protect_paths.py`. A re-run is a new
`RUN-<date>/` folder; a correction to a release is a new version.

## Decisions are argued, not asserted

A decision that is expensive to reverse gets an ADR in `30-decisions/` (copy `ADR-TEMPLATE.md`):
the recommendation, the two strongest alternatives, why they lost, what would change my mind,
and the cost of reversal. `DECISIONS.md` gets a row pointing at it. Changing an ADR means editing
it in place **and** adding a row to its decision log with the old position and the reason — for
`30-decisions/`, that and the commit body are the only record of why a decision moved.

Read `STATE.md`, `30-decisions/DECISIONS.md` and `CONSTRAINTS.md` before proposing anything.

## Backups

The remote is one copy. Periodically also: `git bundle create ../{{NAME}}-backup.bundle --all`.
