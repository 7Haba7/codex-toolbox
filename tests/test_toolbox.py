import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ToolboxTests(unittest.TestCase):
    def test_agent_profiles(self):
        agents = ROOT / ".codex" / "agents"
        expected = {"analyst", "builder", "explorer", "researcher", "reviewer", "tester", "writer"}
        profiles = list(agents.glob("*.toml"))
        self.assertTrue(expected.issubset({p.stem for p in profiles}))
        for path in profiles:
            with self.subTest(path=path), path.open("rb") as stream:
                profile = tomllib.load(stream)
                self.assertEqual(profile["name"], path.stem)
                for field in ("description", "developer_instructions"):
                    self.assertTrue(profile[field].strip())

    def test_summary(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)

            def summary(*args):
                return subprocess.run([sys.executable, ROOT / "tools/context.py", *args],
                                      cwd=repo, capture_output=True, text=True)

            def git(*args):
                subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)

            self.assertNotEqual(summary().returncode, 0)
            git("init", "-q")
            for dirname in ("app[1]", "other"):
                directory = repo / dirname
                directory.mkdir()
                (directory / "tracked.txt").write_text("original\n")
            git("add", ".")
            git("-c", "user.name=Test", "-c", "user.email=test@localhost", "commit", "-qm", "base")
            self.assertEqual(summary().stdout.count("(none)"), 2)
            for file in repo.glob("*/tracked.txt"):
                file.write_text("changed\n")
            git("add", "app[1]/tracked.txt", "other/tracked.txt")
            (repo / "app[1]/tracked.txt").write_text("changed again\n")
            (repo / "app[1]/new.txt").touch()
            result = summary("--path", "app[1]")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("MM app[1]/tracked.txt", result.stdout)
            self.assertIn("?? app[1]/new.txt", result.stdout)
            self.assertNotIn("other", result.stdout)
            self.assertIn("other/tracked.txt", summary().stdout)
            clipped = summary("--limit", "100").stdout
            self.assertEqual(len(clipped), 100)
            self.assertTrue(clipped.endswith("[truncated]\n"))
            self.assertNotEqual(summary("--limit", "99").returncode, 0)

            for i in range(50):
                (repo / (f"change-{i:02d}-" + "x" * 75)).touch()
            full = summary()
            self.assertEqual(full.returncode, 0, full.stderr)
            self.assertGreater(len(full.stdout), 4000)
            self.assertNotIn("[truncated]", full.stdout)
