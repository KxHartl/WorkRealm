---
name: experiment
description: Set up an experiment (experiments/<date>-<topic>/ with question, method, conclusion) or record a new write-once run of one (experiments/<exp>/results/<date>/). Use when trying something out, running a test protocol or benchmark, or recording test results.
argument-hint: "[topic or experiment]"
---

- **Something to try:** `python .ai/wr.py exp new "<topic>"`, then fill in Question and Method
  (or the protocol, step by step).
- **A run:** `python .ai/wr.py run new <experiment-folder>` creates `results/<date>[-NN]/` with the
  commit under test. Record numbers and raw output, not verdicts. Results are write-once
  (R-EVIDENCE): a re-run is a new folder.
- Fill in the experiment's Conclusion from the numbers. A decision drawn from it goes through
  `/decide` or `/adr`; an experiment never writes a decision itself.

Commit after each logical step: `python .ai/checkpoint.py "test(<experiment>): <what ran>"`.
