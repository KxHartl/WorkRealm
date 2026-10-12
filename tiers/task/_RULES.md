## Where things go

> **R-PLACE** · enforced by: git

| Path | Holds | Rule |
|---|---|---|
| `10-research/notes/` | Questions, findings, drafts — anything unsettled | Free to edit |
| `10-research/sources/` | Downloaded material: docs, specs, datasheets, exports | **Read-only once saved** |
| `10-research/SOURCES_LOG.md` | One line per download | Append-only |
| `30-decisions/DECISIONS.md` | Settled decisions, one row each | Rows are superseded, never edited |
| `30-decisions/OPEN-ITEMS.md` | Unresolved questions, with owner and trigger | Close by moving to *Closed* with the answer |
| `src/` | Code | — |

**A document lives in exactly one place.** Move it with `git mv`; never keep two copies.

**Naming** (checked when a file is added): notes are `YYYY-MM-DD-topic` in lowercase kebab-case,
e.g. `10-research/notes/2026-10-12-vendor-comparison.md`. A folder of notes follows the same rule.

## Sources are evidence

> **R-SOURCES** · enforced by: git, claude

- Never edit or delete a file in `10-research/sources/`. Derived output goes to `10-research/notes/`.
- Log every download in `SOURCES_LOG.md`, in the same commit:
  `[date] — [URL] — [local path] — [description]`. A source without a log line is refused,
  and lines are never removed from the log.
- Notes and decisions cite the source they rest on.

## Decisions carry their reason

> **R-DECISIONS** · enforced by: git

Each row in `DECISIONS.md` has: the date, the decision, and the strongest alternative and why it
lost. A settled row is **never edited or removed**: changing a decision is a **new row** that names
the one it supersedes. Each open item in `OPEN-ITEMS.md` has an owner and a trigger — an item
without a trigger is a wish. A commit that touches `30-decisions/` has a body that says why.
A contradiction between two documents is an entry in `OPEN-ITEMS.md` — not something to resolve
by quietly picking one.

## Branches

> **R-BRANCH** · advisory

Small edits go straight to `main`. Larger structural changes go on `ai/<feature>` and are merged
when done — and pushed while in progress, so nothing lives only on one disk.

## Long work

> **R-LONG** · advisory

Every ~5 steps, summarise progress into `STATE.md` instead of holding it all in context.
Use subagents for broad searches or specialist work; it keeps the main context small.
