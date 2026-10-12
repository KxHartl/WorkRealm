#!/usr/bin/env python3
"""Workspace helpers -- the right way to do a thing in one command, from any tool.

    python .ai/wr.py status                      where things stand (also shown at session start)
    python .ai/wr.py checkpoint "type: msg" [body]
    python .ai/wr.py handoff                     before ending a session
    python .ai/wr.py note TOPIC                  task+   10-research/notes/<date>-<topic>.md
    python .ai/wr.py source add URL --desc D [--file LOCAL] [--name NAME]     task+
    python .ai/wr.py decide TEXT --alt "OPTION -- why it lost" [--supersedes D1] [--detail REF]  task+
    python .ai/wr.py open-item QUESTION --owner WHO --trigger WHEN            task+
    python .ai/wr.py close-item O3 ANSWER                                     task+
    python .ai/wr.py adr new TITLE              project
    python .ai/wr.py exp new TOPIC              project
    python .ai/wr.py run new [TOPIC]            project
    python .ai/wr.py prompt new TOPIC | prompt done FILE                      project
    python .ai/wr.py release cut VERSION --include PATH [PATH ...]            project

Each helper produces what the checks in policy.py accept: correct names, complete rows,
logged sources. Rule text lives in AGENTS.md; this file only does the mechanics.
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


def need(tier: str) -> None:
    have = meta().get("tier", "quick")
    if TIERS.index(have) < TIERS.index(tier):
        die(f"this needs the {tier} tier (workspace is {have}). Upgrade with the generator: "
            f"wr upgrade --to {tier}")


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-c", "core.quotepath=off", *args], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def today() -> str:
    return dt.date.today().isoformat()


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if not s:
        die(f"cannot make a file name from {text!r}; use letters or digits")
    return s[:60].rstrip("-")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


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


# ---------------------------------------------------------------- status

def open_items() -> int | None:
    path = ROOT / "30-decisions" / "OPEN-ITEMS.md"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").split("## Closed", 1)[0]
    return sum(1 for m in re.finditer(r"^\|\s*O\d+\s*\|([^|]*)\|", text, re.M) if m.group(1).strip())


def git_summary() -> dict:
    branch = git("symbolic-ref", "--short", "-q", "HEAD").stdout.strip() or "(detached)"
    dirty = len([ln for ln in git("status", "--porcelain").stdout.splitlines() if ln.strip()])
    remote = git("remote", "get-url", "origin").returncode == 0
    unpushed = None
    if remote:
        r = git("rev-list", "--count", "@{upstream}..HEAD")
        unpushed = int(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip().isdigit() else None
    return {"branch": branch, "dirty": dirty, "remote": remote, "unpushed": unpushed}


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
    items = open_items()
    if items is not None:
        lines.append(f"Open items: {items} (30-decisions/OPEN-ITEMS.md)")
    lines.append("Helpers: python .ai/wr.py --help (decide, note, source add, adr new, ...)")
    state = ROOT / "STATE.md"
    if state.exists():
        body = state.read_text(encoding="utf-8").splitlines()
        lines += ["", "--- STATE.md ---"] + body[:STATE_LINES]
        if len(body) > STATE_LINES:
            lines.append(f"... {len(body) - STATE_LINES} more lines. STATE.md is meant to be short: "
                         "summarise it, move detail into notes or decisions.")
    return "\n".join(lines)


def cmd_status(args) -> None:
    print(status_text())


def cmd_checkpoint(args) -> None:
    r = subprocess.run([sys.executable, str(ROOT / ".ai" / "checkpoint.py"), args.subject,
                        *([args.body] if args.body else [])], cwd=ROOT)
    sys.exit(r.returncode)


def cmd_handoff(args) -> None:
    print(status_text())
    print("\nBefore ending the session:\n"
          "  1. STATE.md: what was done, the next concrete step, anything blocking or waiting on the owner.\n"
          "  2. Anything unresolved that someone must answer -> python .ai/wr.py open-item ...\n"
          '  3. python .ai/checkpoint.py "docs: update STATE for handoff"  (the tree must be clean)')


# ---------------------------------------------------------------- task tier

def cmd_note(args) -> None:
    need("task")
    path = ROOT / "10-research" / "notes" / f"{today()}-{slug(args.topic)}.md"
    create(path, f"# {args.topic}\n\n_{today()}. Unsettled: findings, questions, drafts. Cite sources._\n\n")


def cmd_source_add(args) -> None:
    need("task")
    name = args.name or (Path(args.file).name if args.file else
                         Path(urllib.parse.urlparse(args.url).path).name) or "download"
    target = ROOT / "10-research" / "sources" / name
    if target.exists():
        die(f"{rel(target)} already exists; sources are write-once. Pass --name for a new file.")
    target.parent.mkdir(parents=True, exist_ok=True)
    if args.file:
        shutil.copy2(args.file, target)
    else:
        try:
            with urllib.request.urlopen(args.url, timeout=60) as r, open(target, "wb") as out:
                shutil.copyfileobj(r, out)
        except Exception as e:
            target.unlink(missing_ok=True)
            die(f"download failed: {e}. Save the file yourself and pass --file.")
    log = ROOT / "10-research" / "SOURCES_LOG.md"
    lead = "" if log.read_text(encoding="utf-8").endswith("\n") else "\n"  # never rewrite the last line
    with open(log, "a", encoding="utf-8", newline="\n") as f:
        f.write(f"{lead}{today()} — {args.url} — {rel(target)} — {cell(args.desc)}\n")
    print(f"saved {rel(target)} and logged it in {rel(log)}")


def cmd_decide(args) -> None:
    need("task")
    path = ROOT / "30-decisions" / "DECISIONS.md"
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
    path = ROOT / "30-decisions" / "OPEN-ITEMS.md"
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
    path = ROOT / "30-decisions" / "OPEN-ITEMS.md"
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

def cmd_adr_new(args) -> None:
    need("project")
    folder = ROOT / "30-decisions"
    nums = [int(m.group(1)) for p in folder.glob("ADR-*.md") if (m := re.match(r"ADR-(\d+)-", p.name))]
    n = max(nums, default=0) + 1
    path = folder / f"ADR-{n:02d}-{slug(args.title)}.md"
    template = (folder / "ADR-TEMPLATE.md").read_text(encoding="utf-8")
    text = (template.replace("# ADR-NN — Title", f"# ADR-{n:02d} — {args.title}")
            .replace("**Status:** Proposed | Accepted | Superseded by ADR-NN", "**Status:** Proposed")
            .replace("**Date:** YYYY-MM-DD", f"**Date:** {today()}"))
    create(path, text)
    print(f"Then: python .ai/wr.py decide \"...\" --alt \"...\" --detail {path.name}")


def cmd_exp_new(args) -> None:
    need("project")
    path = ROOT / "10-research" / "experiments" / f"EXP-{today().replace('-', '')}-{slug(args.topic)}" / "README.md"
    create(path, f"# {args.topic}\n\n## Hypothesis\n\n## Method\n\n## Result\n\n## Conclusion\n")


def cmd_run_new(args) -> None:
    need("project")
    base = ROOT / "40-lab" / "results"
    stem = f"RUN-{today().replace('-', '')}"
    name, n = stem, 1
    while (base / name).exists():
        n += 1
        name = f"{stem}-{n:02d}"
    create(base / name / "README.md",
           f"# {name}{' — ' + args.topic if args.topic else ''}\n\n"
           "Protocol: \nCommit under test: \n\n## Numbers\n\n_Record measurements, not verdicts._\n")


def cmd_prompt_new(args) -> None:
    need("project")
    create(ROOT / "20-prompts" / "active" / f"{today()}-{slug(args.topic)}.md", f"# {args.topic}\n\n")


def cmd_prompt_done(args) -> None:
    need("project")
    src = Path(args.file)
    src = src if src.is_absolute() else ROOT / src
    if not src.exists() or src.parent != ROOT / "20-prompts" / "active":
        die("give a file in 20-prompts/active/")
    r = git("mv", rel(src), f"20-prompts/archive/{src.name}")
    if r.returncode != 0:
        die(r.stderr.strip())
    print(f"moved {src.name} to 20-prompts/archive/")


def cmd_release_cut(args) -> None:
    need("project")
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-[\w.]+)?", args.version):
        die("version must look like v1.2.0 or v1.2.0-pilot")
    if git("status", "--porcelain").stdout.strip():
        die("commit first: a release is cut from a clean, committed tree")
    dest = ROOT / "50-release" / args.version
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
    print(f"cut {rel(dest)} ({len(files)} files) -- commit it: "
          f'python .ai/checkpoint.py "chore: release {args.version}"')


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
    c = sub.add_parser("checkpoint", help="commit everything after the policy checks")
    c.add_argument("subject")
    c.add_argument("body", nargs="?")
    c.set_defaults(func=cmd_checkpoint)
    sub.add_parser("handoff", help="status plus the end-of-session checklist").set_defaults(func=cmd_handoff)

    n = sub.add_parser("note", help="new dated note in 10-research/notes/")
    n.add_argument("topic")
    n.set_defaults(func=cmd_note)

    s = sub.add_parser("source", help="add a source and log it")
    ssub = s.add_subparsers(dest="action", required=True)
    sa = ssub.add_parser("add")
    sa.add_argument("url", help="where it came from (logged even with --file)")
    sa.add_argument("--desc", required=True)
    sa.add_argument("--file", help="local file to copy instead of downloading")
    sa.add_argument("--name", help="file name inside sources/")
    sa.set_defaults(func=cmd_source_add)

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

    for name, func, arg in (("adr", cmd_adr_new, "title"), ("exp", cmd_exp_new, "topic")):
        g = sub.add_parser(name).add_subparsers(dest="action", required=True).add_parser("new")
        g.add_argument(arg)
        g.set_defaults(func=func)
    r = sub.add_parser("run").add_subparsers(dest="action", required=True).add_parser("new")
    r.add_argument("topic", nargs="?")
    r.set_defaults(func=cmd_run_new)
    pr = sub.add_parser("prompt").add_subparsers(dest="action", required=True)
    pn = pr.add_parser("new")
    pn.add_argument("topic")
    pn.set_defaults(func=cmd_prompt_new)
    pd = pr.add_parser("done")
    pd.add_argument("file")
    pd.set_defaults(func=cmd_prompt_done)
    rc = sub.add_parser("release").add_subparsers(dest="action", required=True).add_parser("cut")
    rc.add_argument("version")
    rc.add_argument("--include", nargs="+", required=True)
    rc.set_defaults(func=cmd_release_cut)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
