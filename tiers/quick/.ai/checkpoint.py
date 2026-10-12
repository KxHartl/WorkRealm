#!/usr/bin/env python3
"""Commit everything as one logical unit, after the policy checks.

    python .ai/checkpoint.py "feat: what changed" ["body: why it changed"]

Staging is `git add -A`, so .gitignore is the first filter and .ai/policy.py the
second. On a block, everything is unstaged again so nothing half-checked lingers.
The git hooks run the same checks, and post-commit pushes.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from policy import ROOT, report, safe_stderr, staged_findings  # noqa: E402


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def main() -> int:
    safe_stderr()
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print('usage: python .ai/checkpoint.py "type: subject" ["body"]', file=sys.stderr)
        return 1

    git("add", "-A")
    if not git("diff", "--cached", "--name-only").stdout.strip():
        print("checkpoint: nothing to commit.")
        return 0

    if report(staged_findings(ROOT), "checkpoint"):
        git("reset", "-q")
        print("checkpoint: nothing was committed.", file=sys.stderr)
        return 2

    msg = ["-m", sys.argv[1]] + (["-m", sys.argv[2]] if len(sys.argv) > 2 else [])
    r = git("commit", "-q", *msg)
    if r.returncode != 0:
        print(r.stdout + r.stderr, file=sys.stderr)
        return r.returncode
    print(git("log", "--oneline", "-1").stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
