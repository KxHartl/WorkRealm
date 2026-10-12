---
name: source
description: Save a downloaded document, spec, datasheet or export into 10-research/sources/ and log it in SOURCES_LOG.md. Use whenever material from the web or from the user is kept as evidence.
argument-hint: "[URL]"
---

Sources are evidence: saved once, never edited, always logged (rule R-SOURCES).

1. Download and log in one step:
   `python .ai/wr.py source add <URL> --desc "<what it is, version/date>"`
   If the file is already local (or the download needs a login), save it first and pass
   `--file <path>`; the URL is still logged as the origin.
2. Never edit the saved file. Extracts, summaries and conversions go to a note (`/note`) that cites it.
3. Commit: `python .ai/checkpoint.py "docs: add source <topic>"`.
