# releases

One folder per handed-over version, `vMAJOR.MINOR.PATCH[-label]/`, each with a `MANIFEST.md`
(what it contains, source commit, file hashes) and a `SUMMARY.md` (what it is, for whom, known
limits). Cut one with `python .ai/wr.py release cut v1.0.0 --include <paths>`.

**Immutable once cut.** A correction is a new version, never an edit.
