#!/usr/bin/env python3
"""Stop hook -- refuse to finish a response with uncommitted work.

The commit rule in AGENTS.md is prose, and prose is probabilistic: compliance
fades as context fills. This hook is the layer that binds.

If `git status` itself fails, that matters more than any uncommitted file (a
corrupt index, a sync tool writing into .git/), so it says so loudly.

MUST honour stop_hook_active, or it loops forever. Exit 2 = keep working.
"""
import json
import subprocess
import sys


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("stop_hook_active"):
        return 0  # already told once; do not loop

    try:
        r = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, timeout=15)
    except Exception as e:
        print(f"WARNING: could not run git ({e}). Commit manually.", file=sys.stderr)
        return 0

    if r.returncode != 0:
        print(
            f"STOP: `git status` failed.\n  {r.stderr.strip()}\n"
            "  Do NOT keep writing files. Check for a corrupt index or '*conflicted copy*'\n"
            "  files in .git/ before anything else; the remote is the backup.",
            file=sys.stderr,
        )
        return 2

    dirty = [ln for ln in r.stdout.splitlines() if ln.strip()]
    if not dirty:
        return 0
    listing = "\n".join(f"    {ln}" for ln in dirty[:15])
    more = f"\n    ... and {len(dirty) - 15} more" if len(dirty) > 15 else ""
    print(
        f"STOP: {len(dirty)} uncommitted change(s).\n{listing}{more}\n\n"
        "  Commit each logical unit before finishing:\n"
        '    python .ai/checkpoint.py "type: what changed"',
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
