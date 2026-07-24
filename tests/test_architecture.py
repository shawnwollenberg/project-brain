from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
ENV = {**os.environ, "PYTHONPATH": str(SRC)}
sys.path.insert(0, str(SRC))

from project_brain import initialize, profile  # noqa: E402


def run(*args: str, cwd: Path | None = None, ok: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=cwd or ROOT, env=ENV, text=True, capture_output=True)
    if ok and result.returncode:
        raise AssertionError(result.stderr or result.stdout)
    return result


def make_repo(path: Path, name: str = "fixture") -> None:
    path.mkdir()
    run("git", "init", "-q", cwd=path)
    run("git", "config", "user.email", "fixture@example.com", cwd=path)
    run("git", "config", "user.name", "Fixture", cwd=path)
    (path / "README.md").write_text(f"# {name}\n\nSynthetic consumer fixture.\n")
    run("git", "add", ".", cwd=path)
    run("git", "commit", "-qm", "initial", cwd=path)


class StandaloneArchitectureTests(unittest.TestCase):
    def test_library_cli_profile_parity_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            make_repo(repo)
            stable_timestamp = "2026-07-24T00:00:00+00:00"
            previous = os.environ.get("PROJECT_BRAIN_TIMESTAMP")
            os.environ["PROJECT_BRAIN_TIMESTAMP"] = stable_timestamp
            ENV["PROJECT_BRAIN_TIMESTAMP"] = stable_timestamp
            try:
                library = profile(repo)
                command = run(
                    sys.executable, str(ROOT / "scripts/project_brain.py"),
                    "profile", "--repo", str(repo), "--format", "json",
                )
            finally:
                if previous is None:
                    os.environ.pop("PROJECT_BRAIN_TIMESTAMP", None)
                    ENV.pop("PROJECT_BRAIN_TIMESTAMP", None)
                else:
                    os.environ["PROJECT_BRAIN_TIMESTAMP"] = previous
                    ENV["PROJECT_BRAIN_TIMESTAMP"] = previous
            self.assertEqual(library, json.loads(command.stdout))

    def test_packaged_resources_and_initialization(self) -> None:
        schemas = SRC / "project_brain/resources/schemas"
        self.assertEqual(13, len(list(schemas.glob("*.schema.json"))))
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            make_repo(repo)
            preview = initialize(repo, dry_run=True)
            self.assertEqual(0, preview.exit_code)
            self.assertFalse((repo / ".project-brain").exists())
            applied = initialize(repo)
            self.assertEqual(0, applied.exit_code)
            self.assertTrue((repo / ".project-brain/schemas/knowledge-evaluation.schema.json").exists())

    def test_skill_install_validate_repeat_and_uninstall(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project-brain"
            installer = str(ROOT / "scripts/install_skill.py")
            run(sys.executable, installer, "install", "--target", str(target))
            repeated = run(sys.executable, installer, "install", "--target", str(target))
            self.assertIn("already installed", repeated.stdout)
            run(sys.executable, installer, "validate", "--target", str(target))
            self.assertFalse((target / "scripts").exists())
            self.assertFalse((target / "assets").exists())
            self.assertIn("project-brain", (target / "SKILL.md").read_text())
            run(sys.executable, installer, "uninstall", "--target", str(target))
            self.assertFalse(target.exists())

    def test_skill_adapter_and_source_launcher_use_same_package_cli(self) -> None:
        package = run("project-brain", "doctor", "--format", "json")
        source = run(sys.executable, str(ROOT / "scripts/project_brain.py"), "doctor", "--format", "json")
        self.assertEqual(json.loads(package.stdout), json.loads(source.stdout))

    def test_disposable_consumer_fixtures(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            for consumer in ("mission-control", "officeanywhere"):
                repo = Path(temporary) / consumer
                make_repo(repo, consumer)
                self.assertEqual(0, initialize(repo).exit_code)
                run("git", "add", ".", cwd=repo)
                run("git", "commit", "-qm", "initialize project brain", cwd=repo)
                validated = run(
                    sys.executable, str(ROOT / "scripts/project_brain.py"),
                    "validate", "--repo", str(repo), "--format", "json",
                )
                self.assertEqual("valid", json.loads(validated.stdout)["status"])


if __name__ == "__main__":
    unittest.main()
