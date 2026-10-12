---
name: open-item
description: Record an unresolved question in 30-decisions/OPEN-ITEMS.md with an owner and a trigger, or close one with its answer. Use when something must be answered by someone before work can proceed, or when two documents contradict each other.
argument-hint: "[question]"
---

Open items carry an owner and a trigger: the point by which they must be answered (R-DECISIONS).

- **Open:** `python .ai/wr.py open-item "<question>" --owner <who> --trigger "<by when / before what>" [--notes "..."]`
- **Close:** `python .ai/wr.py close-item O<n> "<answer>"`. If the answer is a decision, also use `/decide`.
- A contradiction between two documents is an open item. Never resolve it by quietly picking one.

Commit with a body that says why: `python .ai/checkpoint.py "docs: open item <topic>" "<why it matters>"`.
