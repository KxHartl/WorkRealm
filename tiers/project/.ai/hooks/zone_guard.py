#!/usr/bin/env python3
"""PreToolUse hook -- keep the zones meaning something.

Ported from KEV-Ai-Architecture. The check is `write_verdict(..., "zone_placement", ...)`
in .ai/policy.py, shared with the git pre-commit hook. It blocks two category errors:

  * a decision document (ADR-*, DECISIONS, OPEN-ITEMS, CONSTRAINTS) outside
    30-decisions/ or 90-archive/
  * CREATING a document whose name already exists in another zone (a copy)

and notes edits to 30-decisions/. Structural names (README.md etc.) and edits to
existing files are exempt -- without that the guard refuses legitimate writes forever.

Exit 0 = allow (notes printed), exit 2 = block.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from policy import hook_main  # noqa: E402

if __name__ == "__main__":
    sys.exit(hook_main("zone_placement"))
