# experiments

One folder per experiment, `YYYY-MM-DD-topic/` (`python .ai/wr.py exp new "<topic>"`):

```
2026-10-12-cache-warmup/
  README.md        question, method (or protocol), conclusion
  results/
    2026-10-12/    one folder per run: what ran, on which commit, raw output. Write-once.
    2026-10-14-02/ a re-run is a new folder (python .ai/wr.py run new <experiment>)
```

Results record numbers, not verdicts. Conclusions feed `docs/decisions/`.
