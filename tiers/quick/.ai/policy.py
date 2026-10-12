#!/usr/bin/env python3
"""WorkRealm policy core -- every machine-checked rule lives here, once.

Prose rules are followed some of the time; checks bind. Every caller shares this
file, so a rule cannot drift between layers:

    git pre-commit   python .ai/policy.py pre-commit       (binds every tool and human)
    git commit-msg   python .ai/policy.py commit-msg FILE
    Claude hooks     .ai/hooks/*.py call hook_main() / bash_hook_main()
    checkpoint.py    calls staged_findings()

Everything workspace-specific is data in .workrealm.json: which checks run ("checks"),
where things live ("layout"), what is write-once ("protected"), naming ("naming"),
and which folders a document may not be copied between ("zones"). Rule IDs (R-...)
point at the rule text in AGENTS.md; the text is not repeated here.

Exit codes: 0 = pass (warnings may print), 1 = blocked.
"""
from __future__ import annotations

import fnmatch
import json
import os
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
    "R-STATE": {"claude": ["session_start.py"]},
    "R-COMMIT": {"git": ["commit_msg"], "claude": ["checkpoint_gate.py", "bash_guard.py"]},
    "R-SECRETS": {"git": ["secrets"]},
    "R-PLACE": {"git": ["naming"]},
    "R-SOURCES": {"git": ["protected_paths", "sources_logged"], "claude": ["protect_paths.py", "bash_guard.py"]},
    "R-DECISIONS": {"git": ["decision_register", "decision_commit_body"]},
    "R-ZONES": {"git": ["zone_placement"], "claude": ["zone_guard.py"]},
    "R-EVIDENCE": {"git": ["protected_paths"], "claude": ["protect_paths.py", "bash_guard.py"]},
    "R-INBOX": {"claude": ["protect_paths.py", "bash_guard.py"]},
    "R-ADR": {"git": ["adr_format"]},
}

# Defaults for a workspace whose .workrealm.json predates "layout"; wr.py writes the real one.
DEFAULT_LAYOUT = {
    "notes": "docs/notes", "decisions": "docs/decisions", "adr": "docs/decisions/adr",
    "plans": "docs/plans", "sources": "references", "sources_log": "references/SOURCES_LOG.md",
    "inbox": "references/inbox", "data_raw": "data/raw", "experiments": "experiments",
    "reports": "reports", "releases": "releases", "archive": "archive",
}

SECRETISH = re.compile(r"(^|/)(\.env(\..+)?|.*\.pem|.*\.key|id_rsa[^/]*|credentials\.json)$", re.I)
SECRET_ALLOWED = {".env.example"}
STRUCTURAL = {
    "README.md", "AGENTS.md", "CLAUDE.md", "GEMINI.md", "INDEX.md", "MANIFEST.md", "SUMMARY.md",
    "STATE.md", "TEMPLATE.md", "__init__.py", "conftest.py", ".gitkeep", ".gitignore",
}
DECISION_DOC = re.compile(r"^(DECISIONS|OPEN-ITEMS|CONSTRAINTS)\.md$|^ADR-\d+", re.I)
ADR_FILE = re.compile(r"^\d{4}-.+\.md$")
ADR_SECTIONS = ("## Decision", "## Alternatives", "## What would change my mind",
                "## Cost of reversal", "## Decision log")
CONVENTIONAL = re.compile(
    r"^(feat|fix|docs|chore|refactor|test|perf|build|ci|style|revert)(\([\w./-]+\))?!?: \S")
EXEMPT_MSG = re.compile(r"^(Merge |Revert \"|fixup! |squash! |amend! )")
AI_TAG = "\U0001F916 [AI]"  # robot face: marks a commit whose work a subagent did
AI_TRAILER = re.compile(r"^AI-Agent:\s*\S+", re.M)
NON_ENGLISH = re.compile("[\u010d\u0107\u017e\u0161\u0111\u010c\u0106\u017d\u0160\u0110]")  # Croatian letters
TEXT_EXT = {".md", ".txt", ".py", ".ps1", ".sh", ".json", ".yaml", ".yml", ".toml", ".js", ".ts"}


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


def layout(meta: dict) -> dict:
    return {**DEFAULT_LAYOUT, **meta.get("layout", {})}


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


def under(path: str, pattern: str) -> bool:
    """path is pattern or below it. Pattern segments may use * and ? (experiments/*/results)."""
    want = pattern.strip("/").split("/")
    have = path.strip("/").split("/")
    return len(have) >= len(want) and all(fnmatch.fnmatchcase(h, w) for h, w in zip(have, want))


def below(path: str, pattern: str) -> str | None:
    """The first path segment below pattern, or None if path is not strictly below it."""
    want = pattern.strip("/").split("/")
    have = path.strip("/").split("/")
    if len(have) > len(want) and all(fnmatch.fnmatchcase(h, w) for h, w in zip(have, want)):
        return have[len(want)]
    return None


def protected_by(meta: dict, path: str) -> str | None:
    """The write-once pattern covering path, unless a '!pattern' exclusion carves it out.
    A folder's README.md and the sources log are append-to documents, never evidence."""
    if name_of(path) == "README.md" or path == layout(meta)["sources_log"]:
        return None
    rules = meta.get("protected", [])
    if any(r.startswith("!") and under(path, r[1:]) for r in rules):
        return None
    return next((r for r in rules if not r.startswith("!") and under(path, r)), None)


def evidence_rule(meta: dict, pattern: str) -> str:
    return "R-SOURCES" if under(pattern, layout(meta)["sources"]) else "R-EVIDENCE"


def zone_of(meta: dict, path: str) -> str | None:
    zones = [z for z in meta.get("zones", []) if under(path, z)]
    return max(zones, key=len) if zones else None


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


def decision_homes(meta: dict) -> list[str]:
    lay = layout(meta)
    return [lay["decisions"], lay["archive"]] + meta.get("snapshots", [])


# ---------------------------------------------------------------- staged checks

def check_secrets(root, meta, changes):
    for status, path in changes:
        if status != "D" and SECRETISH.search(path) and name_of(path) not in SECRET_ALLOWED:
            yield block("R-SECRETS", f"{path} looks like a secret. Unstage it (`git reset -q {path}`) "
                                     "and add it to .gitignore. If it was ever pushed: rotate it.")


def check_protected_paths(root, meta, changes):
    for status, path in changes:
        pattern = protected_by(meta, path) if status != "A" else None
        if pattern:
            yield block(evidence_rule(meta, pattern),
                        f"{path} is under write-once {pattern}/ and was "
                        f"{'deleted' if status == 'D' else 'modified'}. Restore it "
                        f"(`git restore --staged --worktree {path}`); derived work is a NEW file.")


def check_sources_logged(root, meta, changes):
    lay = layout(meta)
    sources, log_path = lay["sources"], lay["sources_log"]
    log = None
    for status, path in changes:
        if path == log_path and status == "M":
            numstat = git(root, "diff", "--cached", "--numstat", "--", path).stdout.split()
            if numstat and numstat[1] not in ("0", "-"):
                yield block("R-SOURCES", f"{log_path} is append-only; this commit removes lines from it.")
        if status != "A" or path == log_path or name_of(path) in STRUCTURAL \
                or not under(path, sources) or protected_by(meta, path) is None:
            continue  # only evidence needs a log line; the inbox does not
        log = staged_text(root, log_path) if log is None else log
        rel = path[len(sources.rstrip("/")) + 1:]
        if path not in log and rel not in log:
            yield block("R-SOURCES", f"{path} is not in {log_path}. Add a line: "
                                     f"`[date] -- [URL] -- {path} -- [description]` "
                                     "(python .ai/wr.py source add/promote does it for you).")


def check_naming(root, meta, changes):
    for status, path in changes:
        if status != "A" or name_of(path) in STRUCTURAL:
            continue
        for rule in meta.get("naming", []):
            first = below(path, rule["under"])
            if first is not None and first not in STRUCTURAL and not re.fullmatch(rule["pattern"], first):
                yield block("R-PLACE", f"{path}: '{first}' does not follow the naming rule for "
                                       f"{rule['under']}/ (e.g. {rule['example']}). Rename it with `git mv`.")


def check_decision_register(root, meta, changes):
    lay = layout(meta)
    decisions = f"{lay['decisions']}/DECISIONS.md"
    open_items = f"{lay['decisions']}/OPEN-ITEMS.md"
    touched = {path for status, path in changes if status != "D"}
    if decisions in touched:
        new, old = staged_text(root, decisions), head_text(root, decisions)
        new_rows = table_rows(new, "D")
        for rid, cells in new_rows.items():
            if len(cells) >= 4 and cells[2] and not (cells[1] and cells[3]):
                yield block("R-DECISIONS", f"{decisions} {rid}: a decision needs its date and the strongest "
                                           "alternative with why it lost.")
        for rid, cells in table_rows(old, "D").items():
            if len(cells) >= 3 and cells[2] and new_rows.get(rid) != cells:
                yield block("R-DECISIONS", f"{decisions} {rid} was changed or removed. Settled rows are never "
                                           "edited: add a new row that names it under 'Supersedes'.")
    if open_items in touched:
        for rid, cells in table_rows(staged_text(root, open_items), "O", stop_at="## Closed").items():
            if len(cells) >= 4 and cells[1] and not (cells[2] and cells[3]):
                yield block("R-DECISIONS", f"{open_items} {rid}: an open item needs an owner and a trigger "
                                           "(an item without a trigger is a wish).")


def check_zone_placement(root, meta, changes):
    lay = layout(meta)
    homes = decision_homes(meta)
    snapshots = meta.get("snapshots", [])
    tracked = None
    for status, path in changes:
        if status == "D":
            continue
        if DECISION_DOC.search(name_of(path)) and not any(under(path, h) for h in homes):
            yield block("R-ZONES", f"{path} is a decision document outside {lay['decisions']}/. If it is "
                                   f"not settled yet it is a note: {lay['notes']}/.")
    for status, path in changes:
        zone = zone_of(meta, path) if status == "A" else None
        if not zone or name_of(path) in STRUCTURAL or any(under(path, s) for s in snapshots):
            continue
        if tracked is None:
            tracked = [t for t in git(root, "ls-files", "-z").stdout.split("\0") if t]
        dups = [t for t in tracked if t != path and name_of(t) == name_of(path)
                and zone_of(meta, t) not in (None, zone) and not any(under(t, s) for s in snapshots)]
        if dups:
            yield block("R-ZONES", f"{path} duplicates {dups[0]}. A document lives in one place: "
                                   "move it with `git mv`, never copy.")


def check_adr_format(root, meta, changes):
    adr_dir = layout(meta)["adr"]
    for status, path in changes:
        if status == "D" or below(path, adr_dir) != name_of(path) or not ADR_FILE.match(name_of(path)):
            continue
        text = staged_text(root, path)
        missing = [s for s in ADR_SECTIONS if not re.search(rf"^{re.escape(s)}\b", text, re.M)]
        if missing:
            yield block("R-ADR", f"{path} is missing: {', '.join(missing)}. Start from {adr_dir}/TEMPLATE.md "
                                 "(python .ai/wr.py adr new does).")
        elif status == "M" and log_rows(text) <= log_rows(head_text(root, path)):
            yield warn("R-ADR", f"{path} changed without a new decision-log row. If the decision moved, "
                                "add one (date, change, previous position, reason).")


def check_english(root, meta, changes):
    lay = layout(meta)
    skip = [lay["sources"], lay["data_raw"]]
    hits = []
    for status, path in changes:
        if status == "D" or any(under(path, s) for s in skip) or Path(path).suffix not in TEXT_EXT:
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
    meta = load_meta(root)
    enabled = meta.get("checks", [])
    lines = [ln for ln in message.splitlines() if not ln.startswith("#")]
    subject = lines[0].strip() if lines else ""
    body = "\n".join(lines[1:]).strip()
    found = []
    if EXEMPT_MSG.match(subject):
        return found
    if "commit_msg" in enabled:
        if not CONVENTIONAL.match(subject):
            found.append(block("R-COMMIT", f"subject {subject!r} is not a Conventional Commit. "
                                           "Use `type: what changed` (feat, fix, docs, chore, refactor, test, ...)."))
        if (AI_TAG in subject) != bool(AI_TRAILER.search(body)):
            found.append(block("R-COMMIT", f"the {AI_TAG} tag and the `AI-Agent:` trailer go together, and only "
                                           "on commits a subagent made. Use python .ai/checkpoint.py."))
    decisions = layout(meta)["decisions"]
    body_text = AI_TRAILER.sub("", body).strip()
    if "decision_commit_body" in enabled and not body_text \
            and any(under(p, decisions) for _, p in staged_changes(root)):
        found.append(block("R-DECISIONS", f"this commit changes {decisions}/; the body must say why "
                                          "(it is the record of why a decision moved)."))
    return found


# ---------------------------------------------------------------- Claude write hooks

def write_verdict(root: Path, check: str, rel: str, exists: bool) -> tuple[int, str]:
    """Verdict on a single file write about to happen: (exit code, message)."""
    meta = load_meta(root)
    lay = layout(meta)
    if check == "protected_paths":
        pattern = protected_by(meta, rel)
        if pattern and exists:
            return 2, (f"BLOCKED [{evidence_rule(meta, pattern)}] {rel}: {pattern}/ is write-once; existing "
                       f"files there are evidence.\n  Derived work goes to {lay['notes']}/; a re-run or new "
                       "version is a NEW file or folder.")
        if pattern and "inbox" in meta.get("checks", []) and under(pattern, lay["sources"]):
            return 2, (f"BLOCKED [R-INBOX] {rel}: new material goes to {lay['inbox']}/ first "
                       "(python .ai/wr.py source add ...). Promotion into evidence is the owner's call: "
                       "python .ai/wr.py source promote <file>.")
        if pattern:
            return 0, f"NOTE: creating {rel} under protected {pattern}/ -- it becomes read-only once written."
    if check == "zone_placement":
        name = name_of(rel)
        if DECISION_DOC.search(name) and not any(under(rel, h) for h in decision_homes(meta)):
            return 2, (f"BLOCKED [R-ZONES] {rel}: decision documents live in {lay['decisions']}/. If it is "
                       f"not settled yet, it is a note -- {lay['notes']}/.")
        zone = zone_of(meta, rel)
        snapshots = meta.get("snapshots", [])
        if zone and not exists and name not in STRUCTURAL and not any(under(rel, s) for s in snapshots):
            for other in meta.get("zones", []):
                if other == zone or under(other, zone) or under(zone, other) or "*" in other \
                        or not (root / other).is_dir():
                    continue
                for dup in (root / other).rglob(name):
                    dup_rel = dup.relative_to(root).as_posix()
                    if dup.is_file() and zone_of(meta, dup_rel) == other \
                            and not any(under(dup_rel, s) for s in snapshots):
                        return 2, (f"BLOCKED [R-ZONES] {rel}: '{name}' already exists at {dup_rel}. "
                                   "Move it with `git mv`; never copy.")
        if under(rel, lay["decisions"]) and exists:
            return 0, (f"NOTE: editing {rel} -- settled decisions. If a decision moves, add a decision-log "
                       "row (ADR) or a superseding row (DECISIONS.md), and say why in the commit body.")
    return 0, ""


SEPARATORS = re.compile(r"&&|\|\||[;|&\n]")
REDIRECT = re.compile(r"(?<![<\d&])\d?>>?\s*([^\s;|&<>]+)")
DESTRUCTIVE = {
    "rm", "rmdir", "mv", "tee", "truncate", "shred", "unlink", "del", "erase", "ren", "move",
    "remove-item", "move-item", "rename-item", "set-content", "add-content", "out-file", "clear-content",
    "ri", "mi", "rni", "sc", "ac", "clc",
}
CREATING = {"cp", "copy", "mv", "move", "curl", "wget", "tee", "copy-item", "cpi", "move-item", "mi",
            "invoke-webrequest", "iwr", "out-file", "set-content"}
NO_VERIFY = re.compile(r"\bgit\b[^;&|\n]*\s(commit|merge|push|rebase|am|cherry-pick)\b[^;&|\n]*\s--no-verify\b")
COMMIT_N = re.compile(r"\bgit\b[^;&|\n]*\scommit\b[^;&|\n]*\s-[a-zA-Z]*n[a-zA-Z]*\b")
GIT_COMMIT = re.compile(r"\bgit\b[^;&|\n]*\scommit\b")
CHECKPOINT = re.compile(r"(\.ai[/\\]checkpoint\.py|\.ai[/\\]wr\.py\s+checkpoint)\b")
ONLY_CHECKPOINT = re.compile(
    r"""^\s*(python3?|py)\s+\S*(\.ai[/\\]checkpoint\.py|\.ai[/\\]wr\.py\s+checkpoint)"""
    r"""((\s+("[^"]*"|'[^']*'|[^\s"';&|<>`$]+))*)\s*$""")


def _clean(token: str) -> str:
    return token.strip("\"'`()").replace("\\", "/")


def _rel(root: Path, token: str) -> tuple[str, Path] | None:
    token = _clean(token)
    if not token or token.startswith("-") or "://" in token:
        return None
    try:
        path = (root / token).resolve()
        return path.relative_to(root).as_posix(), path
    except (ValueError, OSError):
        return None


def _destroys(meta: dict, root: Path, token: str) -> tuple[str, str] | None:
    """(rel, pattern) if token names an EXISTING write-once path."""
    hit = _rel(root, token)
    if not hit:
        return None
    rel, path = hit
    pattern = protected_by(meta, rel)
    if not pattern or not path.exists():
        return None
    if path.is_dir() and not any(path.iterdir()):
        return None
    return rel, pattern


def _bypasses_inbox(meta: dict, root: Path, token: str) -> str | None:
    hit = _rel(root, token)
    if not hit:
        return None
    rel, _ = hit
    pattern = protected_by(meta, rel)
    if pattern and under(pattern, layout(meta)["sources"]) and rel != pattern.rstrip("/"):
        return rel
    return None


def bash_verdict(root: Path, command: str, agent: str | None = None) -> tuple[int, str, str | None]:
    """Verdict on a shell command about to run: (exit code, message, rewritten command or None).
    Heuristic, so it only blocks clear cases; the pre-commit check catches the rest at commit time.
    `agent` is the subagent type when a subagent runs the command, None for the main agent."""
    if NO_VERIFY.search(command) or COMMIT_N.search(command):
        return 2, ("BLOCKED [R-COMMIT] --no-verify skips the checks that bind every tool. Fix what the "
                   "check refuses instead; if the check itself is wrong, say so to the user."), None
    if "core.hookspath" in command.lower() and ".githooks" not in command:
        return 2, "BLOCKED [R-COMMIT] core.hooksPath must stay .githooks; it is what runs the checks.", None
    rewritten = None
    if CHECKPOINT.search(command):
        if agent is None and re.search(r"\s--agent\b", command):
            return 2, ("BLOCKED [R-COMMIT] --agent marks work a subagent did on its own. Work done at the "
                       "user's prompt is committed unmarked."), None
        if agent is not None and not re.search(r"\s--agent\b", command):
            m = CHECKPOINT.search(command)
            if not ONLY_CHECKPOINT.match(command):
                return 2, ("BLOCKED [R-COMMIT] run the checkpoint as a command of its own, so it can be "
                           "marked as your work: python .ai/checkpoint.py \"type: what\" \"why\""), None
            rewritten = f"{command[:m.end()]} --agent {agent}{command[m.end():]}"
    elif agent is not None and GIT_COMMIT.search(command):
        return 2, ("BLOCKED [R-COMMIT] subagents commit with python .ai/checkpoint.py \"type: what\" \"why\"; "
                   "it runs the checks and marks the commit as a subagent's work."), None

    meta = load_meta(root)
    if not meta.get("protected"):
        return 0, "", rewritten
    inbox = "inbox" in meta.get("checks", [])
    hits, bypass = [], []
    for m in REDIRECT.finditer(command):
        target = m.group(1)
        hits += [h for h in [_destroys(meta, root, target)] if h]
        if inbox:
            bypass += [b for b in [_bypasses_inbox(meta, root, target)] if b]
    for part in SEPARATORS.split(command):
        words = part.split()
        while words and re.fullmatch(r"\w+=\S*", words[0]):  # leading VAR=value
            words = words[1:]
        if not words:
            continue
        verb, args = words[0].lower(), words[1:]
        if verb == "git" and args[:1] and args[0] in ("rm", "mv"):
            verb, args = args[0], args[1:]
        elif verb == "sed" and any(a.startswith("-i") or a == "--in-place" for a in args):
            verb = "rm"  # in-place edit counts as destructive
        if verb in DESTRUCTIVE:
            hits += [h for h in (_destroys(meta, root, a) for a in args) if h]
        if inbox and verb in CREATING:
            bypass += [b for b in (_bypasses_inbox(meta, root, a) for a in args) if b]
    if hits:
        rel, pattern = hits[0]
        return 2, (f"BLOCKED [{evidence_rule(meta, pattern)}] this command would change or remove {rel}; "
                   f"{pattern}/ is write-once.\n  Derived work goes to {layout(meta)['notes']}/; a re-run or "
                   "new version is a NEW file or folder."), None
    if bypass:
        lay = layout(meta)
        return 2, (f"BLOCKED [R-INBOX] this command would put {bypass[0]} straight into evidence. New "
                   f"material goes to {lay['inbox']}/ (python .ai/wr.py source add ...); promoting it is the "
                   "owner's call (python .ai/wr.py source promote <file>)."), None
    return 0, "", rewritten


def bash_hook_main() -> int:
    """Entry point for the Claude Code PreToolUse hook on Bash / PowerShell."""
    safe_stderr()
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    tool_input = payload.get("tool_input", {}) or {}
    command = tool_input.get("command") or ""
    if not command:
        return 0
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ".").resolve()
    agent = (payload.get("agent_type") or "subagent") if payload.get("agent_id") else None
    code, msg, rewritten = bash_verdict(root, command, re.sub(r"[^\w.-]", "-", agent) if agent else None)
    if msg:
        print(msg, file=sys.stderr)
    if rewritten and code == 0:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": f"WorkRealm: commit marked as the work of subagent '{agent}'",
            "updatedInput": {**tool_input, "command": rewritten},
        }}))
    return code


def hook_main(check: str) -> int:
    """Entry point for a Claude Code PreToolUse write hook. Never breaks the session."""
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
