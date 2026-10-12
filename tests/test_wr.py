"""End-to-end tests: scaffold each tier into a temp dir and exercise the hooks.

    python -m unittest discover tests
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WR = ROOT / "wr.py"


def run_wr(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(WR), *args], cwd=cwd, capture_output=True, text=True)


def run_hook(ws: Path, script: str, payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ws / ".ai" / "hooks" / script)], cwd=ws,
                          input=json.dumps(payload), capture_output=True, text=True,
                          env={**__import__("os").environ, "CLAUDE_PROJECT_DIR": str(ws)})


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
        self.assertNotIn("PreToolUse", settings["hooks"])

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
        self.assertTrue((ws / ".git" / "hooks" / "post-commit").exists())

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


if __name__ == "__main__":
    unittest.main()
