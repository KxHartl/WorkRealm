---
name: source
description: Save a downloaded document, spec, datasheet or export as evidence in references/ and log it in SOURCES_LOG.md (at the project tier, stage it in references/inbox/ for the owner to promote). Use whenever material from the web or from the user is kept as evidence.
argument-hint: "[URL]"
---

Sources are evidence: saved once, never edited, always logged (rules R-SOURCES, R-INBOX).

1. Save it in one step:
   `python .ai/wr.py source add <URL> --desc "<what it is, version/date>"`
   If the file is already local (or the download needs a login), save it first and pass
   `--file <path>`; the URL is still recorded as the origin.
   - Task tier: it goes straight into `references/` with a log line.
   - Project tier: it goes into `references/inbox/`. Tell the user it is waiting; promoting it is
     their call (`python .ai/wr.py source promote <file>`, which asks them before it runs).
2. Never edit a saved source. Extracts, summaries and conversions go to a note (`/note`) that cites it.
3. Commit: `python .ai/checkpoint.py "docs: add source <topic>"`.
