## Where things go

| Path | Holds | Rule |
|---|---|---|
| `10-research/notes/` | Questions, findings, drafts — anything unsettled | Free to edit |
| `10-research/sources/` | Downloaded material: docs, specs, datasheets, exports | **Read-only once saved** (hook-enforced) |
| `10-research/SOURCES_LOG.md` | One line per download | Append-only |
| `30-decisions/DECISIONS.md` | Settled decisions, one row each | Superseded by a new row, never silently edited |
| `30-decisions/OPEN-ITEMS.md` | Unresolved questions, with owner and trigger | Close by moving to *Closed* with the answer |
| `src/` | Code | — |

**A document lives in exactly one place.** Move it with `git mv`; never keep two copies.

## Sources are evidence

- Never edit a file in `10-research/sources/`. Derived output goes to `10-research/notes/`.
- Log every download in `SOURCES_LOG.md`: `[date] — [URL] — [local path] — [description]`.
- Notes and decisions cite the source they rest on.

## Decisions carry their reason

Each row in `DECISIONS.md` has: the decision, the strongest alternative and why it lost, and the
date. Changing a decision is a **new row** that names the one it supersedes.
A contradiction between two documents is an entry in `OPEN-ITEMS.md` — not something to resolve
by quietly picking one.

## Branches

Small edits go straight to `main`. Larger structural changes go on `ai/<feature>` and are merged
when done — and pushed while in progress, so nothing lives only on one disk.

## Long work

Every ~5 steps, summarise progress into `STATE.md` instead of holding it all in context.
Use subagents for broad searches or specialist work; it keeps the main context small.
