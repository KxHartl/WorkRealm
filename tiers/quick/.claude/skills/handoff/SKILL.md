---
name: handoff
description: Prepare the workspace for the next session - update STATE.md with what was done, the next step and blockers, then commit. Use when the user is wrapping up, says "handoff", "end of session" or "save progress", or before a long pause.
---

1. Run `python .ai/wr.py handoff` and read the status it prints.
2. Update `STATE.md`: what was done this session, the **next concrete step**, and anything
   blocking or waiting on the owner. Keep it short; detail belongs in notes or decisions.
3. If a question must be answered by someone, record it (task tier and up):
   `python .ai/wr.py open-item "<question>" --owner <who> --trigger "<by when>"`.
4. Commit: `python .ai/checkpoint.py "docs: update STATE for handoff" "<one line on where things stand>"`.
5. Tell the user what the next session will start from.
