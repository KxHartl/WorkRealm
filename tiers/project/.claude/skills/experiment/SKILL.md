---
name: experiment
description: Set up an experiment folder (10-research/experiments/EXP-<date>-<topic>/) or a write-once lab run folder (40-lab/results/RUN-<date>/). Use when trying something out, or when executing a test protocol and recording results.
argument-hint: "[topic]"
---

- **Something to try:** `python .ai/wr.py exp new "<topic>"`, then fill in Hypothesis, Method,
  Result and Conclusion.
- **A protocol run:** `python .ai/wr.py run new "<topic>"` creates a new `RUN-<date>[-NN]/`.
  Record numbers, not verdicts. Results are write-once (R-EVIDENCE): a re-run is a new folder.
- Conclusions feed `30-decisions/` through `/decide` or `/adr`; an experiment never writes a
  decision itself.

Commit after each logical step: `python .ai/checkpoint.py "test(lab): <what ran>"`.
