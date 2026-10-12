#!/usr/bin/env python3
"""SessionStart hook -- every session starts from STATE.md, not from nothing.

Claude Code adds a SessionStart hook's stdout to the model's context. On startup,
resume and clear it prints the workspace status and STATE.md; after a compaction
(source "compact") it adds that STATE.md is now the memory that survived.
PreCompact output never reaches the model, which is why this runs after, not before.

Never fails the session: any error prints nothing and exits 0.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    try:
        from wr import status_text
        text = status_text()
    except Exception:
        return 0
    if payload.get("source") == "compact":
        text = ("Context was just compacted. STATE.md below is what survived: if the last steps are "
                "not in it, update it now and commit.\n\n" + text)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
