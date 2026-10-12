#!/usr/bin/env python3
"""Commit everything as one logical unit, after the policy checks.

    python .ai/checkpoint.py "feat: what changed" ["body: why it changed"]
    python .ai/checkpoint.py --agent researcher "docs: add vendor spec" "why"

Staging is `git add -A`, so .gitignore is the first filter and .ai/policy.py the
second. On a block, everything is unstaged again so nothing half-checked lingers.
The git hooks run the same checks, and post-commit pushes.

--agent NAME marks the commit as work a subagent did on its own: the subject gets the
robot tag and the message an `AI-Agent: NAME` trailer. In Claude Code the bash hook adds
it automatically for subagents and refuses it from the main agent, so nobody has to
remember. Commits made at the user's prompt stay unmarked.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from policy import AI_TAG, ROOT, report, safe_stderr, staged_findings  # noqa: E402


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")


def mark(subject: str) -> str:
    """`type(scope): what` -> `type(scope): <tag> what`."""
    m = re.match(r"^([a-z]+(\([^)]*\))?!?:)\s*(.*)$", subject)
    return f"{m.group(1)} {AI_TAG} {m.group(3)}" if m else f"{AI_TAG} {subject}"


def main(argv: list[str] | None = None) -> int:
    safe_stderr()
    p = argparse.ArgumentParser(prog="python .ai/checkpoint.py", description=__doc__.split("\n\n")[0])
    p.add_argument("subject", help='Conventional Commit subject, e.g. "feat: add parser"')
    p.add_argument("body", nargs="?", help="why it changed")
    p.add_argument("--agent", help="the subagent that did this work (set by the hook)")
    args = p.parse_args(argv)
    if not args.subject.strip():
        p.error("the subject is empty")

    git("add", "-A")
    if not git("diff", "--cached", "--name-only").stdout.strip():
        print("checkpoint: nothing to commit.")
        return 0

    if report(staged_findings(ROOT), "checkpoint"):
        git("reset", "-q")
        print("checkpoint: nothing was committed.", file=sys.stderr)
        return 2

    subject = mark(args.subject) if args.agent else args.subject
    msg = ["-m", subject] + (["-m", args.body] if args.body else [])
    if args.agent:
        msg += ["-m", f"AI-Agent: {args.agent}"]
    r = git("commit", "-q", *msg)
    if r.returncode != 0:
        print(r.stdout + r.stderr, file=sys.stderr)
        return r.returncode
    try:
        sys.stdout.reconfigure(errors="backslashreplace")
    except Exception:
        pass
    print(git("log", "--oneline", "-1").stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
