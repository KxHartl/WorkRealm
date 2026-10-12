#!/usr/bin/env python3
"""PreToolUse hook -- every document keeps one home.

The check is `write_verdict(..., "zone_placement", ...)` in .ai/policy.py, shared with
the git pre-commit hook. Folders come from "zones" in .workrealm.json. It blocks two
category errors:

  * a decision document (DECISIONS.md, OPEN-ITEMS.md, CONSTRAINTS.md, ADR-*) outside the
    decisions folder (or the archive / a release snapshot)
  * CREATING a file whose name already exists in another folder (a copy)

and notes edits to settled decisions. Structural names (README.md etc.), edits to existing
files and release snapshots are exempt; without that a guard refuses legitimate writes.

Exit 0 = allow (notes printed), exit 2 = block.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from policy import hook_main  # noqa: E402

if __name__ == "__main__":
    sys.exit(hook_main("zone_placement"))
