#!/usr/bin/env python3
"""Workspace helpers -- the right way to do a thing in one command, from any tool.

    python .ai/wr.py status                      where things stand (also shown at session start)
    python .ai/wr.py init [--name NAME]          set up a fresh clone (hooks; a template's name and date)
    python .ai/wr.py checkpoint "type: msg" [body]
    python .ai/wr.py handoff                     before ending a session
    python .ai/wr.py ticket start KEY [TITLE] [--type fix]   a branch named after the ticket
    python .ai/wr.py names [PATH ...] [--fix] [--style] [--rewrite-refs] [--keep GLOB]
                                                 names that break R-NAMES; --fix renames them (git mv)
    python .ai/wr.py note TOPIC                  task+    a dated note in docs/notes/
    python .ai/wr.py source add URL --desc D [--file LOCAL] [--name NAME]
                                                 task+    save + log (project: into the inbox)
    python .ai/wr.py source promote FILE --desc D   project  inbox -> evidence (asks the user)
    python .ai/wr.py decide TEXT --alt "OPTION -- why it lost" [--supersedes D1] [--detail REF]
    python .ai/wr.py open-item QUESTION --owner WHO --trigger WHEN
    python .ai/wr.py close-item O3 ANSWER
    python .ai/wr.py plan new TOPIC              project  docs/plans/<topic>.md
    python .ai/wr.py adr new TITLE               project  docs/decisions/adr/NNNN-<title>.md
    python .ai/wr.py exp new TOPIC               project  experiments/<date>-<topic>/
    python .ai/wr.py run new EXPERIMENT          project  experiments/<exp>/results/<date>[-NN]/
    python .ai/wr.py release cut VERSION --include PATH [PATH ...]   project

Each helper produces what the checks in policy.py accept: correct names, complete rows,
logged sources. Paths come from "layout" in .workrealm.json. Rule text lives in AGENTS.md;
this file only does the mechanics.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from policy import (TEXT_EXT, TICKET_KEY, active_ticket, layout, name_problem, protected_by,  # noqa: E402
                    safe_name, to_ascii)

ROOT = Path(__file__).resolve().parent.parent
TIERS = ("quick", "task", "project")
STATE_LINES = 80


# ---------------------------------------------------------------- plumbing

def die(msg: str) -> None:
    print(f"wr: {msg}", file=sys.stderr)
    sys.exit(1)


def meta() -> dict:
    try:
        return json.loads((ROOT / ".workrealm.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def path_of(key: str) -> Path:
    return ROOT / layout(meta())[key]


def tier() -> str:
    return meta().get("tier", "quick")


def need(want: str) -> None:
    if TIERS.index(tier()) < TIERS.index(want):
        die(f"this needs the {want} tier (workspace is {tier()}). Upgrade with the generator: "
            f"wr upgrade --to {want}")


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-c", "core.quotepath=off", *args], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def today() -> str:
    return dt.date.today().isoformat()


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", to_ascii(text).lower()).strip("-")
    if not s:
        die(f"cannot make a file name from {text!r}; use letters or digits")
    return s[:60].rstrip("-")


def intake_name(name: str) -> str:
    """A received file's name made standard (R-NAMES): ASCII, lowercase kebab-case, lowercase
    extension. `Izvjesce o stanju 2024.PDF` -> `izvjesce-o-stanju-2024.pdf`."""
    stem, dot, ext = name.rpartition(".") if "." in name.lstrip(".") else (name, "", "")
    stem = re.sub(r"-*\.-*", ".", re.sub(r"[^a-z0-9.]+", "-", to_ascii(stem).lower())).strip("-.")
    ext = re.sub(r"[^a-z0-9]", "", to_ascii(ext).lower())
    return (stem or "download") + (f".{ext}" if ext else "")


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def create(path: Path, text: str) -> None:
    if path.exists():
        die(f"{rel(path)} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"created {rel(path)}")


def cell(text: str) -> str:
    return text.replace("|", "/").replace("\n", " ").strip()


def append_row(path: Path, row: str, before: str | None = None) -> None:
    """Append a table row after the last row of the first table (or of the table before `before`)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    end = len(lines)
    if before:
        end = next((i for i, ln in enumerate(lines) if ln.startswith(before)), len(lines))
    last = max((i for i, ln in enumerate(lines[:end]) if ln.startswith("|")), default=None)
    if last is None:
        die(f"no table found in {rel(path)}")
    lines.insert(last + 1, row)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def next_id(text: str, prefix: str) -> int:
    nums = [int(n) for n in re.findall(rf"^\|\s*{prefix}(\d+)\s*\|", text, re.M)]
    return max(nums, default=0) + 1


def empty_row(text: str, rid: str) -> bool:
    m = re.search(rf"^\|\s*{rid}\s*\|(.*)$", text, re.M)
    return bool(m) and all(c.strip() in ("", "—", "-") for c in m.group(1).strip().strip("|").split("|"))


def log_source(target: Path, url: str, desc: str) -> None:
    log = path_of("sources_log")
    lead = "" if log.read_text(encoding="utf-8").endswith("\n") else "\n"  # never rewrite the last line
    with open(log, "a", encoding="utf-8", newline="\n") as f:
        f.write(f"{lead}{today()} — {url} — {rel(target)} — {cell(desc)}\n")


# ---------------------------------------------------------------- status

def open_items() -> int | None:
    path = path_of("decisions") / "OPEN-ITEMS.md"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").split("## Closed", 1)[0]
    return sum(1 for m in re.finditer(r"^\|\s*O\d+\s*\|([^|]*)\|", text, re.M) if m.group(1).strip())


def inbox_count() -> int | None:
    inbox = path_of("inbox")
    if tier() != "project" or not inbox.is_dir():
        return None
    return sum(1 for p in inbox.iterdir() if p.is_file() and p.name not in ("README.md", ".gitkeep")
               and p.suffix != ".source")


def git_summary() -> dict:
    branch = git("symbolic-ref", "--short", "-q", "HEAD").stdout.strip() or "(detached)"
    dirty = len([ln for ln in git("status", "--porcelain").stdout.splitlines() if ln.strip()])
    remote = git("remote", "get-url", "origin").returncode == 0
    unpushed = None
    if remote:
        r = git("rev-list", "--count", "@{upstream}..HEAD")
        unpushed = int(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip().isdigit() else None
    return {"branch": branch, "dirty": dirty, "remote": remote, "unpushed": unpushed}


def push_failure() -> str | None:
    """What the post-commit hook kept from its last push, if that push failed."""
    git_dir = git("rev-parse", "--absolute-git-dir").stdout.strip()
    try:
        return (Path(git_dir) / "workrealm-push.log").read_text(encoding="utf-8", errors="replace").strip() or None
    except OSError:
        return None


def phase() -> str | None:
    try:
        m = re.search(r"\*\*Phase:\*\*\s*([^\n·]+)", (ROOT / "STATE.md").read_text(encoding="utf-8"))
    except OSError:
        return None
    value = m.group(1).strip() if m else ""
    return value if value and not value.startswith("_") else None


def status_text() -> str:
    m, g = meta(), git_summary()
    pushed = ("no remote" if not g["remote"] else
              "upstream not set" if g["unpushed"] is None else f"{g['unpushed']} unpushed")
    lines = [f"WorkRealm workspace '{m.get('name', ROOT.name)}' -- tier {m.get('tier', '?')}, "
             f"WorkRealm {m.get('workrealm_version', '?')}",
             f"Git: {g['branch']}, {g['dirty']} uncommitted, {pushed}"]
    failed = push_failure()
    if failed:
        lines.append("LAST PUSH FAILED -- these commits exist on this disk only. Fix the cause, then "
                     "`git push`:\n  " + "\n  ".join(failed.splitlines()[:6]))
    if from_template(m):
        lines.append(f"Made from the template '{m['name']}': python .ai/wr.py init names it '{ROOT.name}' "
                     "and turns the git hooks on")
    elif not hooks_path():
        lines.append("Git hooks are OFF in this clone, so commits are not checked: python .ai/wr.py init")
    ticket = active_ticket(ROOT, m)
    if ticket:
        lines.append(f"Ticket: {ticket} (commits end with `Refs: {ticket}`; checkpoint adds it)")
    if m.get("integrations"):
        lines.append(f"Integrations (.mcp.json): {', '.join(m['integrations'])}")
    items = open_items()
    if items is not None:
        lines.append(f"Open items: {items} ({layout(m)['decisions']}/OPEN-ITEMS.md)")
    waiting = inbox_count()
    if waiting:
        lines.append(f"Inbox: {waiting} source(s) waiting for the owner to promote or delete "
                     f"({layout(m)['inbox']}/)")
    lines.append("Helpers: python .ai/wr.py --help (note, source add, decide, adr new, exp new, ...)")
    state = ROOT / "STATE.md"
    if state.exists():
        body = state.read_text(encoding="utf-8").splitlines()
        lines += ["", "--- STATE.md ---"] + body[:STATE_LINES]
        if len(body) > STATE_LINES:
            lines.append(f"... {len(body) - STATE_LINES} more lines. STATE.md is meant to be short: "
                         "summarise it, move detail into notes, plans or decisions.")
    return "\n".join(lines)


def cmd_status(args) -> None:
    print(status_text())


def cmd_checkpoint(args) -> None:
    extra = (["--agent", args.agent] if args.agent else []) + [args.subject] + ([args.body] if args.body else [])
    r = subprocess.run([sys.executable, str(ROOT / ".ai" / "checkpoint.py"), *extra], cwd=ROOT)
    sys.exit(r.returncode)


def cmd_handoff(args) -> None:
    print(status_text())
    print("\nBefore ending the session:\n"
          "  1. STATE.md: what was done, the next concrete step, anything blocking or waiting on the owner.\n"
          "  2. Anything unresolved that someone must answer -> python .ai/wr.py open-item ...\n"
          '  3. python .ai/checkpoint.py "docs: update STATE for handoff"  (the tree must be clean)')


def hooks_path() -> str:
    return git("config", "core.hooksPath").stdout.strip()


def from_template(m: dict) -> bool:
    """Made with GitHub's "Use this template" and still carrying the template's name."""
    return bool(m.get("template")) and m.get("name") != ROOT.name


def cmd_init(args) -> None:
    """Set up this clone: the git hooks (core.hooksPath is local config, so every clone needs it
    once) and, in a repository made from a template, the workspace's own name and date."""
    have = hooks_path()
    if not have:
        git("config", "core.hooksPath", ".githooks")
        print("git hooks on: core.hooksPath = .githooks")
    elif have != ".githooks":
        print(f"core.hooksPath is {have} (another tool's): left alone. WorkRealm's checks run only if its "
              "hooks call .githooks/pre-commit and .githooks/commit-msg.")
    else:
        print("git hooks: already on")
    m = meta()
    name = args.name or ROOT.name
    if not m.get("template") or (name == m.get("name") and not args.name):
        return
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
        die(f"invalid name {name!r}: letters, digits, '.', '_', '-' only (pass one: init --name NAME)")
    old = m["name"]
    heading = re.compile(rf"^(#[^\n]*?)(?<![\w.-]){re.escape(old)}$")
    for path in git("ls-files", "-z", "*.md").stdout.split("\0"):
        file = ROOT / path
        if not path or not file.is_file():
            continue
        text = file.read_text(encoding="utf-8")
        first, _, rest = text.partition("\n")
        new = heading.sub(lambda mt: mt.group(1) + name, first) + ("\n" + rest if _ else "")
        if path == "STATE.md":
            new = re.sub(r"(\*\*Created:\*\*\s*)\d{4}-\d{2}-\d{2}", rf"\g<1>{today()}", new, count=1)
        if new != text:
            file.write_text(new, encoding="utf-8", newline="\n")
    m.update({"name": name, "created": today(), "from_template": old})
    m.pop("template")
    (ROOT / ".workrealm.json").write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"named {name} (was the template {old}), created {today()}")
    r = subprocess.run([sys.executable, str(ROOT / ".ai" / "checkpoint.py"), f"chore: start {name} from the {old} "
                        "template", "The workspace's own name and date replace the template's."], cwd=ROOT)
    sys.exit(r.returncode)


def cmd_ticket_start(args) -> None:
    key = args.key.strip()
    if not TICKET_KEY.fullmatch(key):
        die(f"{key!r} is not a ticket key: use the tracker's form, e.g. ABC-123")
    name = f"{args.type}/{key}" + (f"-{slug(args.title)}" if args.title else "")
    if git("rev-parse", "--verify", "-q", f"refs/heads/{name}").returncode == 0:
        die(f"branch {name} already exists: git switch {name}")
    r = git("switch", "-c", name)
    if r.returncode != 0:
        die(r.stderr.strip())
    print(f"on branch {name}. Commits made with python .ai/checkpoint.py end with `Refs: {key}`.")


def mentions(old: str) -> list[str]:
    """Tracked text files that still name `old` (links and imports a rename leaves behind)."""
    out = []
    for path in git("ls-files", "-z").stdout.split("\0"):
        file = ROOT / path
        if path and Path(path).suffix in TEXT_EXT and file.is_file():
            try:
                if old in file.read_text(encoding="utf-8"):
                    out.append(path)
            except (OSError, UnicodeDecodeError):
                continue
    return out


# `names --style` applies the R-NAMES default (lowercase ASCII kebab-case) to documents and
# figures, whose standard is the default. Code keeps its language's style, and so does a folder
# that holds code: an import or a build file may name it.
DEFAULT_STYLE_EXT = {".md", ".tex", ".canvas", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".sh"}
CODE_EXT = {".py", ".pyi", ".go", ".rs", ".c", ".h", ".cc", ".cpp", ".hpp", ".r", ".rb", ".sql", ".ps1",
            ".psm1", ".js", ".ts", ".tsx", ".jsx", ".java", ".kt", ".cs", ".m", ".toml", ".yaml", ".yml",
            ".json", ".xml", ".xacro", ".urdf", ".cmake", ".launch"}
BUILD_FILES = {"CMakeLists.txt", "Makefile", "Dockerfile", "package.xml", "setup.py", "setup.cfg"}
META_NAME = re.compile(r"^[A-Z0-9][A-Z0-9_-]*\.md$")  # STATE.md, SOURCES_LOG.md: names people look for
REF_EXT = TEXT_EXT | {".canvas", ".tex", ".bib"}
WIKILINK = re.compile(r"(!?\[\[)([^\]|#\n\\]+)")  # a table escapes the alias bar: [[note\|text]]
MD_LINK = re.compile(r"(\]\()([^)\s#]+)")
STRUCTURAL_NAMES = {"README.md", "AGENTS.md", "CLAUDE.md", "GEMINI.md", "INDEX.md", "MANIFEST.md",
                    "SUMMARY.md", "STATE.md", "TEMPLATE.md", "CHANGELOG.md", "LICENSE.md", "CONTRIBUTING.md"}
ALIASES = re.compile(r"^aliases:\s*(?:\[(.*?)\]|((?:\n\s*-\s*.+)+))", re.M)


def kebab(name: str) -> str:
    """The R-NAMES default: lowercase ASCII kebab-case; the extension is kept, lowercased."""
    suffix = Path(name).suffix if not name.startswith(".") else ""
    stem = name[:len(name) - len(suffix)] if suffix else name
    out = re.sub(r"[^a-z0-9.]+", "-", to_ascii(stem).lower()).strip("-")
    return (out or stem) + suffix.lower()


def code_dirs(paths: set[str]) -> set[str]:
    """Folders with code or a build file anywhere below them."""
    out = set()
    for path in paths:
        name = path.rsplit("/", 1)[-1]
        if Path(name).suffix.lower() in CODE_EXT or name in BUILD_FILES:
            parts = path.split("/")[:-1]
            out.update("/".join(parts[:i + 1]) for i in range(len(parts)))
    return out


def better_name(path: str, style: bool, code: set[str], keep: list[str]) -> str:
    """The name R-NAMES asks for: always safe on every system; with style, also the default
    style for documents, figures and the folders that hold only those."""
    import fnmatch
    segments = path.split("/")
    out = []
    for i, s in enumerate(segments):
        new = safe_name(s) or s
        last = i == len(segments) - 1
        here = "/".join(segments[:i + 1])
        styled = style and not s.startswith(".") and not any(fnmatch.fnmatch(here, k) or fnmatch.fnmatch(s, k)
                                                              for k in keep)
        if styled and last:
            styled = Path(s).suffix.lower() in DEFAULT_STYLE_EXT and s not in STRUCTURAL_NAMES \
                and not META_NAME.match(s)
        elif styled:
            styled = here not in code
        out.append(kebab(new) if styled else new)
    return "/".join(out)


def ref_maps(renames: list[tuple[str, str]], kept: set[str] | frozenset = frozenset()) \
        -> tuple[dict, dict, list[str]]:
    """What a reference to a renamed file or folder becomes: by name (with its extension, or a
    folder), and by note stem (an Obsidian [[link]] leaves out .md). A rename is name-local, so
    one old name always becomes one new name. When it does not -- two new names, or a path in
    `kept` that keeps the same name (a twin outside the scope) -- the name is left alone."""
    names, stems, clashes = {}, {}, set()
    for path in kept:
        for segment in path.split("/"):
            names.setdefault(segment, segment)
        if Path(path).suffix in (".md", ".canvas"):
            stems.setdefault(Path(path).stem, Path(path).stem)
    for old, new in renames:
        for table, o, n in [(names, a, b) for a, b in zip(old.split("/"), new.split("/"))] + \
                [(stems, Path(old).stem, Path(new).stem)] * (Path(old).suffix in (".md", ".canvas")):
            if o == n:
                continue
            if table.get(o, n) != n:
                clashes.add(o)
            table[o] = n
    for o in clashes:
        names.pop(o, None)
        stems.pop(o, None)
    names = {o: n for o, n in names.items() if o != n}
    stems = {o: n for o, n in stems.items() if o != n}
    return names, stems, sorted(clashes)


def map_target(target: str, names: dict, stems: dict) -> str:
    """A link target with each renamed folder, file or note stem replaced."""
    return "/".join(names.get(p) or stems.get(p) or p for p in target.split("/"))


def rewrite_refs(text: str, names: dict, stems: dict) -> str:
    """Point [[wikilinks]], Markdown links and quoted paths at the new names."""
    text = WIKILINK.sub(lambda mt: mt.group(1) + map_target(mt.group(2), names, stems), text)
    text = MD_LINK.sub(lambda mt: mt.group(0) if "://" in mt.group(2)
                       else mt.group(1) + map_target(mt.group(2), names, stems), text)
    files = sorted((k for k in names if Path(k).suffix), key=len, reverse=True)
    if files:
        text = re.sub(r"(?<![\w.-])(" + "|".join(map(re.escape, files)) + r")(?![\w-])",
                      lambda mt: names[mt.group(1)], text)
    folders = sorted((k for k in names if not Path(k).suffix), key=len, reverse=True)
    if folders:
        alt = "|".join(map(re.escape, folders))
        # A folder in a path (either separator, so Windows paths too), or a whole quoted
        # segment, as code joins it: ROOT / "notes" / "10_project".
        text = re.sub(rf"(?<![\w.-])({alt})(?=[/\\])|(?<=[/\\])({alt})(?![\w.-])|(?<=[\"'])({alt})(?=[\"'])",
                      lambda mt: names[mt.group(1) or mt.group(2) or mt.group(3)], text)
    return text


def broken_links(files: set[str], texts: dict[str, str]) -> set[tuple[str, str]]:
    """[[wikilinks]] that resolve to no file, note or alias (Obsidian resolves by name)."""
    known = {p.rsplit("/", 1)[-1].casefold() for p in files}
    known |= {Path(p).stem.casefold() for p in files if Path(p).suffix in (".md", ".canvas")}
    for text in texts.values():
        for mt in ALIASES.finditer(text):
            items = mt.group(1).split(",") if mt.group(1) is not None else re.findall(r"-\s*(.+)", mt.group(2))
            known |= {i.strip().strip("'\"").casefold() for i in items}
    out = set()
    for path, text in texts.items():
        if Path(path).suffix != ".md":
            continue
        for mt in WIKILINK.finditer(text):
            target = mt.group(2).strip()
            last = target.rsplit("/", 1)[-1].casefold()
            if last and last not in known:
                out.add((path, target))
    return out


def read_texts(paths: set[str]) -> dict[str, str]:
    out = {}
    for path in paths:
        if Path(path).suffix.lower() in REF_EXT:
            try:  # bytes, so a CRLF file keeps its line endings when it is written back
                out[path] = (ROOT / path).read_bytes().decode("utf-8")
            except (OSError, UnicodeDecodeError):
                continue
    return out


def move(path: str, better: str, tracked: set[str]) -> str | None:
    """Rename one file (git mv when tracked); the error, or None."""
    (ROOT / better).parent.mkdir(parents=True, exist_ok=True)
    if path in tracked:
        r = git("mv", path, better)
        if r.returncode != 0:
            return r.stderr.strip()
    else:
        (ROOT / path).rename(ROOT / better)
    for parent in (ROOT / path).parents:
        if parent == ROOT or not parent.is_dir() or any(parent.iterdir()):
            break
        parent.rmdir()
    return None


def cmd_names(args) -> None:
    """List the names that break R-NAMES; with --fix, rename those that can be renamed safely.
    --style also applies the default style to documents; --rewrite-refs updates what links to them."""
    m = meta()
    tracked = {t for t in git("ls-files", "-z").stdout.split("\0") if t}
    paths = tracked | {t for t in git("ls-files", "-z", "--others", "--exclude-standard").stdout.split("\0") if t}
    scope = [s.replace("\\", "/").strip("/") for s in args.paths]
    code = code_dirs(paths) if args.style else set()
    todo, planned, targets = 0, [], {}
    for path in sorted(paths):
        if scope and not any(path == s or path.startswith(s + "/") for s in scope):
            continue
        better = better_name(path, args.style, code, args.keep)
        problem = next((p for s in better.split("/") if (p := name_problem(s))), None)
        if better == path and not problem and path.isascii():
            continue
        todo += 1
        committed = git("cat-file", "-e", f"HEAD:{path}").returncode == 0
        if problem or better == path or not better.isascii():
            print(f"by hand  {path}  ({problem or 'no ASCII form'})")
        elif committed and protected_by(m, path):
            print(f"keep     {path}  (write-once evidence: its name is part of the record)")
        elif (ROOT / better).exists() and better.casefold() != path.casefold():
            print(f"by hand  {path}  ({better} already exists)")
        elif better.casefold() in targets:
            print(f"by hand  {path}  (so would {targets[better.casefold()]}: both become {better})")
        else:
            targets[better.casefold()] = path
            planned.append((path, better))
    if args.rewrite_refs and planned:
        names, stems, clashes = ref_maps(planned, paths - {old for old, _ in planned})
        texts = read_texts(paths)
        moved = dict(planned)
        after = {p: t if p in tracked and protected_by(m, p) else rewrite_refs(t, names, stems)
                 for p, t in texts.items()}
        before = {(moved.get(p, p), map_target(t, names, stems)) for p, t in broken_links(paths, texts)}
        introduced = sorted(broken_links({moved.get(p, p) for p in paths},
                                         {moved.get(p, p): t for p, t in after.items()}) - before)
        changed = sorted(moved.get(p, p) for p, t in after.items() if t != texts[p])
        if clashes:
            print(f"refs     left alone, one old name becomes two new ones: {', '.join(clashes)}")
        if introduced:
            for path, target in introduced[:20]:
                print(f"broken   {path}: [[{target}]]")
            if not args.force:
                die(f"{len(introduced)} link(s) would break: nothing renamed. Rename by hand, add --keep, "
                    "or pass --force.")
        print(f"refs     {len(changed)} file(s) {'rewritten' if args.fix else 'would be rewritten'}"
              + (f": {', '.join(changed[:10])}" + (f" (+{len(changed) - 10} more)" if len(changed) > 10 else "")
                 if changed else ""))
    if not args.fix:
        for path, better in planned:
            print(f"rename   {path} -> {better}")
    else:
        done = []
        for path, better in planned:
            error = move(path, better, tracked)
            if error:
                print(f"by hand  {path}  ({error})")
                continue
            done.append((path, better))
            print(f"renamed  {path} -> {better}")
        if args.rewrite_refs and done:
            names, stems, _ = ref_maps(done, paths - {old for old, _ in done})
            moved = dict(done)
            for path, text in read_texts({moved.get(p, p) for p in paths}).items():
                if path in tracked and protected_by(m, path):
                    continue
                new = rewrite_refs(text, names, stems)
                if new != text:
                    (ROOT / path).write_bytes(new.encode("utf-8"))
        elif done:
            for path, _ in done:
                stale = mentions(Path(path).name)
                if stale:
                    print(f"         {path} still named in: {', '.join(stale)}")
    if not todo:
        print("every name follows R-NAMES")
    elif not args.fix and planned:
        print("python .ai/wr.py names --fix renames what is listed as `rename`"
              + (" (--rewrite-refs also updates the links to it)." if not args.rewrite_refs else "."))


# ---------------------------------------------------------------- task tier

def cmd_note(args) -> None:
    need("task")
    path = path_of("notes") / f"{today()}-{slug(args.topic)}.md"
    create(path, f"# {args.topic}\n\n_{today()}. Unsettled: findings, questions, drafts. Cite sources._\n\n")


def cmd_source_add(args) -> None:
    need("task")
    staged = tier() == "project"  # project tier: agents stage, the owner promotes
    received = (Path(args.file).name if args.file else
                urllib.parse.unquote(Path(urllib.parse.urlparse(args.url).path).name)) or "download"
    name = args.name or intake_name(received)
    desc = args.desc + (f" (received as '{received}')" if not args.name and name != received else "")
    folder = path_of("inbox") if staged else path_of("sources")
    target = folder / name
    if target.exists() or (path_of("sources") / name).exists():
        die(f"{name} already exists; sources are write-once. Pass --name for a new file.")
    folder.mkdir(parents=True, exist_ok=True)
    if args.file:
        shutil.copy2(args.file, target)
    else:
        try:
            with urllib.request.urlopen(args.url, timeout=60) as r, open(target, "wb") as out:
                shutil.copyfileobj(r, out)
        except Exception as e:
            target.unlink(missing_ok=True)
            die(f"download failed: {e}. Save the file yourself and pass --file.")
    if staged:
        (target.parent / f"{target.name}.source").write_text(f"{args.url}\n{cell(desc)}\n", encoding="utf-8")
        print(f"staged {rel(target)} for review. The owner promotes it into evidence with:\n"
              f'  python .ai/wr.py source promote {rel(target)} --desc "{cell(desc)}"')
    else:
        log_source(target, args.url, desc)
        print(f"saved {rel(target)} and logged it in {layout(meta())['sources_log']}")


def cmd_source_promote(args) -> None:
    need("project")
    src = Path(args.file)
    src = (src if src.is_absolute() else ROOT / src).resolve()
    inbox = path_of("inbox").resolve()
    if src.parent != inbox or not src.is_file():
        die(f"give a file in {layout(meta())['inbox']}/")
    side = src.parent / f"{src.name}.source"
    url, desc = "", args.desc
    if side.exists():
        lines = side.read_text(encoding="utf-8").splitlines() + ["", ""]
        url, desc = lines[0], args.desc or lines[1]
    if not desc:
        die("pass --desc: what it is, version, date")
    target = path_of("sources") / intake_name(src.name)
    if target.name != src.name and "received as '" not in desc:
        desc += f" (received as '{src.name}')"
    if target.exists():
        die(f"{rel(target)} already exists; sources are write-once. Rename the inbox file first.")
    shutil.move(str(src), str(target))
    side.unlink(missing_ok=True)
    log_source(target, args.url or url or "(provided by the owner)", desc)
    print(f"promoted {rel(target)} into evidence and logged it")


def cmd_decide(args) -> None:
    need("task")
    path = path_of("decisions") / "DECISIONS.md"
    text = path.read_text(encoding="utf-8")
    n = next_id(text, "D")
    if n == 2 and empty_row(text, "D1"):
        n = 1
    row = (f"| D{n} | {today()} | {cell(args.text)} | {cell(args.alt)} | {args.supersedes or '—'} "
           f"| {cell(args.detail or '')} |")
    if n == 1:
        text = re.sub(r"^\|\s*D1\s*\|.*$", lambda _: row, text, count=1, flags=re.M)
        path.write_text(text, encoding="utf-8", newline="\n")
    else:
        append_row(path, row)
    print(f"recorded D{n} in {rel(path)}\nCommit with a body that says why: "
          f'python .ai/checkpoint.py "docs: decide <topic>" "<why>"')


def cmd_open_item(args) -> None:
    need("task")
    path = path_of("decisions") / "OPEN-ITEMS.md"
    text = path.read_text(encoding="utf-8")
    n = next_id(text, "O")
    if n == 2 and empty_row(text, "O1"):
        n = 1
    row = f"| O{n} | {cell(args.question)} | {cell(args.owner)} | {cell(args.trigger)} | {cell(args.notes or '')} |"
    if n == 1:
        text = re.sub(r"^\|\s*O1\s*\|.*$", lambda _: row, text, count=1, flags=re.M)
        path.write_text(text, encoding="utf-8", newline="\n")
    else:
        append_row(path, row, before="## Closed")
    print(f"opened O{n} in {rel(path)}")


def cmd_close_item(args) -> None:
    need("task")
    path = path_of("decisions") / "OPEN-ITEMS.md"
    lines = path.read_text(encoding="utf-8").splitlines()
    idx = next((i for i, ln in enumerate(lines) if re.match(rf"^\|\s*{re.escape(args.id)}\s*\|", ln)), None)
    if idx is None:
        die(f"{args.id} not found in {rel(path)}")
    question = lines[idx].strip().strip("|").split("|")[1].strip()
    del lines[idx]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    append_row(path, f"| {args.id} | {question} | {cell(args.answer)} | {today()} |")
    print(f"closed {args.id}")


# ---------------------------------------------------------------- project tier

def cmd_plan_new(args) -> None:
    need("project")
    create(path_of("plans") / f"{slug(args.topic)}.md",
           f"# {args.topic}\n\n_{today()}._\n\n## Goal\n\n## Phases\n\n| Phase | Exit criteria | State |\n"
           "|---|---|---|\n|  |  |  |\n\n## Risks\n")


ADR_LIKE = re.compile(r"^(?P<pre>[A-Za-z]*[-_]?)(?P<num>\d+)(?P<sep>[-_])[^/]+\.md$")


def cmd_adr_new(args) -> None:
    need("project")
    folder = path_of("adr")
    found = [m for p in folder.glob("*.md") if (m := ADR_LIKE.match(p.name))]
    # Follow the numbering the folder already uses (an adopted ADR-001-x.md), else NNNN-title.md.
    pre, width, sep = max(((m["pre"], len(m["num"]), m["sep"]) for m in found),
                          key=lambda s: sum(1 for m in found if (m["pre"], len(m["num"]), m["sep"]) == s),
                          default=("", 4, "-"))
    n = max((int(m["num"]) for m in found), default=0) + 1
    number = f"{pre}{n:0{width}d}"
    path = folder / f"{number}{sep}{slug(args.title)}.md"
    template_path = folder / "TEMPLATE.md"
    if not template_path.exists():
        die(f"{rel(template_path)} is missing; restore it with: wr doctor --fix")
    template = template_path.read_text(encoding="utf-8")
    text = (template.replace("# NNNN — Title", f"# {number} — {args.title}")
            .replace("**Status:** Proposed | Accepted | Superseded by NNNN", "**Status:** Proposed")
            .replace("**Date:** YYYY-MM-DD", f"**Date:** {today()}"))
    create(path, text)
    print(f'Then: python .ai/wr.py decide "..." --alt "..." --detail {rel(path)}')


def cmd_exp_new(args) -> None:
    need("project")
    folder = path_of("experiments") / f"{today()}-{slug(args.topic)}"
    create(folder / "README.md",
           f"# {args.topic}\n\n## Question\n\n## Method\n\n_Or the protocol, step by step, so a run can be "
           "repeated._\n\n## Runs\n\nOne folder per run in `results/` "
           f"(`python .ai/wr.py run new {folder.name}`).\n\n## Conclusion\n\n"
           "_What the numbers show. A decision drawn from it goes to the decisions register._\n")


def cmd_run_new(args) -> None:
    need("project")
    exps = path_of("experiments")
    exp = exps / args.experiment
    if not (exp / "README.md").exists():
        known = ", ".join(sorted(p.name for p in exps.iterdir() if p.is_dir())) or "none yet"
        die(f"no experiment {args.experiment!r} (known: {known}). Create one with exp new.")
    stem = today()
    name, n = stem, 1
    while (exp / "results" / name).exists():
        n += 1
        name = f"{stem}-{n:02d}"
    commit = git("rev-parse", "--short", "HEAD").stdout.strip()
    create(exp / "results" / name / "README.md",
           f"# Run {name}\n\n- **Commit under test:** {commit}\n- **Environment:** \n\n## Numbers\n\n"
           "_Record measurements and raw output, not verdicts. This folder is write-once once committed._\n")


def cmd_release_cut(args) -> None:
    need("project")
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-[\w.]+)?", args.version):
        die("version must look like v1.2.0 or v1.2.0-pilot")
    if git("status", "--porcelain").stdout.strip():
        die("commit first: a release is cut from a clean, committed tree")
    dest = path_of("releases") / args.version
    if dest.exists():
        die(f"{rel(dest)} exists; releases are immutable. Cut a new version.")
    files = []
    for inc in args.include:
        src = (ROOT / inc).resolve()
        if not src.exists():
            die(f"{inc} does not exist")
        items = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.is_file())
        for f in items:
            target = dest / f.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, target)
            files.append((rel(target), hashlib.sha256(f.read_bytes()).hexdigest()[:16]))
    commit = git("rev-parse", "--short", "HEAD").stdout.strip()
    manifest = [f"# Release {args.version}", "", f"- **Date:** {today()}", f"- **Source commit:** {commit}",
                "", "| File | sha256 (16) |", "|---|---|"] + [f"| {p} | {h} |" for p, h in files]
    (dest / "MANIFEST.md").write_text("\n".join(manifest) + "\n", encoding="utf-8", newline="\n")
    (dest / "SUMMARY.md").write_text(f"# {args.version}\n\n_What it is, for whom, what changed since the "
                                     "previous release, known limits._\n", encoding="utf-8", newline="\n")
    print(f"cut {rel(dest)} ({len(files)} files). Fill in SUMMARY.md, then commit: "
          f'python .ai/checkpoint.py "chore: release {args.version}" "<to whom, for what>"')


# ---------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> None:
    try:
        sys.stdout.reconfigure(errors="backslashreplace")
    except Exception:
        pass
    p = argparse.ArgumentParser(prog="python .ai/wr.py", description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog=__doc__.split("\n\n")[1])
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="where things stand").set_defaults(func=cmd_status)
    i = sub.add_parser("init", help="set up this clone: git hooks; a repo made from a template gets its own name")
    i.add_argument("--name", help="the workspace's name (default: the folder's)")
    i.set_defaults(func=cmd_init)
    c = sub.add_parser("checkpoint", help="commit everything after the policy checks")
    c.add_argument("subject")
    c.add_argument("body", nargs="?")
    c.add_argument("--agent", help=argparse.SUPPRESS)
    c.set_defaults(func=cmd_checkpoint)
    sub.add_parser("handoff", help="status plus the end-of-session checklist").set_defaults(func=cmd_handoff)
    t = sub.add_parser("ticket", help="work on a ticket").add_subparsers(dest="action", required=True)
    ts = t.add_parser("start", help="create and switch to a branch named after the ticket")
    ts.add_argument("key", help="ticket key, e.g. ABC-123")
    ts.add_argument("title", nargs="?", help="a few words for the branch name")
    ts.add_argument("--type", default="feat", choices=["feat", "fix", "docs", "chore", "refactor", "test"])
    ts.set_defaults(func=cmd_ticket_start)
    nm = sub.add_parser("names", help="names that break R-NAMES (ASCII, no spaces, safe on every system)")
    nm.add_argument("paths", nargs="*", help="only these files or folders")
    nm.add_argument("--fix", action="store_true", help="rename them with git mv")
    nm.add_argument("--style", action="store_true",
                    help="also give documents, figures and their folders the default style (kebab-case)")
    nm.add_argument("--rewrite-refs", action="store_true",
                    help="update [[wikilinks]], Markdown links and quoted paths; refuse if a link would break")
    nm.add_argument("--keep", action="append", default=[], metavar="GLOB",
                    help="a path or name that keeps its name (repeatable), e.g. a folder a tool's config names")
    nm.add_argument("--force", action="store_true", help="rename even if a link would break")
    nm.set_defaults(func=cmd_names)

    n = sub.add_parser("note", help="new dated note")
    n.add_argument("topic")
    n.set_defaults(func=cmd_note)

    s = sub.add_parser("source", help="add a source (project tier: into the inbox) or promote one")
    ssub = s.add_subparsers(dest="action", required=True)
    sa = ssub.add_parser("add")
    sa.add_argument("url", help="where it came from (logged even with --file)")
    sa.add_argument("--desc", required=True)
    sa.add_argument("--file", help="local file to copy instead of downloading")
    sa.add_argument("--name", help="file name to save it under")
    sa.set_defaults(func=cmd_source_add)
    sp = ssub.add_parser("promote")
    sp.add_argument("file", help="a file in the inbox")
    sp.add_argument("--desc", help="what it is (default: the description given at add)")
    sp.add_argument("--url", help="origin (default: the URL given at add)")
    sp.set_defaults(func=cmd_source_promote)

    d = sub.add_parser("decide", help="record a decision in DECISIONS.md")
    d.add_argument("text")
    d.add_argument("--alt", required=True, help="strongest alternative -- why it lost")
    d.add_argument("--supersedes", help="row it replaces, e.g. D3")
    d.add_argument("--detail", help="ADR or note with the full argument")
    d.set_defaults(func=cmd_decide)

    o = sub.add_parser("open-item", help="record an unresolved question")
    o.add_argument("question")
    o.add_argument("--owner", required=True)
    o.add_argument("--trigger", required=True, help="when it must be answered by")
    o.add_argument("--notes")
    o.set_defaults(func=cmd_open_item)
    ci = sub.add_parser("close-item", help="move an open item to Closed with its answer")
    ci.add_argument("id")
    ci.add_argument("answer")
    ci.set_defaults(func=cmd_close_item)

    for name, func, arg in (("plan", cmd_plan_new, "topic"), ("adr", cmd_adr_new, "title"),
                            ("exp", cmd_exp_new, "topic"), ("run", cmd_run_new, "experiment")):
        g = sub.add_parser(name).add_subparsers(dest="action", required=True).add_parser("new")
        g.add_argument(arg)
        g.set_defaults(func=func)
    rc = sub.add_parser("release").add_subparsers(dest="action", required=True).add_parser("cut")
    rc.add_argument("version")
    rc.add_argument("--include", nargs="+", required=True)
    rc.set_defaults(func=cmd_release_cut)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
