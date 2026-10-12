#!/usr/bin/env python3
"""PreToolUse hook -- existing files under protected paths are read-only.

Protected paths are listed in .workrealm.json ("protected"), so `wr upgrade`
widens them without touching this script. Creating a NEW file there is allowed
(a download, a new run log, a new release); modifying one that exists is not --
an edited source or result is worthless as evidence.

Covers Write/Edit tools only. A shell command can still change these files;
the rule in AGENTS.md covers that, and this hook catches the common path.

Exit 2 = block and show stderr to the model.
"""
import json
import os
import sys
from pathlib import Path


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # never break the session on a malformed payload

    raw = payload.get("tool_input", {}).get("file_path") or payload.get("tool_input", {}).get("notebook_path")
    if not raw:
        return 0

    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ".").resolve()
    try:
        protected = json.loads((root / ".workrealm.json").read_text(encoding="utf-8")).get("protected", [])
    except Exception:
        return 0
    try:
        rel = Path(raw).resolve().relative_to(root).as_posix()
    except ValueError:
        return 0  # outside the workspace

    for prefix in protected:
        if rel != prefix and not rel.startswith(prefix.rstrip("/") + "/"):
            continue
        if not Path(raw).exists():
            print(f"NOTE: creating {rel} under protected {prefix}/ -- it becomes read-only once written.",
                  file=sys.stderr)
            return 0
        print(
            f"BLOCKED: {rel}\n"
            f"  {prefix}/ is write-once (see AGENTS.md). Existing files there are evidence.\n"
            "  Derived work goes to 10-research/notes/; a re-run or new version is a NEW file or folder.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
