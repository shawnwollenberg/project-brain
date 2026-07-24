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
        laundered = propose_learning(
            self.repo,
            mission_id=self.mission_id,
            claim="Conflicting evidence kinds fail",
            evidence=["file:README.md", "test:README.md"],
            dry_run=True,
        )
        self.assertEqual(2, laundered.exit_code)
        self_authored = self.repo / ".project-brain/lessons/proposed/self-authored.yaml"
        self_authored.write_text("claim: assertion\n")
        rejected = propose_learning(
            self.repo,
            mission_id=self.mission_id,
            claim="Self-authored evidence fails",
            evidence=[".project-brain/lessons/proposed/self-authored.yaml"],
            dry_run=True,
        )
        self.assertEqual(2, rejected.exit_code)

    def test_explicit_cli_values_override_structured_defaults(self) -> None:
        structured = self.repo / "proposal-input.yaml"
        structured.write_text(
            f"mission_id: {self.mission_id}\n"
            "claim: Explicit values override structured defaults\n"
            "scope: [repository]\n"
            "evidence: [{kind: file, reference: README.md}]\n"
            "proposed_by: file-author\n"
            "confidence: low\n"
        )
        preview = propose_learning(
            self.repo,
            input=str(structured),
            proposer="cli-author",
            confidence="high",
            dry_run=True,
        )
        self.assertEqual("cli-author", preview.data["proposal"]["proposed_by"])
        self.assertEqual("high", preview.data["proposal"]["confidence"])

    def test_rejects_mission_path_traversal_and_malformed_structured_scope(self) -> None:
        traversal = propose_learning(
            self.repo,
            mission_id="../outside",
            claim="Traversal must fail",
            evidence=["README.md"],
            dry_run=True,
        )
        self.assertEqual(2, traversal.exit_code)
        self.assertIn("path traversal", traversal.text)
        structured = self.repo / "malformed.yaml"
        structured.write_text(
            f"mission_id: {self.mission_id}\n"
            "claim: Malformed scope must fail\n"
            "scope: repository\n"
            "evidence: [README.md]\n"
        )
        malformed = propose_learning(self.repo, input=str(structured), dry_run=True)
        self.assertEqual(2, malformed.exit_code)
        self.assertIn("list of strings", malformed.text)

    def test_existing_noop_revalidates_full_artifact_and_fingerprint(self) -> None:
        options = {
            "mission_id": self.mission_id,
            "claim": "Existing proposals are revalidated before no-op",
            "scope": ["repository"],
            "evidence": ["README.md"],
        }
        created = propose_learning(self.repo, **options)
        self.assertEqual("created", created.data["status"])
        path = self.repo / created.data["created"][0]
        path.write_text(path.read_text().replace("confidence: medium", "confidence: invalid"))
        invalid = propose_learning(self.repo, **options)
        self.assertEqual(2, invalid.exit_code)
        self.assertIn("Schema validation failed", invalid.text)

    def test_symlink_alias_cannot_hide_self_authored_evidence(self) -> None:
        source = self.repo / ".project-brain/lessons/proposed/source.yaml"
        source.write_text("claim: assertion\n")
        alias = self.repo / "aliased-evidence.md"
        alias.symlink_to(source)
        rejected = propose_learning(
            self.repo,
            mission_id=self.mission_id,
            claim="Symlink aliases cannot launder evidence",
            evidence=["aliased-evidence.md"],
            dry_run=True,
        )
        self.assertEqual(2, rejected.exit_code)
        self.assertIn("not independent evidence", rejected.text)

    def test_empty_explicit_values_do_not_fall_back_to_structured_input(self) -> None:
        structured = self.repo / "proposal-input.yaml"
        structured.write_text(
            f"mission_id: {self.mission_id}\n"
            "claim: File claim\n"
            "scope: [repository]\n"
            "evidence: [README.md]\n"
            "proposed_by: file-author\n"
        )
        result = propose_learning(self.repo, input=str(structured), claim="", dry_run=True)
        self.assertEqual(2, result.exit_code)
        self.assertIn("requires mission_id and claim", result.text)
        empty_scope = propose_learning(self.repo, input=str(structured), scope=[], dry_run=True)
        self.assertEqual(2, empty_scope.exit_code)
        empty_evidence = propose_learning(self.repo, input=str(structured), evidence=[], dry_run=True)
        self.assertEqual(2, empty_evidence.exit_code)

    def test_noop_preserves_original_observation_date(self) -> None:
        options = {
            "mission_id": self.mission_id,
            "claim": "Repeated proposals preserve their original observation date",
            "scope": ["repository"],
            "evidence": ["README.md"],
        }
        created = propose_learning(self.repo, **options)
        self.assertEqual("2026-07-24", created.data["proposal"]["observed_at"])
        run("git", "add", ".", cwd=self.repo)
        run("git", "commit", "-qm", "proposal", cwd=self.repo)
        previous = os.environ.get("PROJECT_BRAIN_DATE")
        os.environ["PROJECT_BRAIN_DATE"] = "2026-07-25"
        try:
            repeated = propose_learning(self.repo, **options)
        finally:
            if previous is None:
                os.environ.pop("PROJECT_BRAIN_DATE", None)
            else:
                os.environ["PROJECT_BRAIN_DATE"] = previous
        self.assertEqual("no-op", repeated.data["status"])
        self.assertEqual("2026-07-24", repeated.data["proposal"]["observed_at"])

    def test_mission_symlink_cannot_escape_missions_directory(self) -> None:
        outside = self.repo / "outside-mission.yaml"
        mission = self.repo / ".project-brain/missions" / f"{self.mission_id}.yaml"
        outside.write_text(mission.read_text().replace(self.mission_id, "symlink-mission", 1))
        alias = self.repo / ".project-brain/missions/symlink.yaml"
        alias.symlink_to(outside)
        rejected = propose_learning(
            self.repo,
            mission_id="symlink-mission",
            claim="Mission symlinks cannot escape",
            evidence=["README.md"],
            dry_run=True,
        )
        self.assertEqual(2, rejected.exit_code)
        self.assertIn("escapes the missions directory", rejected.text)


def _yaml_value(text: str, key: str) -> str:
    for line in text.splitlines():
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip()
    raise AssertionError(f"{key} missing from output")


if __name__ == "__main__":
    unittest.main()
