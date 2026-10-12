#!/usr/bin/env python3
"""Claude Code status line: workspace, tier, branch, uncommitted, unpushed, open items, phase.

Configured in .claude/settings.json ("statusLine"). Reads the session JSON on stdin only
to find the project; everything shown comes from git and the workspace files.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> int:
    try:
        json.load(sys.stdin)
    except Exception:
        pass
    try:
        from wr import git_summary, meta, open_items, phase
        m, g = meta(), git_summary()
        parts = [f"{m.get('name', '?')} [{m.get('tier', '?')}]", g["branch"]]
        parts.append(f"{g['dirty']} uncommitted" if g["dirty"] else "clean")
        if not g["remote"]:
            parts.append("no remote")
        elif g["unpushed"]:
            parts.append(f"{g['unpushed']} unpushed")
        items = open_items()
        if items:
            parts.append(f"{items} open items")
        ph = phase()
        if ph:
            parts.append(f"phase: {ph}")
        print(" | ".join(parts))
    except Exception:
        print("WorkRealm")
    return 0


if __name__ == "__main__":
    sys.exit(main())
