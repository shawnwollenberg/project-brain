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
ENV = {
    **os.environ,
    "PYTHONPATH": str(SRC),
    "PROJECT_BRAIN_DATE": "2026-07-24",
    "PROJECT_BRAIN_TIMESTAMP": "2026-07-24T00:00:00+00:00",
}
sys.path.insert(0, str(SRC))

from project_brain import initialize, propose_learning  # noqa: E402


def run(*args: str, cwd: Path, ok: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=cwd, env=ENV, text=True, capture_output=True)
    if ok and result.returncode:
        raise AssertionError(result.stderr or result.stdout)
    return result


class ProposalWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name)
        run("git", "init", "-q", cwd=self.repo)
        run("git", "config", "user.email", "proposal@example.com", cwd=self.repo)
        run("git", "config", "user.name", "Proposal Test", cwd=self.repo)
        (self.repo / "README.md").write_text("# Proposal evidence\n\nMission-backed proposal evidence.\n")
        run("git", "add", ".", cwd=self.repo)
        run("git", "commit", "-qm", "initial", cwd=self.repo)
        self.assertEqual(0, initialize(self.repo).exit_code)
        run("git", "add", ".", cwd=self.repo)
        run("git", "commit", "-qm", "initialize brain", cwd=self.repo)
        self.start_sha = run("git", "rev-parse", "HEAD", cwd=self.repo).stdout.strip()
        close = run(
            sys.executable, str(ROOT / "scripts/project_brain.py"), "close-mission",
            "--repo", str(self.repo),
            "--objective", "Create standalone proposals",
            "--role", "implementer",
            "--status", "completed",
            "--start-sha", self.start_sha,
            "--acceptance-criterion", "Proposal workflow is tested",
            "--acceptance-outcome", "passed",
            "--check", "unittest=passed",
            "--evidence", "README.md",
            cwd=self.repo,
        )
        self.mission_id = _yaml_value(close.stdout, "mission_id")
        run("git", "add", ".", cwd=self.repo)
        run("git", "commit", "-qm", "record mission", cwd=self.repo)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_dry_run_create_noop_and_json_cli_parity(self) -> None:
        options = {
            "mission_id": self.mission_id,
            "claim": "Mission-backed proposals preserve inspectable evidence",
            "scope": ["Repository", "repository"],
            "evidence": ["README.md", "file:README.md"],
            "proposer": "implementer",
            "dry_run": True,
        }
        preview = propose_learning(self.repo, **options)
        self.assertEqual("dry-run", preview.data["status"])
        self.assertFalse((self.repo / ".project-brain/lessons/proposed" / f"{preview.data['proposal']['id']}.yaml").exists())
        created = propose_learning(self.repo, **{**options, "dry_run": False})
        self.assertEqual("created", created.data["status"])
        self.assertEqual(["repository"], created.data["proposal"]["scope"])
        self.assertRegex(created.data["proposal_fingerprint"], r"^[0-9a-f]{64}$")
        run("git", "add", ".", cwd=self.repo)
        run("git", "commit", "-qm", "proposal", cwd=self.repo)
        repeated = propose_learning(self.repo, **{**options, "dry_run": False})
        self.assertEqual("no-op", repeated.data["status"])
        cli = run(
            sys.executable, str(ROOT / "scripts/project_brain.py"), "propose-learning",
            "--repo", str(self.repo), "--mission-id", self.mission_id,
            "--claim", options["claim"], "--scope", "repository",
            "--evidence", "README.md", "--proposer", "implementer",
            "--format", "json", cwd=self.repo,
        )
        self.assertEqual(repeated.data["proposal_fingerprint"], json.loads(cli.stdout)["proposal_fingerprint"])

    def test_structured_input_and_invalid_mission_sha(self) -> None:
        structured = self.repo / "proposal-input.yaml"
        structured.write_text(
            f"mission_id: {self.mission_id}\n"
            "claim: Structured proposals remain proposal-only\n"
            "scope: [repository]\n"
            "evidence:\n  - kind: file\n    reference: README.md\n"
            "proposed_by: test-author\n"
        )
        preview = propose_learning(self.repo, input=str(structured), dry_run=True)
        self.assertEqual("dry-run", preview.data["status"])
        mission = self.repo / ".project-brain/missions" / f"{self.mission_id}.yaml"
        mission.write_text(mission.read_text().replace(self.start_sha, "f" * 40, 1))
        invalid = propose_learning(
            self.repo,
            mission_id=self.mission_id,
            claim="Invalid SHA is rejected",
            evidence=["README.md"],
            dry_run=True,
        )
        self.assertEqual(2, invalid.exit_code)
        self.assertIn("does not resolve to a Git commit", invalid.text)

    def test_rejects_unsupported_or_unsafe_evidence(self) -> None:
        unsupported = propose_learning(
            self.repo,
            mission_id=self.mission_id,
            claim="Unsupported evidence kinds fail",
            evidence=["imaginary:README.md"],
            dry_run=True,
        )
        self.assertEqual(2, unsupported.exit_code)
        missing = propose_learning(
            self.repo,
            mission_id=self.mission_id,
            claim="Missing evidence paths fail",
            evidence=["missing.md"],
            dry_run=True,
        )
        self.assertEqual(2, missing.exit_code)


def _yaml_value(text: str, key: str) -> str:
    for line in text.splitlines():
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip()
    raise AssertionError(f"{key} missing from output")


if __name__ == "__main__":
    unittest.main()
