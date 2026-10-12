---
name: release
description: Cut an immutable versioned snapshot into releases/v<X.Y.Z>/ with a MANIFEST (source commit, file hashes) and a SUMMARY. Use when something is handed to someone - a report, a deliverable, a pilot package.
argument-hint: "[vX.Y.Z] [paths...]"
---

1. Commit everything first: a release is cut from a clean tree.
2. `python .ai/wr.py release cut v<X.Y.Z>[-label] --include <path> [<path> ...]`
3. Fill in `releases/v<X.Y.Z>/SUMMARY.md`: what it is, for whom, what changed, known limits.
   Claim no more than the evidence shows.
4. Commit: `python .ai/checkpoint.py "chore: release v<X.Y.Z>" "<what was handed over, to whom>"`.
5. Releases are immutable (R-EVIDENCE). A correction is a new version.
