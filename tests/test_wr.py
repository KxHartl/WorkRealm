"""End-to-end tests: scaffold each tier into a temp dir and exercise the hooks.

    python -m unittest discover tests
"""
import importlib.util
import json
import os
import shutil
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WR = ROOT / "wr.py"


NO_BRAIN = {**os.environ, "AGENTBRAIN_PATH": str(Path(tempfile.gettempdir()) / "wr-test-no-brain")}


def run_wr(*args: str, cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run the generator. By default with no AgentBrain, so the real brain never shapes a test."""
    return subprocess.run([sys.executable, str(WR), *args], cwd=cwd, capture_output=True, text=True,
                          env=env or NO_BRAIN)


def run_hook(ws: Path, script: str, payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ws / ".ai" / "hooks" / script)], cwd=ws,
                          input=json.dumps(payload), capture_output=True, text=True,
                          env={**os.environ, "CLAUDE_PROJECT_DIR": str(ws)})


def git(ws: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=ws, capture_output=True, text=True).stdout


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def new(self, name: str, *flags: str) -> Path:
        r = run_wr("new", name, "--dir", str(self.tmp), "--no-remote", *flags)
        self.assertEqual(r.returncode, 0, r.stderr)
        return self.tmp / name


class TestNew(Base):
    def test_default_is_task(self):
        ws = self.new("t1")
        meta = json.loads((ws / ".workrealm.json").read_text())
        self.assertEqual(meta["tier"], "task")
        self.assertTrue((ws / "docs" / "decisions" / "DECISIONS.md").exists())
        self.assertTrue((ws / "references" / "SOURCES_LOG.md").exists())
        self.assertFalse((ws / "experiments").exists())

    def test_quick_is_minimal(self):
        ws = self.new("q1", "--quick")
        self.assertTrue((ws / "STATE.md").exists())
        self.assertTrue((ws / ".ai" / "checkpoint.py").exists())
        self.assertFalse((ws / "docs").exists())
        settings = json.loads((ws / ".claude" / "settings.json").read_text())
        self.assertEqual([m["matcher"] for m in settings["hooks"]["PreToolUse"]], ["Bash|PowerShell"])
        self.assertIn("SessionStart", settings["hooks"])
        self.assertIn(".ai/statusline.py", settings["statusLine"]["command"])
        self.assertIn("Read(./.env)", settings["permissions"]["deny"])
        self.assertTrue((ws / ".claude" / "skills" / "checkpoint" / "SKILL.md").exists())
        self.assertFalse((ws / ".claude" / "skills" / "decide").exists())
        self.assertIn("@./AGENTS.md", (ws / "GEMINI.md").read_text(encoding="utf-8"))

    def test_project_has_zones_and_guard(self):
        ws = self.new("p1", "--project")
        for folder in ("docs/notes", "docs/plans", "docs/decisions/adr", "references/inbox", "data/raw",
                       "data/processed", "src", "tests", "reports", "experiments", "releases", "archive"):
            self.assertTrue((ws / folder).is_dir(), folder)
        settings = json.loads((ws / ".claude" / "settings.json").read_text())
        cmds = [h["command"] for h in settings["hooks"]["PreToolUse"][0]["hooks"]]
        self.assertTrue(any("zone_guard" in c for c in cmds))
        self.assertIn("Tier:** project", (ws / "STATE.md").read_text(encoding="utf-8"))

    def test_rules_are_cumulative(self):
        agents = (self.new("p2", "--project") / "AGENTS.md").read_text(encoding="utf-8")
        for heading in ("## Context first", "## Where things go", "## The project layout"):
            self.assertIn(heading, agents)
        self.assertNotIn("{{", agents)

    def test_placeholders_rendered_everywhere(self):
        ws = self.new("p3", "--project")
        for f in ws.rglob("*"):
            if f.is_file() and ".git" not in f.parts and f.suffix in (".md", ".json", ".py"):
                self.assertNotIn("{{", f.read_text(encoding="utf-8"), f)

    def test_initial_commit_clean_and_hook_installed(self):
        ws = self.new("t2")
        self.assertEqual(git(ws, "status", "--porcelain"), "")
        self.assertIn("scaffold task workspace", git(ws, "log", "--oneline"))
        self.assertEqual(git(ws, "config", "core.hooksPath").strip(), ".githooks")
        for hook in ("pre-commit", "commit-msg", "post-commit"):
            self.assertTrue((ws / ".githooks" / hook).exists(), hook)

    def test_scaffold_passes_its_own_checks_silently(self):
        ws = self.new("t3", "--project")
        subprocess.run(["git", "checkout", "-q", "--orphan", "fresh"], cwd=ws)  # every file staged as added
        self.assertIn("A  AGENTS.md", git(ws, "status", "--porcelain"))
        r = subprocess.run([sys.executable, ".ai/policy.py", "pre-commit"], cwd=ws, capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stderr), (0, ""))

    def test_flags_exclusive_and_nonempty_target_refused(self):
        self.assertNotEqual(run_wr("new", "x", "--quick", "--project", "--dir", str(self.tmp)).returncode, 0)
        (self.tmp / "full").mkdir()
        (self.tmp / "full" / "f").write_text("x")
        self.assertNotEqual(run_wr("new", "full", "--dir", str(self.tmp), "--no-remote").returncode, 0)


class TestUpgrade(Base):
    def test_quick_to_project_adds_and_preserves(self):
        ws = self.new("u1", "--quick")
        (ws / "STATE.md").write_text("my state", encoding="utf-8")
        agents = ws / "AGENTS.md"
        agents.write_text(agents.read_text(encoding="utf-8") + "\n- my own rule\n", encoding="utf-8")

        r = run_wr("upgrade", "--to", "project", "--path", str(ws))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((ws / "STATE.md").read_text(encoding="utf-8"), "my state")
        text = agents.read_text(encoding="utf-8")
        self.assertIn("- my own rule", text)
        self.assertIn("## The project layout", text)
        self.assertEqual(text.count("## Context first"), 1)
        self.assertTrue((ws / "experiments" / "README.md").exists())
        self.assertEqual(json.loads((ws / ".workrealm.json").read_text())["tier"], "project")

    def test_no_downgrade(self):
        ws = self.new("u2", "--project")
        self.assertNotEqual(run_wr("upgrade", "--to", "task", "--path", str(ws)).returncode, 0)


class TestHooks(Base):
    def test_protect_paths(self):
        ws = self.new("h1")
        src = ws / "references" / "spec.pdf"
        src.write_bytes(b"x")
        blocked = run_hook(ws, "protect_paths.py", {"tool_name": "Edit", "tool_input": {"file_path": str(src)}})
        self.assertEqual(blocked.returncode, 2)
        new = run_hook(ws, "protect_paths.py",
                       {"tool_name": "Write", "tool_input": {"file_path": str(src.with_name("new.pdf"))}})
        self.assertEqual(new.returncode, 0)
        note = run_hook(ws, "protect_paths.py",
                        {"tool_name": "Edit", "tool_input": {"file_path": str(ws / "docs" / "notes" / "a.md")}})
        self.assertEqual(note.returncode, 0)

    def test_zone_guard(self):
        ws = self.new("h2", "--project")
        stray = run_hook(ws, "zone_guard.py",
                         {"tool_name": "Write", "tool_input": {"file_path": str(ws / "docs" / "notes" / "DECISIONS.md")}})
        self.assertEqual(stray.returncode, 2)
        (ws / "docs" / "notes" / "plan.md").write_text("x")
        copy = run_hook(ws, "zone_guard.py",
                        {"tool_name": "Write", "tool_input": {"file_path": str(ws / "docs" / "plans" / "plan.md")}})
        self.assertEqual(copy.returncode, 2)
        ok = run_hook(ws, "zone_guard.py",
                      {"tool_name": "Write", "tool_input": {"file_path": str(ws / "docs" / "decisions" / "adr" / "0001-x.md")}})
        self.assertEqual(ok.returncode, 0)
        snapshot = run_hook(ws, "zone_guard.py",
                            {"tool_name": "Write", "tool_input": {"file_path": str(ws / "releases" / "v1.0.0" / "plan.md")}})
        self.assertEqual(snapshot.returncode, 0)
        nb = run_hook(ws, "zone_guard.py",
                      {"tool_name": "NotebookEdit", "tool_input": {"notebook_path": str(ws / "src" / "CONSTRAINTS.md")}})
        self.assertEqual(nb.returncode, 2)

    def test_checkpoint_gate_and_checkpoint(self):
        ws = self.new("h3", "--quick")
        (ws / "work.txt").write_text("x")
        self.assertEqual(run_hook(ws, "checkpoint_gate.py", {}).returncode, 2)
        self.assertEqual(run_hook(ws, "checkpoint_gate.py", {"stop_hook_active": True}).returncode, 0)
        r = subprocess.run([sys.executable, ".ai/checkpoint.py", "feat: work"], cwd=ws, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(run_hook(ws, "checkpoint_gate.py", {}).returncode, 0)

    def test_checkpoint_refuses_secrets(self):
        ws = self.new("h4", "--quick")
        (ws / "deploy.pem").write_text("k")
        (ws / ".gitignore").write_text("")  # simulate a gitignore that let it through
        r = subprocess.run([sys.executable, ".ai/checkpoint.py", "feat: oops"], cwd=ws, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("deploy.pem", r.stderr)
        self.assertEqual(git(ws, "log", "--oneline").count("\n"), 1)


def commit(ws: Path, *messages: str) -> subprocess.CompletedProcess:
    """A plain `git commit`, as Gemini, Codex or a human would make it -- no Claude hooks."""
    subprocess.run(["git", "add", "-A"], cwd=ws, capture_output=True)
    msg = [arg for m in messages for arg in ("-m", m)]
    return subprocess.run(["git", "commit", "-q", *msg], cwd=ws, capture_output=True, text=True)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class TestGitPolicy(Base):
    """The git layer binds every tool, so each check is exercised through `git commit`."""

    def assertRefused(self, r: subprocess.CompletedProcess, rule: str):
        self.assertNotEqual(r.returncode, 0, "commit should have been refused")
        self.assertIn(rule, r.stderr)

    def assertCommitted(self, r: subprocess.CompletedProcess):
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_secret_refused(self):
        ws = self.new("g1", "--quick")
        write(ws / ".env", "TOKEN=x")
        subprocess.run(["git", "add", "-f", ".env"], cwd=ws)
        self.assertRefused(commit(ws, "feat: config"), "R-SECRETS")

    def test_commit_message_must_be_conventional(self):
        ws = self.new("g2", "--quick")
        write(ws / "a.txt", "x")
        self.assertRefused(commit(ws, "added stuff"), "R-COMMIT")
        self.assertCommitted(commit(ws, "feat: add a"))

    def test_sources_logged_and_write_once(self):
        ws = self.new("g3")
        src = ws / "references" / "spec.pdf"
        write(src, "v1")
        self.assertRefused(commit(ws, "docs: add spec"), "R-SOURCES")
        log = ws / "references" / "SOURCES_LOG.md"
        write(log, log.read_text(encoding="utf-8") + "\n2026-10-12 — https://x — references/spec.pdf — spec\n")
        self.assertCommitted(commit(ws, "docs: add spec"))
        write(src, "v2")
        self.assertRefused(commit(ws, "docs: tweak spec"), "R-SOURCES")
        subprocess.run(["git", "checkout", "--", "."], cwd=ws)
        src.unlink()
        self.assertRefused(commit(ws, "chore: drop spec"), "R-SOURCES")
        subprocess.run(["git", "checkout", "--", "."], cwd=ws)
        write(log, "# Sources log\n")
        self.assertRefused(commit(ws, "docs: tidy log"), "R-SOURCES")

    def test_naming(self):
        ws = self.new("g4")
        write(ws / "docs" / "notes" / "Random Notes.md", "x")
        self.assertRefused(commit(ws, "docs: notes"), "R-PLACE")
        subprocess.run(["git", "reset", "-q"], cwd=ws)
        (ws / "docs" / "notes" / "Random Notes.md").unlink()
        write(ws / "docs" / "notes" / "2026-10-12-vendor-options.md", "x")
        self.assertCommitted(commit(ws, "docs: notes"))

    def test_decision_register(self):
        ws = self.new("g5")
        dec = ws / "docs" / "decisions" / "DECISIONS.md"
        base = dec.read_text(encoding="utf-8")
        d1 = "| D1 | 2026-10-12 | Use Postgres | SQLite — no concurrent writers | — | |"
        write(dec, base.replace("| D1 | | | | — | |", "| D1 | 2026-10-12 | Use Postgres | | — | |"))
        self.assertRefused(commit(ws, "docs: decide db", "why"), "R-DECISIONS")   # no alternative
        write(dec, base.replace("| D1 | | | | — | |", d1))
        self.assertRefused(commit(ws, "docs: decide db"), "R-DECISIONS")          # no body
        self.assertCommitted(commit(ws, "docs: decide db", "Concurrency needs it."))
        write(dec, dec.read_text(encoding="utf-8").replace("Use Postgres", "Use MySQL"))
        self.assertRefused(commit(ws, "docs: change db", "why"), "R-DECISIONS")   # edited a settled row
        write(dec, base.replace("| D1 | | | | — | |", d1)
              + "| D2 | 2026-10-13 | Use MySQL | Postgres — licence | D1 | |\n")
        self.assertCommitted(commit(ws, "docs: supersede D1", "Licence review."))

    def test_open_item_needs_owner_and_trigger(self):
        ws = self.new("g6")
        oi = ws / "docs" / "decisions" / "OPEN-ITEMS.md"
        base = oi.read_text(encoding="utf-8")
        write(oi, base.replace("| O1 | | | | |", "| O1 | Which vendor? | KH | | |"))
        self.assertRefused(commit(ws, "docs: open item", "why"), "R-DECISIONS")
        write(oi, base.replace("| O1 | | | | |", "| O1 | Which vendor? | KH | before pilot | |"))
        self.assertCommitted(commit(ws, "docs: open item", "Blocks the pilot."))

    def test_adr_format_and_zones(self):
        ws = self.new("g7", "--project")
        adr = ws / "docs" / "decisions" / "adr"
        write(adr / "0001-storage.md", "# 0001\n\n## Decision\n\nPostgres.\n")
        self.assertRefused(commit(ws, "docs: adr", "why"), "R-ADR")
        write(adr / "0001-storage.md", (adr / "TEMPLATE.md").read_text(encoding="utf-8"))
        self.assertCommitted(commit(ws, "docs: adr", "Storage needs an argued decision."))
        write(adr / "ADR-2-cache.md", "x")
        self.assertRefused(commit(ws, "docs: adr", "why"), "R-PLACE")
        subprocess.run(["git", "reset", "-q"], cwd=ws)
        (adr / "ADR-2-cache.md").unlink()

        write(ws / "docs" / "notes" / "2026-10-12-draft.md", "x")
        self.assertCommitted(commit(ws, "docs: draft"))
        write(ws / "reports" / "2026-10-12-draft.md", "x")
        self.assertRefused(commit(ws, "docs: copy draft"), "R-ZONES")
        subprocess.run(["git", "reset", "-q"], cwd=ws)
        (ws / "reports" / "2026-10-12-draft.md").unlink()
        write(ws / "src" / "DECISIONS.md", "x")
        self.assertRefused(commit(ws, "docs: stray"), "R-ZONES")

    def test_english_warns_but_commits(self):
        ws = self.new("g8", "--quick")
        write(ws / "notes.md", "Odluka je donesena: što prije.\n")
        r = commit(ws, "docs: note")
        self.assertCommitted(r)
        self.assertIn("R-LANG", r.stderr)
        write(ws / "names.md", "The file was `izvješće.pdf`; letters like `č` are quoted.\n")
        self.assertNotIn("R-LANG", commit(ws, "docs: names").stderr)   # code spans are literal

    def test_final_outputs_are_croatian_everything_else_english(self):
        ws = self.new("g9")
        self.assertIn("are written in Croatian", (ws / "AGENTS.md").read_text(encoding="utf-8"))
        write(ws / "reports" / "izvjestaj.md", "Zaključak: rizik je prihvatljiv.\n")
        self.assertNotIn("R-LANG", commit(ws, "docs: draft report").stderr)
        write(ws / "docs" / "notes" / "2026-10-16-findings.md", "Zaključak: rizik je prihvatljiv.\n")
        self.assertIn("R-LANG", commit(ws, "docs: findings").stderr)  # notes stay English


class TestRuleContract(unittest.TestCase):
    """Every rule declares its enforcement; every declared layer really exists at that tier."""

    TAG = re.compile(r"^> \*\*(R-[A-Z]+)\*\* · (advisory|enforced by: ([a-z, ]+))$", re.M)

    def test_every_rule_is_tagged_and_enforced(self):
        spec = importlib.util.spec_from_file_location("policy", ROOT / "tiers" / "quick" / ".ai" / "policy.py")
        policy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(policy)
        sys.path.insert(0, str(ROOT))
        import wr

        seen = set()
        for tier in wr.TIERS:
            text = (ROOT / "tiers" / tier / "_RULES.md").read_text(encoding="utf-8")
            sections = [ln for ln in text.splitlines() if ln.startswith("## ")
                        and ln != "## How these rules bind"]
            tags = self.TAG.findall(text)
            self.assertEqual(len(tags), len(sections), f"{tier}: every rule section needs a tag")
            enabled = wr.cumulative(wr.CHECKS, tier)
            for rule, kind, layers in tags:
                seen.add(rule)
                if kind == "advisory":
                    self.assertNotIn(rule, policy.ENFORCES, f"{rule} is enforced but tagged advisory")
                    continue
                declared = {layer.strip() for layer in layers.split(",")}
                self.assertEqual(declared, set(policy.ENFORCES[rule]), rule)
                for check in policy.ENFORCES[rule].get("git", []):
                    self.assertIn(check, enabled, f"{rule}: check {check} not enabled at {tier}")
                for script in policy.ENFORCES[rule].get("claude", []):
                    self.assertTrue(any((ROOT / "tiers" / t / ".ai" / "hooks" / script).exists()
                                        for t in wr.tiers_upto(tier)), f"{rule}: {script} missing at {tier}")
        self.assertEqual(set(policy.ENFORCES) - seen, set(), "checks for rules that no _RULES.md declares")


class TestUpgradeTooling(Base):
    def test_upgrade_refreshes_tool_files_and_installs_hooks(self):
        ws = self.new("r1", "--quick")
        (ws / ".ai" / "policy.py").write_text("# stale", encoding="utf-8")
        subprocess.run(["git", "config", "--unset", "core.hooksPath"], cwd=ws)  # as a 0.1.0 workspace
        r = run_wr("upgrade", "--to", "task", "--path", str(ws))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ENFORCES", (ws / ".ai" / "policy.py").read_text(encoding="utf-8"))
        self.assertEqual(git(ws, "config", "core.hooksPath").strip(), ".githooks")
        self.assertIn("naming", json.loads((ws / ".workrealm.json").read_text())["checks"])
        done = subprocess.run([sys.executable, ".ai/checkpoint.py", "chore: upgrade to task tier",
                               "WorkRealm upgrade."], cwd=ws, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_upgrade_keeps_user_settings(self):
        ws = self.new("r2", "--quick")
        path = ws / ".claude" / "settings.json"
        settings = json.loads(path.read_text())
        settings["model"] = "opus"
        settings["statusLine"] = {"type": "command", "command": "my-line"}
        settings["permissions"]["deny"].append("Bash(rm -rf *)")
        path.write_text(json.dumps(settings))
        self.assertEqual(run_wr("upgrade", "--to", "project", "--path", str(ws)).returncode, 0)
        after = json.loads(path.read_text())
        self.assertEqual(after["model"], "opus")
        self.assertEqual(after["statusLine"]["command"], "my-line")
        self.assertIn("Bash(rm -rf *)", after["permissions"]["deny"])
        self.assertEqual(after["permissions"]["deny"].count("Read(./.env)"), 1)
        self.assertEqual(after["hooks"]["PreToolUse"][0]["matcher"], "Write|Edit|MultiEdit|NotebookEdit")


def helper(ws: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, ".ai/wr.py", *args], cwd=ws, capture_output=True, text=True)


class TestClaudeErgonomics(Base):
    def test_session_start_prints_state_and_status(self):
        ws = self.new("s1")
        out = run_hook(ws, "session_start.py", {"source": "startup"})
        self.assertEqual(out.returncode, 0)
        self.assertIn("tier task", out.stdout)
        self.assertIn("--- STATE.md ---", out.stdout)
        self.assertIn("Open items: 0", out.stdout)
        self.assertIn("compacted", run_hook(ws, "session_start.py", {"source": "compact"}).stdout)

    def test_statusline(self):
        ws = self.new("s2", "--project")
        (ws / "x.txt").write_text("x")
        r = subprocess.run([sys.executable, ".ai/statusline.py"], cwd=ws, input="{}", capture_output=True, text=True)
        self.assertEqual(r.stdout.strip(), "s2 [project] | main | 1 uncommitted | no remote")

    def test_bash_guard(self):
        ws = self.new("s3", "--project")
        write(ws / "references" / "spec.pdf", "x")
        write(ws / "experiments" / "2026-10-12-x" / "results" / "2026-10-12" / "out.txt", "1")
        cases = {
            "rm references/spec.pdf": 2,
            "Remove-Item references\\spec.pdf": 2,
            "sed -i s/a/b/ references/spec.pdf": 2,
            "echo x >> references/spec.pdf": 2,
            "git mv references/spec.pdf docs/notes/": 2,
            "rm -rf experiments/2026-10-12-x/results": 2,
            "cat references/spec.pdf > docs/notes/2026-10-12-spec.md": 0,
            "echo x >> references/SOURCES_LOG.md": 0,
            "curl -o references/inbox/new.pdf https://example.com/a.pdf": 0,
            "curl -o references/new.pdf https://example.com/a.pdf": 2,     # project tier: via the inbox
            "cp ~/Downloads/a.pdf references/a.pdf": 2,
            'git commit --no-verify -m "feat: x"': 2,
            'git commit -nm "feat: x"': 2,
            "git push -n origin main": 0,
            "git config core.hooksPath /dev/null": 2,
            "git status && ls references": 0,
        }
        for command, expected in cases.items():
            r = run_hook(ws, "bash_guard.py", {"tool_name": "Bash", "tool_input": {"command": command}})
            self.assertEqual(r.returncode, expected, f"{command}: {r.stderr}")

    def test_task_tier_saves_sources_directly(self):
        ws = self.new("s3b")
        r = run_hook(ws, "bash_guard.py", {"tool_name": "Bash",
                                           "tool_input": {"command": "curl -o references/new.pdf https://x/a.pdf"}})
        self.assertEqual(r.returncode, 0, r.stderr)
        r = run_hook(ws, "protect_paths.py", {"tool_name": "Write",
                                              "tool_input": {"file_path": str(ws / "references" / "new.md")}})
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_task_helpers_produce_what_the_checks_accept(self):
        ws = self.new("s4")
        self.assertEqual(helper(ws, "note", "Vendor options!").returncode, 0)
        self.assertEqual(len(list((ws / "docs" / "notes").glob("*-vendor-options.md"))), 1)
        local = self.tmp / "spec-v2.pdf"
        local.write_bytes(b"pdf")
        r = helper(ws, "source", "add", "https://example.com/spec-v2.pdf", "--desc", "Spec v2", "--file", str(local))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((ws / "references" / "spec-v2.pdf").exists())
        self.assertNotEqual(helper(ws, "source", "add", "https://x", "--desc", "d", "--file", str(local)).returncode, 0)
        self.assertEqual(helper(ws, "decide", "Use Postgres", "--alt", "SQLite -- no concurrent writers").returncode, 0)
        self.assertEqual(helper(ws, "decide", "Use MySQL", "--alt", "Postgres -- licence",
                                "--supersedes", "D1").returncode, 0)
        decisions = (ws / "docs" / "decisions" / "DECISIONS.md").read_text(encoding="utf-8")
        self.assertIn("| D2 |", decisions)
        self.assertEqual(len(re.findall(r"^\| D1 \|", decisions, re.M)), 1)
        self.assertEqual(helper(ws, "open-item", "Which vendor?", "--owner", "KH", "--trigger", "pilot").returncode, 0)
        self.assertEqual(helper(ws, "open-item", "Budget?", "--owner", "KH", "--trigger", "Q4").returncode, 0)
        self.assertEqual(helper(ws, "close-item", "O1", "Vendor A").returncode, 0)
        items = (ws / "docs" / "decisions" / "OPEN-ITEMS.md").read_text(encoding="utf-8")
        self.assertIn("| O1 | Which vendor? | Vendor A |", items.split("## Closed")[1])
        self.assertNotIn("Which vendor?", items.split("## Closed")[0])
        r = commit(ws, "docs: helpers", "Exercise every task helper.")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotEqual(helper(ws, "adr", "new", "x").returncode, 0)  # project tier only

    def test_project_helpers_produce_what_the_checks_accept(self):
        ws = self.new("s5", "--project")
        for args in (("plan", "new", "Pilot rollout"), ("adr", "new", "Storage backend"),
                     ("exp", "new", "Cache warmup")):
            self.assertEqual(helper(ws, *args).returncode, 0, args)
        self.assertTrue((ws / "docs" / "plans" / "pilot-rollout.md").exists())
        self.assertTrue((ws / "docs" / "decisions" / "adr" / "0001-storage-backend.md").exists())
        exp = next(p for p in (ws / "experiments").iterdir() if p.is_dir())
        self.assertRegex(exp.name, r"^\d{4}-\d{2}-\d{2}-cache-warmup$")
        self.assertNotEqual(helper(ws, "run", "new", "no-such-experiment").returncode, 0)
        for _ in range(2):
            self.assertEqual(helper(ws, "run", "new", exp.name).returncode, 0)
        runs = sorted(p.name for p in (exp / "results").iterdir())
        self.assertEqual(len(runs), 2)
        self.assertTrue(runs[1].endswith("-02"))
        r = commit(ws, "docs: scaffold work", "Exercise every project helper.")
        self.assertEqual(r.returncode, 0, r.stderr)
        write(exp / "results" / runs[0] / "README.md", "edited")  # README is append-to, allowed
        write(exp / "results" / runs[0] / "out.csv", "1")
        self.assertEqual(commit(ws, "test(cache): record run").returncode, 0)
        write(exp / "results" / runs[0] / "out.csv", "2")
        self.assertIn("R-EVIDENCE", commit(ws, "test(cache): fix numbers").stderr)
        subprocess.run(["git", "reset", "-q", "--hard"], cwd=ws)
        self.assertEqual(helper(ws, "release", "cut", "v0.1.0", "--include", "docs/decisions").returncode, 0)
        manifest = (ws / "releases" / "v0.1.0" / "MANIFEST.md").read_text(encoding="utf-8")
        self.assertIn("0001-storage-backend.md", manifest)
        self.assertNotEqual(helper(ws, "release", "cut", "v0.2.0", "--include", "src").returncode, 0)  # dirty
        r = commit(ws, "chore: release v0.1.0", "Hand-over to the pilot team.")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_inbox_then_promotion(self):
        ws = self.new("s5b", "--project")
        local = self.tmp / "datasheet.pdf"
        local.write_bytes(b"pdf")
        r = helper(ws, "source", "add", "https://vendor.example/ds.pdf", "--desc", "Datasheet rev C", "--file", str(local))
        self.assertEqual(r.returncode, 0, r.stderr)
        inbox = ws / "references" / "inbox" / "datasheet.pdf"
        self.assertTrue(inbox.exists())
        self.assertFalse((ws / "references" / "datasheet.pdf").exists())
        self.assertEqual(commit(ws, "docs: stage datasheet").returncode, 0)  # the inbox needs no log line
        self.assertIn("Inbox: 1", helper(ws, "status").stdout)
        direct = run_hook(ws, "protect_paths.py", {"tool_name": "Write",
                                                   "tool_input": {"file_path": str(ws / "references" / "x.pdf")}})
        self.assertEqual(direct.returncode, 2)
        self.assertIn("R-INBOX", direct.stderr)
        r = helper(ws, "source", "promote", "references/inbox/datasheet.pdf")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((ws / "references" / "datasheet.pdf").exists())
        self.assertFalse(inbox.exists())
        log = (ws / "references" / "SOURCES_LOG.md").read_text(encoding="utf-8")
        self.assertIn("https://vendor.example/ds.pdf — references/datasheet.pdf — Datasheet rev C", log)
        r = commit(ws, "docs: promote datasheet")
        self.assertEqual(r.returncode, 0, r.stderr)
        settings = json.loads((ws / ".claude" / "settings.json").read_text())
        self.assertIn("Bash(python .ai/wr.py source promote *)", settings["permissions"]["ask"])

    def test_every_skill_is_well_formed_and_calls_real_helpers(self):
        ws = self.new("s6", "--project")
        skills = sorted((ws / ".claude" / "skills").glob("*/SKILL.md"))
        self.assertEqual(len(skills), 10)
        for skill in skills:
            text = skill.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\nname: " + skill.parent.name + "\ndescription: "), skill)
            for cmd in set(re.findall(r"python \.ai/wr\.py ([a-z-]+(?: new| add| cut| promote)?)", text)):
                r = helper(ws, *cmd.split(), "--help")
                self.assertEqual(r.returncode, 0, f"{skill.parent.name}: {cmd}")


ROBOT = "\U0001F916 [AI]"


class TestAiMarking(Base):
    """Only a subagent's own work is marked; work done at the user's prompt is not."""

    def test_checkpoint_marks_subject_and_trailer(self):
        ws = self.new("m1", "--quick")
        write(ws / "a.txt", "x")
        r = subprocess.run([sys.executable, ".ai/checkpoint.py", "--agent", "researcher", "docs: add notes", "why"],
                           cwd=ws, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        msg = subprocess.run(["git", "log", "-1", "--format=%B"], cwd=ws, capture_output=True,
                             text=True, encoding="utf-8").stdout
        self.assertTrue(msg.startswith(f"docs: {ROBOT} add notes"), msg)
        self.assertIn("AI-Agent: researcher", msg)

    def test_tag_and_trailer_must_go_together(self):
        ws = self.new("m2", "--quick")
        write(ws / "a.txt", "x")
        self.assertIn("R-COMMIT", commit(ws, f"docs: {ROBOT} sneaky").stderr)
        self.assertIn("R-COMMIT", commit(ws, "docs: plain", "AI-Agent: researcher").stderr)
        self.assertEqual(commit(ws, f"docs: {ROBOT} marked", "Why.", "AI-Agent: researcher").returncode, 0)

    def test_bash_hook_marks_subagent_commits_only(self):
        ws = self.new("m3", "--quick")
        cmd = 'python .ai/checkpoint.py "docs: add notes" "why"'
        sub = run_hook(ws, "bash_guard.py", {"tool_name": "Bash", "agent_id": "a1", "agent_type": "researcher",
                                             "tool_input": {"command": cmd, "description": "commit"}})
        self.assertEqual(sub.returncode, 0, sub.stderr)
        out = json.loads(sub.stdout)["hookSpecificOutput"]
        self.assertEqual(out["updatedInput"]["command"],
                         'python .ai/checkpoint.py --agent researcher "docs: add notes" "why"')
        self.assertEqual(out["updatedInput"]["description"], "commit")
        main = run_hook(ws, "bash_guard.py", {"tool_name": "Bash", "tool_input": {"command": cmd}})
        self.assertEqual((main.returncode, main.stdout), (0, ""))
        forged = run_hook(ws, "bash_guard.py", {"tool_name": "Bash", "tool_input": {
            "command": 'python .ai/checkpoint.py --agent researcher "docs: x"'}})
        self.assertEqual(forged.returncode, 2)
        raw = run_hook(ws, "bash_guard.py", {"tool_name": "Bash", "agent_id": "a1", "agent_type": "researcher",
                                             "tool_input": {"command": 'git commit -m "docs: x"'}})
        self.assertEqual(raw.returncode, 2)
        chained = run_hook(ws, "bash_guard.py", {"tool_name": "Bash", "agent_id": "a1", "agent_type": "researcher",
                                                 "tool_input": {"command": cmd + " && rm -rf src"}})
        self.assertEqual(chained.returncode, 2)


REAL_BRAIN = Path(os.environ.get("AGENTBRAIN_PATH") or Path.home() / ".agentbrain")
AGENT_SRC = """---
name: {name}
role: {name} role
tiers: {tiers}
triggers:
  - "do {name}"
writes_to:
  - "docs/notes/"
never_touches:
  - "references/"
---

Body of {name}.
"""


@unittest.skipUnless((REAL_BRAIN / "scripts" / "sync_skills.py").exists(), "AgentBrain >= 2.4.0 not installed")
class TestBrainSync(Base):
    """A fixture brain with the real sync scripts, so the brain's own agents never shape results."""

    def setUp(self):
        super().setUp()
        self.brain = self.tmp / "brain"
        (self.brain / "scripts").mkdir(parents=True)
        for script in ("sync_agents.py", "sync_skills.py"):
            shutil.copy2(REAL_BRAIN / "scripts" / script, self.brain / "scripts" / script)
        (self.brain / "manifest.yaml").write_text('version: "9.1.0"\nmin_workrealm_version: "0.4.0"\n')
        self.agent("researcher", "[task, project]")
        self.agent("lab_runner", "[project]")
        write(self.brain / "skills" / "diagnose.md",
              "---\ndomain: engineering\ntype: skill\ntiers: [task, project]\n---\n# Diagnose\n\n"
              "## Context\nUse when something is broken.\n")
        self.env = {**os.environ, "AGENTBRAIN_PATH": str(self.brain)}

    def agent(self, name: str, tiers: str) -> Path:
        path = self.brain / "agents" / "work" / f"{name}.md"
        write(path, AGENT_SRC.format(name=name, tiers=tiers))
        return path

    def new_ws(self, name: str, *flags: str) -> Path:
        r = run_wr("new", name, "--dir", str(self.tmp), "--no-remote", *flags, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("AgentBrain 9.1.0 (", r.stdout)  # synced, not refused
        return self.tmp / name

    def test_new_syncs_per_tier_and_stamps_the_brain(self):
        ws = self.new_ws("b1")
        self.assertEqual(sorted(p.stem for p in (ws / ".claude" / "agents").glob("*.md")), ["researcher"])
        self.assertTrue((ws / ".claude" / "skills" / "diagnose" / "SKILL.md").exists())
        self.assertEqual(json.loads((ws / ".workrealm.json").read_text())["agentbrain_version"], "9.1.0")
        self.assertEqual(git(ws, "status", "--porcelain"), "")  # synced files are in the scaffold commit
        quick = self.new_ws("b2", "--quick")
        self.assertFalse((quick / ".claude" / "agents").exists())

    def test_upgrade_adds_project_agents(self):
        ws = self.new_ws("b3")
        r = run_wr("upgrade", "--to", "project", "--path", str(ws), env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((ws / ".claude" / "agents" / "lab_runner.md").exists())

    def test_sync_check_detects_drift_and_sync_prunes(self):
        ws = self.new_ws("b4")
        self.assertEqual(run_wr("sync", "--check", "--path", str(ws), env=self.env).returncode, 0)
        (self.brain / "agents" / "work" / "researcher.md").unlink()
        self.agent("reviewer", "[task]")
        self.assertNotEqual(run_wr("sync", "--check", "--path", str(ws), env=self.env).returncode, 0)
        self.assertEqual(run_wr("sync", "--path", str(ws), env=self.env).returncode, 0)
        self.assertEqual(sorted(p.stem for p in (ws / ".claude" / "agents").glob("*.md")), ["reviewer"])
        r = subprocess.run([sys.executable, ".ai/checkpoint.py", "chore: sync AgentBrain agents and skills"],
                           cwd=ws, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_brain_that_needs_a_newer_workrealm_is_refused(self):
        (self.brain / "manifest.yaml").write_text('version: "9.2.0"\nmin_workrealm_version: "99.0.0"\n')
        r = run_wr("new", "b5", "--dir", str(self.tmp), "--no-remote", env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)  # the workspace is still created
        self.assertIn("needs WorkRealm >= 99.0.0", r.stdout)
        self.assertFalse((self.tmp / "b5" / ".claude" / "agents").exists())


class TestNoBrain(Base):
    def test_missing_brain_warns_and_still_works(self):
        r = run_wr("new", "n1", "--dir", str(self.tmp), "--no-remote")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("AgentBrain not found", r.stdout)
        self.assertNotEqual(run_wr("sync", "--path", str(self.tmp / "n1")).returncode, 0)


def doctor(ws: Path, *flags: str) -> subprocess.CompletedProcess:
    return run_wr("doctor", "--path", str(ws), *flags)


def row(out: str, name: str) -> str:
    """The doctor line for one check, e.g. 'FAIL  git hooks  ...'."""
    return next((ln for ln in out.splitlines() if re.match(rf"^\w+\s+{re.escape(name)}\s", ln)), "")


class TestDoctor(Base):
    def test_fresh_workspace_is_healthy(self):
        ws = self.new("d1")
        r = doctor(ws)
        self.assertEqual(r.returncode, 0, r.stdout)
        for name in ("version", "tool files", "settings", "rules", "git hooks", "work tree", "secrets", "policy"):
            self.assertTrue(row(r.stdout, name).startswith("OK"), r.stdout)
        self.assertTrue(row(r.stdout, "remote").startswith("WARN"))  # task tier without a remote

    def test_missing_hooks_path_fails_and_fix_restores_it(self):
        ws = self.new("d2")
        git(ws, "config", "--unset", "core.hooksPath")
        r = doctor(ws)
        self.assertEqual(r.returncode, 1)
        self.assertTrue(row(r.stdout, "git hooks").startswith("FAIL"), r.stdout)
        self.assertEqual(doctor(ws, "--ci").returncode, 0)  # a CI checkout never has it; not checked there
        fixed = doctor(ws, "--fix")
        self.assertTrue(row(fixed.stdout, "git hooks").startswith("FIXED"), fixed.stdout)
        self.assertEqual(git(ws, "config", "core.hooksPath").strip(), ".githooks")
        self.assertEqual(doctor(ws).returncode, 0)

    def test_tracked_virtualenvs_build_output_and_large_files_are_reported(self):
        ws = self.new("d8")
        self.assertTrue(row(doctor(ws).stdout, "hygiene").startswith("OK"))
        write(ws / ".venv" / "pyvenv.cfg", "home = /usr/bin\n")
        write(ws / ".venv" / "lib" / "site.py", "x\n")
        write(ws / "web" / "node_modules" / "left-pad" / "index.js", "x\n")
        write(ws / "src" / "mod.cpython-312.pyc", "x")
        (ws / "big.bin").write_bytes(b"\0" * (11 * 1024 * 1024))
        subprocess.run(["git", "add", "-Af"], cwd=ws, capture_output=True)
        subprocess.run(["git", "commit", "-q", "--no-verify", "-m", "chore: everything"], cwd=ws)
        r = doctor(ws, "--fix")
        self.assertEqual(r.returncode, 0, r.stdout)
        report = r.stdout.split("hygiene", 1)[1].split("\nOK", 1)[0]
        for expected in (".venv/ (a virtualenv), 2 file(s)", "web/node_modules/ (build output)", "*.pyc",
                         "big.bin (11 MB)", "git rm -r --cached"):
            self.assertIn(expected, report)
        self.assertNotIn("site.py", report)
        self.assertIn(".venv/lib/site.py", git(ws, "ls-files"))  # reported, never removed

    def test_another_tools_hooks_path_is_reported_never_taken_over(self):
        ws = self.new("d7")
        write(ws / ".husky" / "pre-commit", "#!/bin/sh\nnpm test\n")
        git(ws, "config", "core.hooksPath", ".husky")
        fixed = doctor(ws, "--fix")
        self.assertEqual(fixed.returncode, 1)
        self.assertIn("another tool's", row(fixed.stdout, "git hooks"))
        self.assertEqual(git(ws, "config", "core.hooksPath").strip(), ".husky")
        write(ws / ".husky" / "pre-commit", '#!/bin/sh\nnpm test\n.githooks/pre-commit "$@"\n')
        write(ws / ".husky" / "commit-msg", '#!/bin/sh\n.githooks/commit-msg "$@"\n')
        self.assertTrue(row(doctor(ws).stdout, "git hooks").startswith("OK"))

    def test_tool_drift_settings_and_rules_are_repaired(self):
        ws = self.new("d3", "--project")
        original = (ws / ".ai" / "policy.py").read_text(encoding="utf-8")
        (ws / ".ai" / "policy.py").write_text("# weakened", encoding="utf-8")
        (ws / ".githooks" / "commit-msg").unlink()
        settings = json.loads((ws / ".claude" / "settings.json").read_text())
        del settings["hooks"]["Stop"]
        settings["model"] = "opus"
        (ws / ".claude" / "settings.json").write_text(json.dumps(settings))
        agents = ws / "AGENTS.md"
        agents.write_text(agents.read_text(encoding="utf-8").replace("## Context first", "## Context whenever")
                          + "\n- my rule\n", encoding="utf-8")
        r = doctor(ws)
        for name in ("tool files", "settings", "rules"):
            self.assertTrue(row(r.stdout, name).startswith("WARN"), r.stdout)
        doctor(ws, "--fix")
        self.assertEqual((ws / ".ai" / "policy.py").read_text(encoding="utf-8"), original)
        self.assertTrue((ws / ".githooks" / "commit-msg").exists())
        after = json.loads((ws / ".claude" / "settings.json").read_text())
        self.assertIn("Stop", after["hooks"])
        self.assertEqual(after["model"], "opus")
        text = agents.read_text(encoding="utf-8")
        self.assertIn("## Context first", text)
        self.assertIn("- my rule", text)
        self.assertEqual(doctor(ws, "--ci").returncode, 0)

    def test_tracked_secrets_fail_and_are_not_auto_fixed(self):
        ws = self.new("d4", "--quick")
        write(ws / ".mcp.json", '{"mcpServers": {"jira": {"env": {"JIRA_API_TOKEN": "abcd1234efgh5678"}}}}')
        subprocess.run(["git", "add", "-A"], cwd=ws)
        subprocess.run(["git", "commit", "-q", "--no-verify", "-m", "chore: mcp"], cwd=ws)
        r = doctor(ws, "--fix")
        self.assertEqual(r.returncode, 1)
        self.assertIn(".mcp.json", row(r.stdout, "secrets"))
        self.assertIn("ROTATE", row(r.stdout, "secrets"))
        write(ws / ".mcp.json", '{"mcpServers": {"jira": {"env": {"JIRA_API_TOKEN": "${JIRA_API_TOKEN}"}}}}')
        subprocess.run(["git", "commit", "-qam", "fix: token from the environment"], cwd=ws)
        self.assertTrue(row(doctor(ws).stdout, "secrets").startswith("OK"))

    def test_upstream_missing_is_pushed_by_fix(self):
        ws = self.new("d5")
        remote = self.tmp / "remote.git"
        subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
        git(ws, "remote", "add", "origin", str(remote))
        r = doctor(ws)
        self.assertTrue(row(r.stdout, "remote").startswith("WARN"), r.stdout)
        fixed = doctor(ws, "--fix")
        self.assertTrue(row(fixed.stdout, "remote").startswith("FIXED"), fixed.stdout)
        self.assertTrue(row(doctor(ws).stdout, "remote").startswith("OK"))

    def test_a_failed_automatic_push_is_kept_and_shown_until_a_push_lands(self):
        ws = self.new("d5b")
        remote = self.tmp / "later.git"                      # not there yet: the push fails
        git(ws, "remote", "add", "origin", str(remote))
        write(ws / "a.txt", "x")
        self.assertEqual(commit(ws, "feat: a").returncode, 0)
        log = ws / ".git" / "workrealm-push.log"
        for _ in range(100):                                 # the hook pushes in the background
            if log.exists() and log.read_text(encoding="utf-8").strip():
                break
            time.sleep(0.1)
        self.assertIn("failed", log.read_text(encoding="utf-8"))
        self.assertIn("LAST PUSH FAILED", helper(ws, "status").stdout)
        self.assertIn("last automatic push failed", row(doctor(ws).stdout, "remote"))
        subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
        self.assertTrue(row(doctor(ws, "--fix").stdout, "remote").startswith("FIXED"))
        self.assertFalse(log.exists())
        self.assertNotIn("LAST PUSH FAILED", helper(ws, "status").stdout)

    def test_existing_violations_are_reported_not_blocking(self):
        ws = self.new("d6")
        write(ws / "docs" / "notes" / "Random.md", "x")
        subprocess.run(["git", "add", "-A"], cwd=ws)
        subprocess.run(["git", "commit", "-q", "--no-verify", "-m", "docs: random"], cwd=ws)
        r = doctor(ws)
        self.assertEqual(r.returncode, 0)
        self.assertTrue(row(r.stdout, "policy").startswith("WARN"))
        self.assertIn("Random.md", r.stdout)


def fixture_code_repo(root: Path) -> Path:
    """A typical code repository with its own rules files and an ignored build folder."""
    repo = root / "service"
    write(repo / "README.md", "# Service\n")
    write(repo / "src" / "app.py", "print('hi')\n")
    write(repo / "tests" / "test_app.py", "def test_ok():\n    assert True\n")
    write(repo / "AGENTS.md", "# Team rules\n\n- Format with black.\n")
    write(repo / "CLAUDE.md", "Be terse.\n")
    write(repo / ".gitignore", "dist/\n")
    write(repo / "dist" / "bundle.js", "built")
    for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-q", "-m", "initial"]):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
    return repo


def fixture_research_folder(root: Path) -> Path:
    """A folder with no Git, its own names, undated notes and old-style ADRs."""
    folder = root / "study"
    for name in ("ideas.md", "meeting.md", "todo.md"):
        write(folder / "notes" / name, f"# {name}\n")
    write(folder / "literature" / "paper.pdf", "pdf")
    write(folder / "decisions" / "ADR-001-database.md", "# ADR-001\n\n## Decision\n\nPostgres.\n")
    write(folder / "decisions" / "ADR-002-queue.md", "# ADR-002\n\n## Decision\n\nRabbitMQ.\n")
    write(folder / "dist" / "v1" / "report.pdf", "r1")
    write(folder / "old" / "stale.md", "old\n")
    write(folder / "scratch" / "misc.txt", "misc\n")
    return folder


def snapshot(folder: Path) -> dict[str, bytes]:
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob("*")
            if p.is_file() and ".git" not in p.relative_to(folder).parts}


class TestAdopt(Base):
    def test_dry_run_writes_nothing(self):
        repo = fixture_code_repo(self.tmp)
        before = snapshot(repo)
        r = run_wr("adopt", str(repo), "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Dry run", r.stdout)
        self.assertEqual(snapshot(repo), before)
        self.assertEqual(git(repo, "status", "--porcelain"), "")

    def test_code_repo_moves_nothing_and_keeps_its_rules(self):
        repo = fixture_code_repo(self.tmp)
        before = snapshot(repo)
        r = run_wr("adopt", str(repo))
        self.assertEqual(r.returncode, 0, r.stderr)
        after = snapshot(repo)
        for rel in ("README.md", "src/app.py", "tests/test_app.py", "dist/bundle.js"):
            self.assertEqual(after[rel], before[rel], rel)          # nothing moved or rewritten
        self.assertTrue(after[".gitignore"].startswith(before[".gitignore"]))
        agents = (repo / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("workrealm:rules:start", agents)
        self.assertIn("- Format with black.", agents.split("## Project-specific rules")[1])
        claude = (repo / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertTrue(claude.startswith("@AGENTS.md"))
        self.assertIn("Be terse.", claude)
        meta = json.loads((repo / ".workrealm.json").read_text())
        self.assertEqual(meta["layout"]["src"], "src")
        self.assertNotEqual(meta["layout"]["releases"], "dist")      # ignored build output is not a role
        self.assertEqual(git(repo, "config", "core.hooksPath").strip(), ".githooks")
        done = subprocess.run([sys.executable, ".ai/checkpoint.py", "chore: adopt WorkRealm", "Rules and checks."],
                              cwd=repo, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(doctor(repo).returncode, 0)
        self.assertNotEqual(run_wr("adopt", str(repo)).returncode, 0)  # already a workspace

    def test_another_tools_files_stop_adopt_before_anything_is_written(self):
        repo = fixture_code_repo(self.tmp)
        write(repo / ".ai" / "policy.py", "# another tool's policy\n")
        write(repo / ".githooks" / "pre-commit", "#!/bin/sh\nnpm test\n")
        for args in (["add", "-A"], ["commit", "-q", "-m", "chore: tooling"]):
            subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
        before = snapshot(repo)
        dry = run_wr("adopt", str(repo), "--dry-run")
        self.assertIn("! .ai/policy.py", dry.stdout)
        self.assertIn("! .githooks/pre-commit", dry.stdout)
        r = run_wr("adopt", str(repo))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Nothing was written", r.stderr)
        self.assertEqual(snapshot(repo), before)
        self.assertEqual(git(repo, "status", "--porcelain"), "")
        self.assertEqual(git(repo, "config", "core.hooksPath").strip(), "")

    def test_the_repositorys_own_git_hooks_keep_running(self):
        repo = fixture_code_repo(self.tmp)
        hooks = repo / ".git" / "hooks"
        write(hooks / "pre-commit", '#!/bin/sh\ntouch "$(git rev-parse --git-dir)/own-pre-commit-ran"\n')
        write(hooks / "pre-push", "#!/bin/sh\nexit 0\n")
        for h in ("pre-commit", "pre-push"):
            (hooks / h).chmod(0o755)
        r = run_wr("adopt", str(repo))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(".git/hooks/pre-commit keeps running", r.stdout)
        self.assertIn("+ .githooks/pre-push", r.stdout)
        self.assertIn("hooks/pre-push", (repo / ".githooks" / "pre-push").read_text(encoding="utf-8"))
        done = subprocess.run([sys.executable, ".ai/checkpoint.py", "chore: adopt WorkRealm", "Rules and checks."],
                              cwd=repo, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue((repo / ".git" / "own-pre-commit-ran").exists())

    def test_build_output_is_reported_in_a_repo_and_ignored_in_a_new_baseline(self):
        repo = fixture_code_repo(self.tmp)
        write(repo / "node_modules" / "x" / "index.js", "x\n")
        for args in (["add", "-A"], ["commit", "-q", "-m", "chore: deps"]):
            subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
        self.assertIn("node_modules/ (build output)", run_wr("adopt", str(repo), "--dry-run").stdout)

        folder = fixture_research_folder(self.tmp)
        write(folder / "analysis" / ".venv" / "pyvenv.cfg", "home = /usr/bin\n")
        write(folder / "analysis" / ".venv" / "lib" / "site.py", "x\n")
        write(folder / "analysis" / "build" / "out.o", "x")
        r = run_wr("adopt", str(folder))
        self.assertEqual(r.returncode, 0, r.stderr)
        ignore = (folder / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("analysis/.venv/", ignore)
        self.assertIn("analysis/build/", ignore)
        baseline = git(folder, "ls-files")
        self.assertNotIn(".venv", baseline)
        self.assertNotIn("out.o", baseline)
        self.assertIn("scratch/misc.txt", baseline)

    def test_dirty_repo_is_refused(self):
        repo = fixture_code_repo(self.tmp)
        write(repo / "src" / "wip.py", "x")
        self.assertNotEqual(run_wr("adopt", str(repo)).returncode, 0)

    def test_research_folder_keeps_its_names_and_conventions(self):
        folder = fixture_research_folder(self.tmp)
        r = run_wr("adopt", str(folder), "--tier", "project")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("baseline before adopting", git(folder, "log", "--oneline"))
        self.assertIn("scratch/", r.stdout)                            # reported, not touched
        meta = json.loads((folder / ".workrealm.json").read_text())
        lay = meta["layout"]
        self.assertEqual((lay["notes"], lay["sources"], lay["decisions"], lay["adr"], lay["releases"], lay["archive"]),
                         ("notes", "literature", "decisions", "decisions", "dist", "old"))
        self.assertIn("notes", meta["naming_relaxed"])
        self.assertIn("releases", meta["naming_relaxed"])              # dist/v1 is not v1.2.0
        self.assertEqual(meta["naming_overrides"]["adr"]["example"], "ADR-001-title.md")
        agents = (folder / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("`literature/`", agents)                         # the rules name the real folders
        self.assertNotIn("`references/`", agents)
        self.assertTrue((folder / "decisions" / "DECISIONS.md").exists())
        self.assertTrue((folder / "literature" / "inbox" / "README.md").exists())
        done = subprocess.run([sys.executable, ".ai/checkpoint.py", "chore: adopt WorkRealm", "Rules and checks."],
                              cwd=folder, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)

        write(folder / "literature" / "paper.pdf", "edited")
        self.assertIn("R-SOURCES", commit(folder, "docs: tweak paper").stderr)
        subprocess.run(["git", "reset", "-q", "--hard"], cwd=folder)
        write(folder / "notes" / "Loose Thoughts.md", "x")             # notes naming relaxed
        self.assertEqual(commit(folder, "docs: thoughts").returncode, 0)
        write(folder / "decisions" / "ADR-001-database.md",            # a legacy ADR may be edited
              "# ADR-001\n\n## Decision\n\nPostgres 16.\n")
        self.assertEqual(commit(folder, "docs: adr", "Version pinned.").returncode, 0)
        r = helper(folder, "adr", "new", "Cache layer")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((folder / "decisions" / "ADR-003-cache-layer.md").exists())
        self.assertEqual(commit(folder, "docs: adr cache", "Needs an argued decision.").returncode, 0)
        write(folder / "decisions" / "0004-other.md", (folder / "decisions" / "ADR-003-cache-layer.md").read_text())
        self.assertIn("R-PLACE", commit(folder, "docs: adr", "why").stderr)  # the folder's own style holds

    def test_upgrade_keeps_an_adopted_layout(self):
        folder = fixture_research_folder(self.tmp)
        self.assertEqual(run_wr("adopt", str(folder), "--tier", "task").returncode, 0)
        subprocess.run([sys.executable, ".ai/checkpoint.py", "chore: adopt", "x"], cwd=folder, capture_output=True)
        r = run_wr("upgrade", "--to", "project", "--path", str(folder))
        self.assertEqual(r.returncode, 0, r.stderr)
        meta = json.loads((folder / ".workrealm.json").read_text())
        self.assertEqual(meta["layout"]["sources"], "literature")
        self.assertIn("!literature/inbox", meta["protected"])
        self.assertFalse((folder / "references").exists())
        self.assertFalse((folder / "docs" / "notes").exists())


def checkpoint(ws: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, ".ai/checkpoint.py", *args], cwd=ws, capture_output=True, text=True)


class TestIntegrations(Base):
    def test_new_with_writes_mcp_entries_and_env_example(self):
        ws = self.new("i1", "--with", "github,rag")
        mcp = json.loads((ws / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]
        self.assertEqual(mcp["github"]["type"], "http")
        self.assertEqual(mcp["github"]["headers"]["Authorization"], "Bearer ${GITHUB_PAT}")
        self.assertEqual(mcp["agentbrain-rag"]["type"], "stdio")
        self.assertIn("rag_server.py", " ".join(mcp["agentbrain-rag"]["args"]))
        self.assertIn("GITHUB_PAT=", (ws / ".env.example").read_text(encoding="utf-8"))
        meta = json.loads((ws / ".workrealm.json").read_text())
        self.assertEqual(meta["integrations"], ["github", "rag"])
        self.assertEqual(git(ws, "status", "--porcelain"), "")  # committed with the scaffold
        r = run_wr("new", "i2", "--dir", str(self.tmp), "--no-remote", "--with", "jira")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unknown integration", r.stderr)

    def test_integrate_keeps_other_servers_and_doctor_restores_entries(self):
        ws = self.new("i3", "--quick")
        mine = {"mcpServers": {"mine": {"type": "stdio", "command": "x"}}, "extra": 1}
        write(ws / ".mcp.json", json.dumps(mine))
        r = run_wr("integrate", "rag", "--path", str(ws))
        self.assertEqual(r.returncode, 0, r.stderr)
        r = run_wr("integrate", "github", "--path", str(ws))
        data = json.loads((ws / ".mcp.json").read_text(encoding="utf-8"))
        self.assertEqual(set(data["mcpServers"]), {"mine", "agentbrain-rag", "github"})
        self.assertEqual(data["extra"], 1)
        self.assertEqual(json.loads((ws / ".workrealm.json").read_text())["integrations"], ["github", "rag"])
        del data["mcpServers"]["github"]
        write(ws / ".mcp.json", json.dumps(data))
        env = {k: v for k, v in NO_BRAIN.items() if k != "GITHUB_PAT"}
        out = run_wr("doctor", "--path", str(ws), env=env).stdout
        self.assertIn("WARN  integrations", out)
        self.assertIn("GITHUB_PAT not set", out)
        self.assertIn("no AgentBrain RAG server", out)
        run_wr("doctor", "--path", str(ws), "--fix", env=env)
        data = json.loads((ws / ".mcp.json").read_text(encoding="utf-8"))
        self.assertIn("github", data["mcpServers"])
        self.assertIn("mine", data["mcpServers"])
        ci = run_wr("doctor", "--path", str(ws), "--ci", env=env).stdout
        self.assertNotIn("GITHUB_PAT", ci)  # credentials are local state

    def test_literal_token_in_mcp_json_is_refused(self):
        ws = self.new("i4", "--quick", "--with", "github")
        path = ws / ".mcp.json"
        write(path, path.read_text(encoding="utf-8").replace("${GITHUB_PAT}", "ghp_" + "a1" * 18))
        r = commit(ws, "chore: pin token")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("R-SECRETS", r.stderr)
        subprocess.run(["git", "commit", "-q", "--no-verify", "-m", "chore: pin token"], cwd=ws)
        self.assertIn("FAIL  secrets", run_wr("doctor", "--path", str(ws), "--ci").stdout)

    def test_rag_launcher_finds_agentbrain_and_runs_in_the_workspace(self):
        ws = self.new("i5", "--quick", "--with", "rag")
        launcher = [sys.executable, str(ws / ".ai" / "rag_server.py")]
        env = {**os.environ, "AGENTBRAIN_PATH": str(self.tmp / "nobrain"), "CLAUDE_PROJECT_DIR": str(ws)}
        r = subprocess.run(launcher, capture_output=True, text=True, env=env, cwd=self.tmp)
        self.assertEqual(r.returncode, 1)
        self.assertIn("no AgentBrain RAG server", r.stderr)
        brain = self.tmp / "brain"
        write(brain / "scripts" / "rag" / "mcp_server.py", "import os\nprint(os.getcwd())\n")
        env["AGENTBRAIN_PATH"] = str(brain)
        r = subprocess.run(launcher, capture_output=True, text=True, env=env, cwd=self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(Path(r.stdout.strip()).resolve(), ws.resolve())


class TestTicket(Base):
    def test_workspace_for_a_ticket(self):
        ws = self.new("k1", "--ticket", "ABC-12")
        self.assertEqual(json.loads((ws / ".workrealm.json").read_text())["ticket"], "ABC-12")
        self.assertIn("- **Ticket:** ABC-12", (ws / "STATE.md").read_text(encoding="utf-8"))
        self.assertIn("Refs: ABC-12", git(ws, "log", "-1", "--format=%B"))
        write(ws / "a.txt", "x")
        self.assertEqual(checkpoint(ws, "feat: add a", "First piece.").returncode, 0)
        self.assertIn("First piece.\n\nRefs: ABC-12", git(ws, "log", "-1", "--format=%B"))
        write(ws / "b.txt", "x")
        r = commit(ws, "feat: add b")
        self.assertEqual(r.returncode, 0, r.stderr)  # a warning, never a block
        self.assertIn("R-TICKET", r.stderr)
        write(ws / "c.txt", "x")
        self.assertNotIn("R-TICKET", commit(ws, "feat: add c", "Refs: ABC-12").stderr)
        r = run_wr("new", "k2", "--dir", str(self.tmp), "--no-remote", "--ticket", "abc12")
        self.assertNotEqual(r.returncode, 0)

    def test_ticket_branch_names_the_key_and_commits_reference_it(self):
        ws = self.new("k3", "--quick")
        r = helper(ws, "ticket", "start", "XY-7", "Cache warm-up", "--type", "fix")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(git(ws, "branch", "--show-current").strip(), "fix/XY-7-cache-warm-up")
        self.assertIn("Ticket: XY-7", helper(ws, "status").stdout)
        write(ws / "a.txt", "x")
        self.assertEqual(checkpoint(ws, "fix: warm the cache").returncode, 0)
        self.assertIn("Refs: XY-7", git(ws, "log", "-1", "--format=%B"))
        subprocess.run(["git", "switch", "-q", "main"], cwd=ws)
        self.assertNotEqual(helper(ws, "ticket", "start", "XY-7", "Cache warm-up", "--type", "fix").returncode, 0)
        self.assertNotEqual(helper(ws, "ticket", "start", "not-a-key").returncode, 0)
        write(ws / "b.txt", "x")
        self.assertNotIn("R-TICKET", commit(ws, "feat: no ticket here").stderr)


def stage_blob(ws: Path, path: str) -> None:
    """Stage a path the local file system could not hold (CON, a trailing dot, a case twin)."""
    sha = subprocess.run(["git", "hash-object", "-w", "--stdin"], cwd=ws, input="x", capture_output=True,
                         text=True).stdout.strip()
    subprocess.run(["git", "-c", "core.protectNTFS=false", "update-index", "--add", "--cacheinfo", f"100644,{sha},{path}"], cwd=ws, check=True)


def plain_commit(ws: Path, message: str) -> subprocess.CompletedProcess:
    """`git commit` of what is staged, without adding the work tree."""
    return subprocess.run(["git", "commit", "-q", "-m", message], cwd=ws, capture_output=True, text=True)


class TestNames(Base):
    def test_names_that_break_a_checkout_are_refused(self):
        ws = self.new("n1", "--quick")
        write(ws / "notes-a.md", "x")
        self.assertEqual(commit(ws, "docs: a").returncode, 0)
        for bad in ("CON.txt", "docs/aux.md", "report.", "what?.md", "Notes-A.md", "d/" + "x" * 200 + ".md"):
            stage_blob(ws, bad)
            r = plain_commit(ws, "docs: bad name")
            self.assertNotEqual(r.returncode, 0, bad)
            self.assertIn("R-NAMES", r.stderr, bad)
            subprocess.run(["git", "-c", "core.protectNTFS=false", "rm", "-q", "--cached", bad], cwd=ws, check=True)
        write(ws / "console-log.md", "x")                      # only the exact reserved names
        self.assertEqual(commit(ws, "docs: log").returncode, 0)

    def test_non_ascii_and_spaces_warn_with_the_ascii_name(self):
        ws = self.new("n2", "--quick")
        write(ws / "Izvješće o đaku.md", "x")
        write(ws / "src" / "data loader.py", "x")
        r = commit(ws, "docs: draft")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("R-NAMES", r.stderr)
        self.assertIn("Izvjesce-o-daku.md", r.stderr)
        self.assertIn("src/data_loader.py", r.stderr)          # Python takes snake_case

    def test_branch_outside_the_convention_warns(self):
        ws = self.new("n3", "--quick")
        subprocess.run(["git", "switch", "-q", "-c", "ai/thing"], cwd=ws)
        write(ws / "a.txt", "x")
        self.assertIn("R-NAMES", commit(ws, "feat: a").stderr)
        subprocess.run(["git", "branch", "-m", "feat/thing"], cwd=ws)
        write(ws / "b.txt", "x")
        self.assertNotIn("R-NAMES", commit(ws, "feat: b").stderr)

    def test_names_fix_renames_and_keeps_evidence(self):
        ws = self.new("n4")
        write(ws / "references" / "Norma č.pdf", "x")
        log = ws / "references" / "SOURCES_LOG.md"
        write(log, log.read_text(encoding="utf-8") + "2026-10-26 — https://x — references/Norma č.pdf — norm\n")
        write(ws / "docs" / "notes" / "2026-10-26-sastanak.md", "See Bilješke sastanka.md.\n")
        write(ws / "Bilješke sastanka.md", "x")
        self.assertEqual(commit(ws, "docs: material").returncode, 0)
        write(ws / "src" / "data loader.py", "x")              # not yet tracked
        r = helper(ws, "names")
        self.assertIn("rename   Bilje", r.stdout)
        self.assertIn("keep     references/Norma", r.stdout)
        self.assertTrue((ws / "Bilješke sastanka.md").exists())    # a listing changes nothing
        r = helper(ws, "names", "--fix")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((ws / "Biljeske-sastanka.md").exists())
        self.assertTrue((ws / "src" / "data_loader.py").exists())
        self.assertTrue((ws / "references" / "Norma č.pdf").exists())
        self.assertIn("still named in: docs/notes/2026-10-26-sastanak.md", r.stdout)
        self.assertIn("R  ", git(ws, "status", "--porcelain"))           # tracked files moved with git mv
        self.assertEqual(commit(ws, "chore: ascii names").returncode, 0)
        self.assertIn("keep", helper(ws, "names").stdout)

    def test_style_renames_documents_and_rewrites_every_link(self):
        ws = self.new("n7", "--quick")
        write(ws / "notes" / "10_project" / "thesis_plan.md",
              "---\naliases:\n  - EN 1\n---\nSee [[ops_log]] and [[10_project/thesis_plan|plan]].\n")
        write(ws / "notes" / "ops_log.md", "Back to [[thesis_plan#Goal]], ![[fig_01.png]], "
              "[x](10_project/thesis_plan.md), `notes/ops_log.md`, [[EN 1]], [[missing_note]].\n")
        write(ws / "notes" / "fig_01.png", "png")
        write(ws / "notes" / "README.md", "Start at [[ops_log]].\n")
        write(ws / "notes" / "overview.canvas", '{"nodes": [{"file": "notes/10_project/thesis_plan.md"}]}\n')
        write(ws / "notes" / "card_tools" / "make_cards.py", "SRC = 'notes/ops_log.md'\n")
        write(ws / "notes" / "99_inbox" / "new_idea.md", "x\n")
        write(ws / "src" / "data_loader.py", "x\n")
        (ws / "run.ps1").write_bytes(b"Get-Content notes/ops_log.md\r\n")
        self.assertEqual(commit(ws, "docs: vault").returncode, 0)
        r = helper(ws, "names", "notes", "--style", "--rewrite-refs", "--keep", "notes/99_inbox")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("rename   notes/10_project/thesis_plan.md -> notes/10-project/thesis-plan.md", r.stdout)
        self.assertIn("would be rewritten", r.stdout)
        self.assertNotIn("src/", r.stdout)                                  # outside the scope
        self.assertNotIn("rename   notes/card_tools", r.stdout)             # code keeps its style
        self.assertTrue((ws / "notes" / "ops_log.md").exists())             # a listing changes nothing
        r = helper(ws, "names", "notes", "--style", "--rewrite-refs", "--keep", "notes/99_inbox", "--fix")
        self.assertEqual(r.returncode, 0, r.stderr)
        for kept in ("notes/README.md", "notes/card_tools/make_cards.py", "src/data_loader.py"):
            self.assertTrue((ws / kept).exists(), kept)
        self.assertTrue((ws / "notes" / "99_inbox" / "new-idea.md").exists())
        self.assertTrue((ws / "notes" / "fig-01.png").exists())
        log = (ws / "notes" / "ops-log.md").read_text(encoding="utf-8")
        for link in ("[[thesis-plan#Goal]]", "![[fig-01.png]]", "[x](10-project/thesis-plan.md)",
                     "`notes/ops-log.md`", "[[EN 1]]", "[[missing_note]]"):
            self.assertIn(link, log)
        plan = (ws / "notes" / "10-project" / "thesis-plan.md").read_text(encoding="utf-8")
        self.assertIn("[[ops-log]] and [[10-project/thesis-plan|plan]]", plan)
        self.assertIn("notes/10-project/thesis-plan.md", (ws / "notes" / "overview.canvas").read_text())
        self.assertIn("notes/ops-log.md", (ws / "notes" / "card_tools" / "make_cards.py").read_text())
        self.assertIn(b"notes/ops-log.md\r\n", (ws / "run.ps1").read_bytes())  # CRLF kept
        self.assertEqual(commit(ws, "docs: default names").returncode, 0)

    def test_rewrite_refs_refuses_a_rename_that_breaks_a_link(self):
        ws = self.new("n8")
        write(ws / "references" / "reading_list.md", "Start with [[my_note]].\n")  # write-once: not rewritten
        write(ws / "docs" / "my_note.md", "x\n")
        subprocess.run(["git", "add", "-A"], cwd=ws)
        subprocess.run(["git", "commit", "-q", "--no-verify", "-m", "docs: notes"], cwd=ws, check=True)
        r = helper(ws, "names", "docs", "--style", "--rewrite-refs", "--fix")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("broken   references/reading_list.md: [[my_note]]", r.stdout)
        self.assertTrue((ws / "docs" / "my_note.md").exists())               # nothing renamed
        r = helper(ws, "names", "docs", "--style", "--rewrite-refs", "--fix", "--force")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((ws / "docs" / "my-note.md").exists())

    def test_received_files_get_standard_names_and_keep_the_original_in_the_log(self):
        ws = self.new("n5")
        local = self.tmp / "Izvješće o stanju 2024.PDF"
        local.write_bytes(b"pdf")
        r = helper(ws, "source", "add", "https://x/r.pdf", "--desc", "Status report", "--file", str(local))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((ws / "references" / "izvjesce-o-stanju-2024.pdf").exists())
        log = (ws / "references" / "SOURCES_LOG.md").read_text(encoding="utf-8")
        self.assertIn("Status report (received as 'Izvješće o stanju 2024.PDF')", log)
        r = commit(ws, "docs: add report")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("R-NAMES", r.stderr)
        self.assertEqual(helper(ws, "note", "Čvorište Đakovo").returncode, 0)
        self.assertEqual(len(list((ws / "docs" / "notes").glob("*-cvoriste-dakovo.md"))), 1)

        ws = self.new("n6", "--project")
        write(ws / "references" / "inbox" / "Datasheet V2.PDF", "pdf")  # dropped in by hand
        r = helper(ws, "source", "promote", "references/inbox/Datasheet V2.PDF", "--desc", "Datasheet")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((ws / "references" / "datasheet-v2.pdf").exists())
        self.assertIn("Datasheet (received as 'Datasheet V2.PDF')",
                      (ws / "references" / "SOURCES_LOG.md").read_text(encoding="utf-8"))

    def test_every_workspace_gets_an_editorconfig_and_a_users_own_is_kept(self):
        ws = self.new("n7", "--quick")
        self.assertIn("indent_size = 4", (ws / ".editorconfig").read_text(encoding="utf-8"))
        write(ws / ".editorconfig", "root = true\n")
        self.assertEqual(commit(ws, "chore: own editorconfig").returncode, 0)
        self.assertEqual(run_wr("upgrade", "--to", "task", "--path", str(ws)).returncode, 0)
        self.assertEqual((ws / ".editorconfig").read_text(encoding="utf-8"), "root = true\n")


class TestTemplate(Base):
    def use_template(self, template: Path, name: str) -> Path:
        """What GitHub's "Use this template" does: the tracked files, one "Initial commit", no hooks."""
        import tarfile
        archive = self.tmp / f"{name}.tar"
        subprocess.run(["git", "archive", "--format=tar", "-o", str(archive), "HEAD"], cwd=template, check=True)
        repo = self.tmp / name
        with tarfile.open(archive) as tar:
            tar.extractall(repo)
        for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-q", "-m", "Initial commit"]):
            subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
        return repo

    def test_a_workspace_from_a_github_template_needs_only_init(self):
        tpl = self.new("task-template", "--template")
        self.assertTrue(json.loads((tpl / ".workrealm.json").read_text())["template"])
        self.assertNotIn("Made from the template", helper(tpl, "status").stdout)  # the template itself

        ws = self.use_template(tpl, "acme-report")
        ci = subprocess.run([sys.executable, ".ai/policy.py", "ci", "--before", "0" * 40], cwd=ws,
                            capture_output=True, text=True)
        self.assertEqual(ci.returncode, 0, ci.stderr)                    # GitHub's own first commit passes
        self.assertIn("Made from the template 'task-template'", helper(ws, "status").stdout)

        r = helper(ws, "init")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(git(ws, "config", "core.hooksPath").strip(), ".githooks")
        self.assertEqual(git(ws, "status", "--porcelain"), "")
        self.assertIn("chore: start acme-report from the task-template template", git(ws, "log", "--oneline"))
        meta = json.loads((ws / ".workrealm.json").read_text())
        self.assertEqual((meta["name"], meta["from_template"]), ("acme-report", "task-template"))
        self.assertNotIn("template", meta)
        for rel in ("README.md", "STATE.md", "docs/decisions/DECISIONS.md"):
            first = (ws / rel).read_text(encoding="utf-8").splitlines()[0]
            self.assertTrue(first.endswith("acme-report"), first)
        self.assertNotIn("task-template", (ws / "STATE.md").read_text(encoding="utf-8"))
        self.assertNotIn("Made from the template", helper(ws, "status").stdout)
        again = helper(ws, "init")
        self.assertIn("already on", again.stdout)
        self.assertEqual(git(ws, "log", "--oneline").count("\n"), 2)     # nothing more to commit

    def test_a_fresh_clone_is_told_its_hooks_are_off(self):
        ws = self.new("clone1", "--quick")
        git(ws, "config", "--unset", "core.hooksPath")
        self.assertIn("Git hooks are OFF", helper(ws, "status").stdout)
        helper(ws, "init")
        self.assertEqual(git(ws, "config", "core.hooksPath").strip(), ".githooks")
        self.assertNotIn("Git hooks are OFF", helper(ws, "status").stdout)


class TestCI(Base):
    def ci(self, ws: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, ".ai/policy.py", "ci", *args], cwd=ws, capture_output=True, text=True)

    def test_workflow_ships_from_the_task_tier_as_a_tool_file(self):
        quick = self.new("c1", "--quick")
        self.assertFalse((quick / ".github").exists())
        run_wr("upgrade", "--to", "task", "--path", str(quick))
        flow = quick / ".github" / "workflows" / "workrealm.yml"
        self.assertTrue(flow.exists())
        self.assertIn("python .ai/policy.py ci", flow.read_text(encoding="utf-8"))
        write(flow, "name: tampered\n")
        self.assertIn(".github/workflows/workrealm.yml", run_wr("doctor", "--path", str(quick)).stdout)
        run_wr("doctor", "--path", str(quick), "--fix")
        self.assertIn("policy.py ci", flow.read_text(encoding="utf-8"))

    def test_ci_catches_what_skipped_the_hooks(self):
        ws = self.new("c2")
        before = git(ws, "rev-parse", "HEAD").strip()
        self.assertEqual(self.ci(ws, "--before", before).returncode, 0)
        write(ws / "references" / "spec.pdf", "v1")
        write(ws / "references" / "SOURCES_LOG.md",
              (ws / "references" / "SOURCES_LOG.md").read_text(encoding="utf-8")
              + "2026-10-16 — https://x — references/spec.pdf — spec\n")
        self.assertEqual(commit(ws, "docs: add spec").returncode, 0)
        write(ws / "references" / "spec.pdf", "v2")
        subprocess.run(["git", "commit", "-qam", "tweaked the spec", "--no-verify"], cwd=ws)
        r = self.ci(ws, "--before", before)
        self.assertEqual(r.returncode, 1)
        self.assertIn("R-COMMIT", r.stderr)
        self.assertIn("R-SOURCES", r.stderr)
        head = git(ws, "rev-parse", "HEAD").strip()
        self.assertEqual(self.ci(ws, "--before", head).returncode, 0)  # nothing new pushed

    def test_ci_range_of_a_new_branch_skips_what_other_branches_have(self):
        ws = self.new("c3", "--quick")
        bare = self.tmp / "remote.git"
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
        subprocess.run(["git", "remote", "add", "origin", str(bare)], cwd=ws, check=True)
        subprocess.run(["git", "push", "-q", "origin", "main"], cwd=ws, check=True)
        subprocess.run(["git", "fetch", "-q", "origin"], cwd=ws, check=True)
        subprocess.run(["git", "switch", "-q", "-c", "feat/work"], cwd=ws)
        write(ws / "a.txt", "x")
        subprocess.run(["git", "add", "-A"], cwd=ws)
        subprocess.run(["git", "commit", "-q", "--no-verify", "-m", "wip"], cwd=ws)
        r = self.ci(ws, "--before", "0" * 40, "--branch", "feat/work")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stderr.count("R-COMMIT"), 1)  # only the new commit, not main's history


if __name__ == "__main__":
    unittest.main()
