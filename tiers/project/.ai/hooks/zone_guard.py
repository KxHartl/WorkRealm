#!/usr/bin/env python3
"""PreToolUse hook -- keep the zones meaning something.

Ported from KEV-Ai-Architecture. A taxonomy nobody enforces is just a folder
listing: within a month there is a decision in 10-research/ and a note in
30-decisions/. This mostly WARNS -- crossing zones is how work progresses; what
is not fine is crossing without noticing. It blocks two category errors:

  * a decision document (ADR-*, DECISIONS, OPEN-ITEMS, CONSTRAINTS) outside
    30-decisions/ or 90-archive/
  * CREATING a document whose name already exists in another zone (a copy)

Both checks skip structural names (README.md etc.) and edits to files that
already exist -- without those exclusions the guard refuses legitimate writes
forever (found the hard way in KEV).

Exit 0 = allow (notes printed), exit 2 = block.
"""
import json
import os
import re
import sys
from pathlib import Path

ZONES = ("10-research", "20-prompts", "30-decisions", "40-lab", "50-release", "90-archive")
DECISION_DOC = re.compile(r"^(ADR-\d+|DECISIONS|OPEN-ITEMS|CONSTRAINTS)", re.I)
STRUCTURAL = {
    "README.md", "AGENTS.md", "CLAUDE.md", "INDEX.md", "MANIFEST.md", "STATE.md",
    "__init__.py", "conftest.py", ".gitkeep", ".gitignore",
}


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    raw = payload.get("tool_input", {}).get("file_path", "")
    if not raw:
        return 0

    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ".").resolve()
    try:
        rel = Path(raw).resolve().relative_to(root).as_posix()
    except ValueError:
        return 0
    head = rel.split("/", 1)[0]
    zone = head if head in ZONES else None
    name = Path(rel).name
    exists = Path(raw).exists()

    if DECISION_DOC.search(name) and name != "ADR-TEMPLATE.md" and zone not in ("30-decisions", "90-archive"):
        print(
            f"BLOCKED: {rel}\n"
            "  Decision documents live in 30-decisions/. If it is not settled yet, it is\n"
            "  research -- 10-research/notes/.",
            file=sys.stderr,
        )
        return 2

    if zone and not exists and name not in STRUCTURAL:
        for other in ZONES:
            if other == zone or not (root / other).is_dir():
                continue
            for dup in (root / other).rglob(name):
                if dup.is_file():
                    print(
                        f"BLOCKED: {rel}\n"
                        f"  '{name}' already exists at {dup.relative_to(root).as_posix()}.\n"
                        "  A document lives in exactly one zone. MOVE it with `git mv`; never copy.",
                        file=sys.stderr,
                    )
                    return 2

    if zone == "30-decisions" and exists:
        print(
            f"NOTE: editing {rel} -- the settled zone. Confirm the decision change is deliberate\n"
            "  and add a decision-log row with the previous position and the reason.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
