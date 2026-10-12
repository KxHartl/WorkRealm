## Zones — a document lives in exactly one

> **R-ZONES** · enforced by: git, claude

The numbered folders are the workflow; sorting them alphabetically sorts them by stage of work.

| Zone | Holds | Enters when | Leaves when |
|---|---|---|---|
| `10-research/` | Anything unsettled: notes, sources, experiments | You start looking into something | It concludes → a decision or a prompt |
| `20-prompts/` | Prompts being shaped (`active/`) and already run (`archive/`) | You are shaping how to attack a problem | Run → `archive/`; output lands elsewhere |
| `30-decisions/` | Only what is settled | A decision is actually made | Never. ADRs change in place with a decision-log row; the `DECISIONS.md` register only grows |
| `40-lab/` | Protocols and run results | There is something to test | Results feed `30-decisions/` |
| `50-release/` | Versioned snapshots handed to someone | You hand something over | Never. Immutable once cut |
| `90-archive/` | Superseded originals | A document is dissolved | Never |

**Moving a document between zones is a deliberate, committed act** (`git mv`). Never keep the
same content in two zones. Decision documents outside `30-decisions/` and copies across zones are
refused; the Claude hook also notes every edit to `30-decisions/`.

Where new work goes by default, and how it is named (checked when added):

- A question you cannot answer yet → `10-research/notes/YYYY-MM-DD-topic.md`
- Something to try → `10-research/experiments/EXP-<YYYYMMDD>-<topic>/`
- A prompt about to be run → `20-prompts/active/YYYY-MM-DD-topic.md`, then `archive/`
- A test result → `40-lab/results/RUN-<YYYYMMDD>[-NN]/`, **write-once**
- A conclusion → a row in `DECISIONS.md`, and `30-decisions/ADR-<NN>-<topic>.md` if it needs the
  full argument
- A hand-over → `50-release/v<MAJOR>.<MINOR>.<PATCH>[-label]/`

## Read-only evidence

> **R-EVIDENCE** · enforced by: git, claude

`10-research/sources/`, `40-lab/results/`, `50-release/` and `90-archive/` are write-once:
new files yes, edits and deletions no. A re-run is a new `RUN-<date>/` folder; a correction to a
release is a new version.

## Decisions are argued, not asserted

> **R-ADR** · enforced by: git

A decision that is expensive to reverse gets an ADR in `30-decisions/` (copy `ADR-TEMPLATE.md`):
the recommendation, the two strongest alternatives, why they lost, what would change my mind,
and the cost of reversal — an ADR missing one of those sections is refused. `DECISIONS.md` gets a
row pointing at it. Changing an ADR means editing it in place **and** adding a row to its decision
log with the old position and the reason (a change without one draws a warning). That row and the
commit body are the record of why a decision moved.

Read `STATE.md`, `30-decisions/DECISIONS.md` and `CONSTRAINTS.md` before proposing anything.

## Backups

> **R-BACKUP** · advisory

The remote is one copy. Periodically also: `git bundle create ../{{NAME}}-backup.bundle --all`.
