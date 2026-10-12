#!/usr/bin/env python3
"""Commit everything as one logical unit, after a secrets check.

    python .ai/checkpoint.py "feat: what changed" ["body: why it changed"]

The post-commit hook pushes. Staging is `git add -A`, so .gitignore is the
filter -- and this script is the second filter for files that slipped past it.
"""
import re
import subprocess
import sys

SECRETISH = re.compile(r"(^|/)(\.env(\..+)?|.*\.pem|.*\.key|id_rsa[^/]*|credentials\.json)$", re.I)
ALLOWED = {".env.example"}


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True)


def main() -> int:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print('usage: python .ai/checkpoint.py "type: subject" ["body"]', file=sys.stderr)
        return 1

    git("add", "-A")
    staged = git("diff", "--cached", "--name-only").stdout.splitlines()
    if not staged:
        print("checkpoint: nothing to commit.")
        return 0

    leaks = [f for f in staged if SECRETISH.search(f) and f.rsplit("/", 1)[-1] not in ALLOWED]
    if leaks:
        git("reset", "-q")
        print("checkpoint: REFUSED -- these look like secrets:\n  " + "\n  ".join(leaks)
              + "\nAdd them to .gitignore. Nothing was committed.", file=sys.stderr)
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
