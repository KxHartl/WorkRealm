---
name: adr
description: Create an Architecture Decision Record in docs/decisions/adr/ for a decision that is expensive to reverse - recommendation, two strongest alternatives, what would change my mind, cost of reversal. Use when a decision needs its full argument, or to revise an existing ADR.
argument-hint: "[title]"
---

Decisions are argued, not asserted (rule R-ADR). Read `docs/decisions/DECISIONS.md` and
`CONSTRAINTS.md` first.

**New ADR**
1. `python .ai/wr.py adr new "<title>"` creates `docs/decisions/adr/NNNN-<title>.md` from the template.
2. Fill in every section: Context (cite sources), Decision, Alternatives (the two strongest and
   why they lost), What would change my mind, Cost of reversal.
3. Add a register row:
   `python .ai/wr.py decide "<decision>" --alt "<alt> -- <why>" --detail docs/decisions/adr/NNNN-<title>.md`

**Revising an ADR**: edit it in place **and** add a row to its *Decision log* (date, change,
previous position, reason).

Commit with a body that says why: `python .ai/checkpoint.py "docs(adr): <title>" "<why>"`.
