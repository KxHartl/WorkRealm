---
name: note
description: Start a dated note in docs/notes/ for anything unsettled - findings, comparisons, drafts, questions. Use when investigating something whose conclusion is not yet a decision.
argument-hint: "[topic]"
---

1. `python .ai/wr.py note "<topic>"` creates `docs/notes/<date>-<topic>.md` with the right name (R-PLACE).
2. Write the findings. Cite the source each claim rests on (`references/...` or a URL).
3. When it concludes, it becomes a decision (`/decide`) or an open item (`/open-item`). The note stays as the record.
4. Commit: `python .ai/checkpoint.py "docs(notes): <topic>"`.
