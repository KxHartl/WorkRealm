## Where things go

> **R-PLACE** · enforced by: git

| Path | Holds | Rule |
|---|---|---|
| `STATE.md` | Goal, focus, next step, who is waiting on what | Read first, keep short |
| `docs/notes/` | Findings, comparisons, drafts, questions: anything unsettled | Free to edit; `YYYY-MM-DD-topic.md` |
| `docs/decisions/` | `DECISIONS.md` (what is settled), `OPEN-ITEMS.md` (what is not) | See R-DECISIONS |
| `references/` | Evidence: downloaded docs, specs, datasheets, exports | **Write-once**, logged in `SOURCES_LOG.md` |
| `src/` · `tests/` | Code and its tests | Tests sit next to the behaviour they prove |
| `reports/` | Deliverables being written: reports, memos, slides, figures | Free to edit |

**A document lives in exactly one place.** Move it with `git mv`; never keep two copies.
Names follow R-NAMES. Notes are dated, checked when added:
`docs/notes/2026-10-12-vendor-comparison.md`. `python .ai/wr.py note "<topic>"` names it for you.

## Sources are evidence

> **R-SOURCES** · enforced by: git, claude

- Never edit or delete a file in `references/`. Extracts and summaries go to a note that cites it.
- Every source has a line in `references/SOURCES_LOG.md` in the same commit, and the log only
  grows. `python .ai/wr.py source add <URL> --desc "..."` (or `--file <path>`) saves and logs it.
- Every claim in a note, decision or report cites the source it rests on.

## Decisions carry their reason

> **R-DECISIONS** · enforced by: git

- Each row in `docs/decisions/DECISIONS.md` has the date, the decision, and the strongest
  alternative with why it lost: `python .ai/wr.py decide "..." --alt "... -- why it lost"`.
- A settled row is **never edited or removed**. Changing a decision is a new row that names the
  one it supersedes (`--supersedes D<n>`).
- Each open item in `OPEN-ITEMS.md` has an owner and a trigger, the point by which it must be
  answered: `python .ai/wr.py open-item "..." --owner ... --trigger ...`; close it with
  `close-item O<n> "answer"`.
- A commit that touches `docs/decisions/` has a body that says why.
- A contradiction between two documents is an open item, not something to resolve by quietly
  picking one. Only the owner decides; an agent proposes.

## Branches

> **R-BRANCH** · advisory

Small edits go straight to `main`. Larger structural changes go on a `<type>/<short-desc>` branch (R-NAMES) and are merged
when done, and pushed while in progress so nothing lives only on one disk.

## Long work and specialists

> **R-LONG** · advisory

Every ~5 steps, summarise progress into `STATE.md` instead of holding it all in context.
Hand broad searches and specialist work to subagents; it keeps the main context small.
The specialists in `.claude/agents/` (`researcher`, `reviewer`; at the project tier also
`decision_keeper`, `lab_runner`, `releaser`) and the synced skills come from `~/.agentbrain` via
`wr sync`. Change them there, never in place: a sync overwrites them.

## Lessons flow back

> **R-LEARN** · advisory

When something costs time and would cost it again elsewhere (a tool quirk, a failure mode, a
pattern that worked), write it down where it will be found. General lessons go to
`~/.agentbrain/gotchas/` or `skills/` (format: `~/.agentbrain/_TEMPLATE.md`), committed there.
Lessons specific to this workspace go to a note, a decision or `STATE.md` *Notes*.
