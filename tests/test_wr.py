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
        self.assertTrue((ws / "30-decisions" / "DECISIONS.md").exists())
        self.assertFalse((ws / "40-lab").exists())

    def test_quick_is_minimal(self):
        ws = self.new("q1", "--quick")
        self.assertTrue((ws / "STATE.md").exists())
        self.assertTrue((ws / ".ai" / "checkpoint.py").exists())
        self.assertFalse((ws / "10-research").exists())
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
        for zone in ("10-research", "20-prompts", "30-decisions", "40-lab", "50-release", "90-archive"):
            self.assertTrue((ws / zone).is_dir(), zone)
        settings = json.loads((ws / ".claude" / "settings.json").read_text())
        cmds = [h["command"] for h in settings["hooks"]["PreToolUse"][0]["hooks"]]
        self.assertTrue(any("zone_guard" in c for c in cmds))
        self.assertIn("Tier:** project", (ws / "STATE.md").read_text(encoding="utf-8"))

    def test_rules_are_cumulative(self):
        agents = (self.new("p2", "--project") / "AGENTS.md").read_text(encoding="utf-8")
        for heading in ("## Context first", "## Where things go", "## Zones"):
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
        self.assertIn("## Zones", text)
        self.assertEqual(text.count("## Context first"), 1)
        self.assertTrue((ws / "40-lab" / "README.md").exists())
        self.assertEqual(json.loads((ws / ".workrealm.json").read_text())["tier"], "project")

    def test_no_downgrade(self):
        ws = self.new("u2", "--project")
        self.assertNotEqual(run_wr("upgrade", "--to", "task", "--path", str(ws)).returncode, 0)


class TestHooks(Base):
    def test_protect_paths(self):
        ws = self.new("h1")
        src = ws / "10-research" / "sources" / "spec.pdf"
        src.write_bytes(b"x")
        blocked = run_hook(ws, "protect_paths.py", {"tool_name": "Edit", "tool_input": {"file_path": str(src)}})
        self.assertEqual(blocked.returncode, 2)
        new = run_hook(ws, "protect_paths.py",
                       {"tool_name": "Write", "tool_input": {"file_path": str(src.with_name("new.pdf"))}})
        self.assertEqual(new.returncode, 0)
        note = run_hook(ws, "protect_paths.py",
                        {"tool_name": "Edit", "tool_input": {"file_path": str(ws / "10-research" / "notes" / "a.md")}})
        self.assertEqual(note.returncode, 0)

    def test_zone_guard(self):
        ws = self.new("h2", "--project")
        stray = run_hook(ws, "zone_guard.py",
                         {"tool_name": "Write", "tool_input": {"file_path": str(ws / "10-research" / "notes" / "ADR-01-x.md")}})
        self.assertEqual(stray.returncode, 2)
        (ws / "10-research" / "notes" / "plan.md").write_text("x")
        copy = run_hook(ws, "zone_guard.py",
                        {"tool_name": "Write", "tool_input": {"file_path": str(ws / "30-decisions" / "plan.md")}})
        self.assertEqual(copy.returncode, 2)
        ok = run_hook(ws, "zone_guard.py",
                      {"tool_name": "Write", "tool_input": {"file_path": str(ws / "30-decisions" / "ADR-01-x.md")}})
        self.assertEqual(ok.returncode, 0)
        nb = run_hook(ws, "zone_guard.py",
                      {"tool_name": "NotebookEdit", "tool_input": {"notebook_path": str(ws / "src" / "DECISIONS.ipynb")}})
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
        src = ws / "10-research" / "sources" / "spec.pdf"
        write(src, "v1")
        self.assertRefused(commit(ws, "docs: add spec"), "R-SOURCES")
        log = ws / "10-research" / "SOURCES_LOG.md"
        write(log, log.read_text(encoding="utf-8") + "\n2026-10-12 — https://x — 10-research/sources/spec.pdf — spec\n")
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
        write(ws / "10-research" / "notes" / "Random Notes.md", "x")
        self.assertRefused(commit(ws, "docs: notes"), "R-PLACE")
        subprocess.run(["git", "reset", "-q"], cwd=ws)
        (ws / "10-research" / "notes" / "Random Notes.md").unlink()
        write(ws / "10-research" / "notes" / "2026-10-12-vendor-options.md", "x")
        self.assertCommitted(commit(ws, "docs: notes"))

    def test_decision_register(self):
        ws = self.new("g5")
        dec = ws / "30-decisions" / "DECISIONS.md"
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
        oi = ws / "30-decisions" / "OPEN-ITEMS.md"
        base = oi.read_text(encoding="utf-8")
        write(oi, base.replace("| O1 | | | | |", "| O1 | Which vendor? | KH | | |"))
        self.assertRefused(commit(ws, "docs: open item", "why"), "R-DECISIONS")
        write(oi, base.replace("| O1 | | | | |", "| O1 | Which vendor? | KH | before pilot | |"))
        self.assertCommitted(commit(ws, "docs: open item", "Blocks the pilot."))

    def test_adr_format_and_zones(self):
        ws = self.new("g7", "--project")
        write(ws / "30-decisions" / "ADR-01-storage.md", "# ADR-01\n\n## Decision\n\nPostgres.\n")
        self.assertRefused(commit(ws, "docs: adr", "why"), "R-ADR")
        template = (ws / "30-decisions" / "ADR-TEMPLATE.md").read_text(encoding="utf-8")
        write(ws / "30-decisions" / "ADR-01-storage.md", template)
        self.assertCommitted(commit(ws, "docs: adr", "Storage needs an argued decision."))

        write(ws / "10-research" / "notes" / "2026-10-12-draft.md", "x")
        self.assertCommitted(commit(ws, "docs: draft"))
        write(ws / "40-lab" / "protocols" / "2026-10-12-draft.md", "x")
        self.assertRefused(commit(ws, "docs: copy draft"), "R-ZONES")
        subprocess.run(["git", "reset", "-q"], cwd=ws)
        (ws / "40-lab" / "protocols" / "2026-10-12-draft.md").unlink()
        write(ws / "src" / "DECISIONS.md", "x")
        self.assertRefused(commit(ws, "docs: stray"), "R-ZONES")

    def test_english_warns_but_commits(self):
        ws = self.new("g8", "--quick")
        write(ws / "notes.md", "Odluka je donesena: što prije.\n")
        r = commit(ws, "docs: note")
        self.assertCommitted(r)
        self.assertIn("R-LANG", r.stderr)


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
        src = ws / "10-research" / "sources" / "spec.pdf"
        src.write_bytes(b"x")
        cases = {
            "rm 10-research/sources/spec.pdf": 2,
            "Remove-Item 10-research\\sources\\spec.pdf": 2,
            "sed -i s/a/b/ 10-research/sources/spec.pdf": 2,
            "echo x >> 10-research/sources/spec.pdf": 2,
            "git mv 10-research/sources/spec.pdf 10-research/notes/": 2,
            "rm -rf 40-lab/results": 2,
            "cat 10-research/sources/spec.pdf > 10-research/notes/2026-10-12-spec.md": 0,
            "curl -o 10-research/sources/new.pdf https://example.com/a.pdf": 0,
            "echo x > 10-research/sources/new.txt": 0,
            'git commit --no-verify -m "feat: x"': 2,
            'git commit -nm "feat: x"': 2,
            "git push -n origin main": 0,
            "git config core.hooksPath /dev/null": 2,
            "git status && ls 10-research/sources": 0,
        }
        for command, expected in cases.items():
            r = run_hook(ws, "bash_guard.py", {"tool_name": "Bash", "tool_input": {"command": command}})
            self.assertEqual(r.returncode, expected, f"{command}: {r.stderr}")

    def test_task_helpers_produce_what_the_checks_accept(self):
        ws = self.new("s4")
        self.assertEqual(helper(ws, "note", "Vendor options!").returncode, 0)
        self.assertTrue((ws / "10-research" / "notes").glob("*-vendor-options.md"))
        local = self.tmp / "spec-v2.pdf"
        local.write_bytes(b"pdf")
        r = helper(ws, "source", "add", "https://example.com/spec-v2.pdf", "--desc", "Spec v2", "--file", str(local))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotEqual(helper(ws, "source", "add", "https://x", "--desc", "d", "--file", str(local)).returncode, 0)
        self.assertEqual(helper(ws, "decide", "Use Postgres", "--alt", "SQLite -- no concurrent writers").returncode, 0)
        self.assertEqual(helper(ws, "decide", "Use MySQL", "--alt", "Postgres -- licence",
                                "--supersedes", "D1").returncode, 0)
        decisions = (ws / "30-decisions" / "DECISIONS.md").read_text(encoding="utf-8")
        self.assertIn("| D1 |", decisions)
        self.assertIn("| D2 |", decisions)
        self.assertEqual(len(re.findall(r"^\| D1 \|", decisions, re.M)), 1)
        self.assertEqual(helper(ws, "open-item", "Which vendor?", "--owner", "KH", "--trigger", "pilot").returncode, 0)
        self.assertEqual(helper(ws, "open-item", "Budget?", "--owner", "KH", "--trigger", "Q4").returncode, 0)
        self.assertEqual(helper(ws, "close-item", "O1", "Vendor A").returncode, 0)
        items = (ws / "30-decisions" / "OPEN-ITEMS.md").read_text(encoding="utf-8")
        self.assertIn("| O1 | Which vendor? | Vendor A |", items.split("## Closed")[1])
        self.assertNotIn("Which vendor?", items.split("## Closed")[0])
        self.assertEqual(commit(ws, "docs: helpers", "Exercise every task helper.").returncode, 0)
        self.assertNotEqual(helper(ws, "adr", "new", "x").returncode, 0)  # project tier only

    def test_project_helpers_produce_what_the_checks_accept(self):
        ws = self.new("s5", "--project")
        for args in (("adr", "new", "Storage backend"), ("exp", "new", "Cache warmup"), ("run", "new", "smoke"),
                     ("run", "new"), ("prompt", "new", "Restructure plan")):
            self.assertEqual(helper(ws, *args).returncode, 0, args)
        self.assertTrue((ws / "30-decisions" / "ADR-01-storage-backend.md").exists())
        runs = sorted(p.name for p in (ws / "40-lab" / "results").iterdir() if p.is_dir())
        self.assertEqual(len(runs), 2)
        self.assertTrue(runs[1].endswith("-02"))
        r = commit(ws, "docs: scaffold work", "Exercise every project helper.")
        self.assertEqual(r.returncode, 0, r.stderr)
        prompt = next((ws / "20-prompts" / "active").glob("*-restructure-plan.md"))
        self.assertEqual(helper(ws, "prompt", "done", str(prompt.relative_to(ws))).returncode, 0)
        self.assertEqual(commit(ws, "docs: prompt ran").returncode, 0)
        self.assertEqual(helper(ws, "release", "cut", "v0.1.0", "--include", "30-decisions").returncode, 0)
        manifest = (ws / "50-release" / "v0.1.0" / "MANIFEST.md").read_text(encoding="utf-8")
        self.assertIn("ADR-01-storage-backend.md", manifest)
        self.assertNotEqual(helper(ws, "release", "cut", "v0.2.0", "--include", "src").returncode, 0)  # dirty
        r = commit(ws, "chore: release v0.1.0")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_every_skill_is_well_formed_and_calls_real_helpers(self):
        ws = self.new("s6", "--project")
        skills = sorted((ws / ".claude" / "skills").glob("*/SKILL.md"))
        self.assertEqual(len(skills), 9)
        for skill in skills:
            text = skill.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\nname: " + skill.parent.name + "\ndescription: "), skill)
            for cmd in set(re.findall(r"python \.ai/wr\.py ([a-z-]+(?: new| add| cut| done)?)", text)):
                r = helper(ws, *cmd.split(), "--help")
                self.assertEqual(r.returncode, 0, f"{skill.parent.name}: {cmd}")


REAL_BRAIN = Path(os.environ.get("AGENTBRAIN_PATH") or Path.home() / ".agentbrain")
AGENT_SRC = """---
name: {name}
role: {name} role
tiers: {tiers}
triggers:
  - "do {name}"
writes_to:
  - "10-research/notes/"
never_touches:
  - "10-research/sources/"
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


if __name__ == "__main__":
    unittest.main()
