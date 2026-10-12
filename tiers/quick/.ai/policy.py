#!/usr/bin/env python3
"""WorkRealm policy core -- every machine-checked rule lives here, once.

Prose rules are followed some of the time; checks bind. Every caller shares this
file, so a rule cannot drift between layers:

    git pre-commit   python .ai/policy.py pre-commit       (binds every tool and human)
    git commit-msg   python .ai/policy.py commit-msg FILE
    Claude hooks     .ai/hooks/*.py import write_verdict()
    checkpoint.py    imports staged_findings()

Which checks run is data: the "checks" list in .workrealm.json, set per tier.
Rule IDs (R-...) point at the rule text in AGENTS.md; the text is not repeated here.

Exit codes: 0 = pass (warnings may print), 1 = blocked.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
META = ".workrealm.json"

# Which rule each check enforces, and by which layer. tests/test_wr.py asserts that
# every rule tagged "enforced by" in AGENTS.md appears here with those layers.
ENFORCES = {
    "R-LANG": {"git": ["english"]},
    "R-COMMIT": {"git": ["commit_msg"], "claude": ["checkpoint_gate.py"]},
    "R-SECRETS": {"git": ["secrets"]},
    "R-PLACE": {"git": ["naming"]},
    "R-SOURCES": {"git": ["protected_paths", "sources_logged"], "claude": ["protect_paths.py"]},
    "R-DECISIONS": {"git": ["decision_register", "decision_commit_body"]},
    "R-ZONES": {"git": ["zone_placement"], "claude": ["zone_guard.py"]},
    "R-EVIDENCE": {"git": ["protected_paths"], "claude": ["protect_paths.py"]},
    "R-ADR": {"git": ["adr_format"]},
}

SECRETISH = re.compile(r"(^|/)(\.env(\..+)?|.*\.pem|.*\.key|id_rsa[^/]*|credentials\.json)$", re.I)
SECRET_ALLOWED = {".env.example"}
STRUCTURAL = {
    "README.md", "AGENTS.md", "CLAUDE.md", "GEMINI.md", "INDEX.md", "MANIFEST.md", "STATE.md",
    "__init__.py", "conftest.py", ".gitkeep", ".gitignore",
}
ZONES = ("10-research", "20-prompts", "30-decisions", "40-lab", "50-release", "90-archive")
DECISION_DOC = re.compile(r"^(ADR-\d+|DECISIONS|OPEN-ITEMS|CONSTRAINTS)", re.I)
ADR_FILE = re.compile(r"^ADR-\d+.*\.md$")
ADR_SECTIONS = ("## Decision", "## Alternatives", "## What would change my mind",
                "## Cost of reversal", "## Decision log")
CONVENTIONAL = re.compile(
    r"^(feat|fix|docs|chore|refactor|test|perf|build|ci|style|revert)(\([\w./-]+\))?!?: \S")
EXEMPT_MSG = re.compile(r"^(Merge |Revert \"|fixup! |squash! |amend! )")
NON_ENGLISH = re.compile("[\u010d\u0107\u017e\u0161\u0111\u010c\u0106\u017d\u0160\u0110]")  # Croatian letters
TEXT_EXT = {".md", ".txt", ".py", ".ps1", ".sh", ".json", ".yaml", ".yml", ".toml", ".js", ".ts"}
SOURCES = "10-research/sources"
SOURCES_LOG = "10-research/SOURCES_LOG.md"
DECISIONS = "30-decisions/DECISIONS.md"
OPEN_ITEMS = "30-decisions/OPEN-ITEMS.md"


class Finding:
    def __init__(self, level: str, rule: str, text: str):
        self.level, self.rule, self.text = level, rule, text

    def __str__(self) -> str:
        tag = "BLOCKED" if self.level == "block" else "WARNING"
        return f"{tag} [{self.rule}] {self.text}"


def block(rule: str, text: str) -> Finding:
    return Finding("block", rule, text)


def warn(rule: str, text: str) -> Finding:
    return Finding("warn", rule, text)


# ---------------------------------------------------------------- plumbing

def safe_stderr() -> None:
    """A non-ASCII path on a cp1252 console must not crash a hook (a crash refuses the commit)."""
    try:
        sys.stderr.reconfigure(errors="backslashreplace")
    except Exception:
        pass


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-c", "core.quotepath=off", *args], cwd=root,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def load_meta(root: Path) -> dict:
    try:
        return json.loads((root / META).read_text(encoding="utf-8"))
    except Exception:
        return {}


def staged_changes(root: Path) -> list[tuple[str, str]]:
    """(status, path) for every staged change. Renames count as delete + add."""
    out = git(root, "diff", "--cached", "--name-status", "--no-renames", "-z").stdout
    parts = [p for p in out.split("\0") if p]
    return [(parts[i][0], parts[i + 1]) for i in range(0, len(parts) - 1, 2)]


def staged_text(root: Path, path: str) -> str:
    return git(root, "show", f":{path}").stdout


def head_text(root: Path, path: str) -> str:
    r = git(root, "show", f"HEAD:{path}")
    return r.stdout if r.returncode == 0 else ""


def under(path: str, prefix: str) -> bool:
    prefix = prefix.rstrip("/")
    return path == prefix or path.startswith(prefix + "/")


def name_of(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def table_rows(text: str, row_id: str, stop_at: str | None = None) -> dict[str, list[str]]:
    """Markdown table rows whose first cell matches row_id (e.g. 'D' -> D1, D2...)."""
    rows = {}
    for line in text.splitlines():
        if stop_at and line.startswith(stop_at):
            break
        m = re.match(rf"^\|\s*({row_id}\d+)\s*\|", line)
        if m:
            rows[m.group(1)] = [c.strip() for c in line.strip().strip("|").split("|")]
    return rows


def log_rows(text: str) -> int:
    """Data rows in an ADR's '## Decision log' table (header and separator excluded)."""
    _, _, tail = text.partition("## Decision log")
    rows = [ln for ln in tail.splitlines() if ln.startswith("|")]
    return max(0, len(rows) - 2)


# ---------------------------------------------------------------- staged checks

def check_secrets(root, meta, changes):
    for status, path in changes:
        if status != "D" and SECRETISH.search(path) and name_of(path) not in SECRET_ALLOWED:
            yield block("R-SECRETS", f"{path} looks like a secret. Unstage it (`git reset -q {path}`) "
                                     "and add it to .gitignore. If it was ever pushed: rotate it.")


def check_protected_paths(root, meta, changes):
    for status, path in changes:
        if status == "A":
            continue
        for prefix in meta.get("protected", []):
            if under(path, prefix):
                rule = "R-SOURCES" if under(prefix, SOURCES) else "R-EVIDENCE"
                yield block(rule, f"{path} is under write-once {prefix}/ and was "
                                  f"{'deleted' if status == 'D' else 'modified'}. Restore it "
                                  f"(`git restore --staged --worktree {path}`); derived work is a NEW file.")


def check_sources_logged(root, meta, changes):
    log = None
    for status, path in changes:
        if path == SOURCES_LOG and status == "M":
            numstat = git(root, "diff", "--cached", "--numstat", "--", path).stdout.split()
            if numstat and numstat[1] not in ("0", "-"):
                yield block("R-SOURCES", f"{SOURCES_LOG} is append-only; this commit removes lines from it.")
        if status == "A" and under(path, SOURCES) and name_of(path) not in STRUCTURAL:
            log = staged_text(root, SOURCES_LOG) if log is None else log
            rel = path[len(SOURCES) + 1:]
            if path not in log and rel not in log:
                yield block("R-SOURCES", f"{path} is not in {SOURCES_LOG}. Add a line: "
                                         f"`[date] -- [URL] -- {path} -- [description]`.")


def check_naming(root, meta, changes):
    for status, path in changes:
        if status != "A" or name_of(path) in STRUCTURAL:
            continue
        for rule in meta.get("naming", []):
            base = rule["under"].rstrip("/")
            if not path.startswith(base + "/"):
                continue
            first = path[len(base) + 1:].split("/", 1)[0]
            if not re.fullmatch(rule["pattern"], first):
                yield block("R-PLACE", f"{path}: '{first}' does not follow the naming rule for "
                                       f"{base}/ (e.g. {rule['example']}). Rename it with `git mv`.")


def check_decision_register(root, meta, changes):
    touched = {path for status, path in changes if status != "D"}
    if DECISIONS in touched:
        new, old = staged_text(root, DECISIONS), head_text(root, DECISIONS)
        new_rows = table_rows(new, "D")
        for rid, cells in new_rows.items():
            if len(cells) >= 4 and cells[2] and not (cells[1] and cells[3]):
                yield block("R-DECISIONS", f"{DECISIONS} {rid}: a decision needs its date and the strongest "
                                           "alternative with why it lost.")
        for rid, cells in table_rows(old, "D").items():
            if len(cells) >= 3 and cells[2] and new_rows.get(rid) != cells:
                yield block("R-DECISIONS", f"{DECISIONS} {rid} was changed or removed. Settled rows are never "
                                           "edited: add a new row that names it under 'Supersedes'.")
    if OPEN_ITEMS in touched:
        for rid, cells in table_rows(staged_text(root, OPEN_ITEMS), "O", stop_at="## Closed").items():
            if len(cells) >= 4 and cells[1] and not (cells[2] and cells[3]):
                yield block("R-DECISIONS", f"{OPEN_ITEMS} {rid}: an open item needs an owner and a trigger "
                                           "(an item without a trigger is a wish).")


def check_zone_placement(root, meta, changes):
    added = [path for status, path in changes if status == "A"]
    tracked = None
    for status, path in changes:
        if status == "D":
            continue
        name = name_of(path)
        zone = path.split("/", 1)[0] if path.split("/", 1)[0] in ZONES else None
        if DECISION_DOC.search(name) and name != "ADR-TEMPLATE.md" and zone not in ("30-decisions", "90-archive"):
            yield block("R-ZONES", f"{path} is a decision document outside 30-decisions/. If it is not "
                                   "settled yet it is research: 10-research/notes/.")
    for path in added:
        name, zone = name_of(path), path.split("/", 1)[0]
        if zone not in ZONES or name in STRUCTURAL:
            continue
        if tracked is None:
            tracked = git(root, "ls-files", "-z").stdout.split("\0")
        dups = [t for t in tracked if t and t != path and name_of(t) == name
                and t.split("/", 1)[0] in ZONES and t.split("/", 1)[0] != zone]
        if dups:
            yield block("R-ZONES", f"{path} duplicates {dups[0]}. A document lives in one zone: "
                                   "move it with `git mv`, never copy.")


def check_adr_format(root, meta, changes):
    for status, path in changes:
        name = name_of(path)
        if status == "D" or not under(path, "30-decisions") or not ADR_FILE.match(name) \
                or name == "ADR-TEMPLATE.md":
            continue
        text = staged_text(root, path)
        missing = [s for s in ADR_SECTIONS if not re.search(rf"^{re.escape(s)}\b", text, re.M)]
        if missing:
            yield block("R-ADR", f"{path} is missing: {', '.join(missing)}. Start from ADR-TEMPLATE.md.")
        elif status == "M" and log_rows(text) <= log_rows(head_text(root, path)):
            yield warn("R-ADR", f"{path} changed without a new decision-log row. If the decision moved, "
                                "add one (date, change, previous position, reason).")


def check_english(root, meta, changes):
    hits = []
    for status, path in changes:
        if status == "D" or under(path, SOURCES) or Path(path).suffix not in TEXT_EXT:
            continue
        diff = git(root, "diff", "--cached", "-U0", "--", path).stdout
        if any(ln.startswith("+") and not ln.startswith("+++") and NON_ENGLISH.search(ln)
               for ln in diff.splitlines()):
            hits.append(path)
    if hits:
        yield warn("R-LANG", "documents, code and commits are English; non-English text added in: "
                             + ", ".join(hits) + ". Quotes from sources are fine.")


STAGED_CHECKS = {
    "secrets": check_secrets,
    "protected_paths": check_protected_paths,
    "sources_logged": check_sources_logged,
    "naming": check_naming,
    "decision_register": check_decision_register,
    "zone_placement": check_zone_placement,
    "adr_format": check_adr_format,
    "english": check_english,
}


def staged_findings(root: Path = ROOT) -> list[Finding]:
    meta = load_meta(root)
    enabled = meta.get("checks", [])
    changes = staged_changes(root)
    found = []
    for name, check in STAGED_CHECKS.items():
        if name in enabled:
            found += list(check(root, meta, changes))
    return found


# ---------------------------------------------------------------- commit message

def message_findings(message: str, root: Path = ROOT) -> list[Finding]:
    enabled = load_meta(root).get("checks", [])
    lines = [ln for ln in message.splitlines() if not ln.startswith("#")]
    subject = lines[0].strip() if lines else ""
    body = "\n".join(lines[1:]).strip()
    found = []
    if EXEMPT_MSG.match(subject):
        return found
    if "commit_msg" in enabled and not CONVENTIONAL.match(subject):
        found.append(block("R-COMMIT", f"subject {subject!r} is not a Conventional Commit. "
                                       "Use `type: what changed` (feat, fix, docs, chore, refactor, test, ...)."))
    if "decision_commit_body" in enabled and not body \
            and any(under(p, "30-decisions") for _, p in staged_changes(root)):
        found.append(block("R-DECISIONS", "this commit changes 30-decisions/; the body must say why "
                                          "(it is the record of why a decision moved)."))
    return found


# ---------------------------------------------------------------- Claude write hooks

def write_verdict(root: Path, check: str, rel: str, exists: bool) -> tuple[int, str]:
    """Verdict on a single file write about to happen: (exit code, message)."""
    meta = load_meta(root)
    if check == "protected_paths":
        for prefix in meta.get("protected", []):
            if not under(rel, prefix):
                continue
            if not exists:
                return 0, f"NOTE: creating {rel} under protected {prefix}/ -- it becomes read-only once written."
            rule = "R-SOURCES" if under(prefix, SOURCES) else "R-EVIDENCE"
            return 2, (f"BLOCKED [{rule}] {rel}: {prefix}/ is write-once; existing files there are evidence.\n"
                       "  Derived work goes to 10-research/notes/; a re-run or new version is a NEW file or folder.")
    if check == "zone_placement":
        name = name_of(rel)
        head = rel.split("/", 1)[0]
        zone = head if head in ZONES else None
        if DECISION_DOC.search(name) and name != "ADR-TEMPLATE.md" and zone not in ("30-decisions", "90-archive"):
            return 2, (f"BLOCKED [R-ZONES] {rel}: decision documents live in 30-decisions/. If it is not "
                       "settled yet, it is research -- 10-research/notes/.")
        if zone and not exists and name not in STRUCTURAL:
            for other in ZONES:
                if other == zone or not (root / other).is_dir():
                    continue
                for dup in (root / other).rglob(name):
                    if dup.is_file():
                        return 2, (f"BLOCKED [R-ZONES] {rel}: '{name}' already exists at "
                                   f"{dup.relative_to(root).as_posix()}. Move it with `git mv`; never copy.")
        if zone == "30-decisions" and exists:
            return 0, (f"NOTE: editing {rel} -- the settled zone. If the decision moves, add a decision-log "
                       "row (ADR) or a superseding row (DECISIONS.md), and say why in the commit body.")
    return 0, ""


def hook_main(check: str) -> int:
    """Entry point for a Claude Code PreToolUse hook. Never breaks the session."""
    import os
    safe_stderr()
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    tool_input = payload.get("tool_input", {}) or {}
    raw = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not raw:
        return 0
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ".").resolve()
    try:
        rel = Path(raw).resolve().relative_to(root).as_posix()
    except ValueError:
        return 0  # outside the workspace
    code, msg = write_verdict(root, check, rel, Path(raw).exists())
    if msg:
        print(msg, file=sys.stderr)
    return code


# ---------------------------------------------------------------- CLI

def report(found: list[Finding], where: str) -> int:
    for f in found:
        print(f"{where}: {f}", file=sys.stderr)
    if any(f.level == "block" for f in found):
        print(f"{where}: commit refused. Rule text: AGENTS.md (search for the rule ID).", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str]) -> int:
    safe_stderr()
    if argv[:1] == ["pre-commit"]:
        return report(staged_findings(), "pre-commit")
    if argv[:1] == ["commit-msg"] and len(argv) == 2:
        return report(message_findings(Path(argv[1]).read_text(encoding="utf-8", errors="replace")),
                      "commit-msg")
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
