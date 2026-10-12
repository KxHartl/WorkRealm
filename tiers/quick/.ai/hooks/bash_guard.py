#!/usr/bin/env python3
"""PreToolUse hook on Bash / PowerShell -- the shell is not a way around the rules.

The check is `bash_verdict()` in .ai/policy.py. It blocks `--no-verify` (all tiers),
moving core.hooksPath away from .githooks, and shell commands that would change or
remove an existing file under a write-once path (rm, mv, sed -i, redirects, tee,
Remove-Item, Set-Content ...). It is a heuristic: it blocks only clear cases, and the
git pre-commit check catches anything it misses at commit time.

Exit 2 = block and show stderr to the model.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from policy import bash_hook_main  # noqa: E402

if __name__ == "__main__":
    sys.exit(bash_hook_main())
