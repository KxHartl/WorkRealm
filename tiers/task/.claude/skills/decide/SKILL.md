---
name: decide
description: Record a settled decision in docs/decisions/DECISIONS.md with its date and the strongest alternative and why it lost. Use when the user decides something, approves a recommendation, or a choice is clearly settled. Not for open questions (use open-item) or drafts (use note).
argument-hint: "[the decision]"
---

Record a decision (rule R-DECISIONS in AGENTS.md).

1. Confirm it is actually settled. Only the owner decides; if the user has not decided, it is a
   note or an open item.
2. Identify the **strongest alternative** and why it lost. If you do not know, ask; never invent one.
3. If it replaces an earlier decision, find that row (`D<n>`) in `docs/decisions/DECISIONS.md`.
   Settled rows are never edited: the new row supersedes the old one.
4. Run:
   `python .ai/wr.py decide "<decision>" --alt "<alternative> -- <why it lost>" [--supersedes D<n>] [--detail <ADR or note>]`
5. At the project tier, a decision that is expensive to reverse also needs an ADR (`/adr`).
6. Commit with a body that says why:
   `python .ai/checkpoint.py "docs: decide <topic>" "<why>"`.
