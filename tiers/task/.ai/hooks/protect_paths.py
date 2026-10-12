#!/usr/bin/env python3
"""PreToolUse hook -- existing files under protected paths are read-only.

The check itself is `write_verdict(..., "protected_paths", ...)` in .ai/policy.py,
shared with the git pre-commit hook (which also catches shell writes, at commit
time). Protected paths are listed in .workrealm.json ("protected").

Exit 2 = block and show stderr to the model.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from policy import hook_main  # noqa: E402

if __name__ == "__main__":
    sys.exit(hook_main("protected_paths"))
