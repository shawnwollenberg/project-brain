from __future__ import annotations

import hashlib
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

from project_brain import capabilities, consumer_operation, initialize  # noqa: E402
from project_brain import core  # noqa: E402


def run(*args: str, cwd: Path, ok: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=cwd, env=ENV, text=True, capture_output=True)
    if ok and result.returncode:
        raise AssertionError(result.stderr or result.stdout)
    return result


def make_repo(path: Path) -> None:
    run("git", "init", "-q", cwd=path)
    run("git", "config", "user.email", "consumer@example.com", cwd=path)
    run("git", "config", "user.name", "Consumer Test", cwd=path)
    (path / "README.md").write_text("# Consumer fixture\n\nContext contract evidence.\n")
    (path / "src.py").write_text("def integration_contract():\n    return 'context evidence'\n")
    run("git", "add", ".", cwd=path)
    run("git", "commit", "-qm", "initial", cwd=path)


class ConsumerIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name)
        make_repo(self.repo)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def initialize(self) -> None:
        self.assertEqual(0, initialize(self.repo).exit_code)
        run("git", "add", ".", cwd=self.repo)
        run("git", "commit", "-qm", "initialize brain", cwd=self.repo)

    def validate_envelope(self, value: dict) -> None:
        core.validate_data(value, core.ASSET_ROOT / "schemas/consumer-envelope.schema.json")

    def test_capability_discovery_and_contract_compatibility(self) -> None:
        report = capabilities()
        self.assertEqual("0.4.0", report["core_version"])
        self.assertEqual(["1.0"], report["consumer_contract_versions"])
        self.assertFalse(report["feature_flags"]["automatic_promotion"])
        self.assertIn("prepare_context", report["operations"])
        compatible = consumer_operation("detect_repository", self.repo, contract_version="1.0")
        unsupported = consumer_operation("detect_repository", self.repo, contract_version="2.0")
        self.assertEqual("succeeded", compatible["status"])
        self.assertEqual("incompatible_contract", unsupported["exit_classification"])
        self.validate_envelope(compatible)
        self.validate_envelope(unsupported)

    def test_structured_errors_do_not_expose_tracebacks(self) -> None:
        result = consumer_operation("validate_repository", self.repo)
        self.assertEqual("failed", result["status"])
        self.assertEqual("not_initialized", result["exit_classification"])
        self.assertNotIn("Traceback", json.dumps(result))
        self.validate_envelope(result)

    def test_context_quality_revision_checksum_and_mutation_reporting(self) -> None:
        self.initialize()
        result = consumer_operation(
            "prepare_context",
            self.repo,
            {
                "objective": "Use the integration contract",
                "role": "implementer",
                "reference": ["README.md"],
                "missing_context": ["src.py"],
                "revision_count": 1,
                "mission_id": "mission-1",
                "execution_id": "execution-1",
                "write": True,
            },
        )
        self.assertEqual("succeeded", result["status"])
        self.assertTrue(result["repository_files_changed"])
        quality = result["data"]["context_pack"]["context_quality"]
        self.assertEqual("revised", quality["completeness_status"])
        self.assertEqual(["src.py"], quality["missing_context_detected"])
        self.assertTrue(quality["final_explicit_sources_complete"])
        self.assertFalse(quality["optimality_claimed"])
        artifact = result["artifacts"][0]
        content = (self.repo / artifact["path"]).read_bytes()
        self.assertEqual(hashlib.sha256(content).hexdigest(), artifact["sha256"])
        binding = result["data"]["context_pack"]["consumer_binding"]
        self.assertEqual("mission-1", binding["mission_id"])
        self.assertEqual("execution-1", binding["execution_id"])
        self.validate_envelope(result)

    def test_health_summary_uses_inspectable_counts_without_score(self) -> None:
        self.initialize()
        result = consumer_operation("get_health", self.repo)
        self.assertEqual("succeeded", result["status"])
        health = result["data"]
        self.assertTrue(health["brain_initialized"])
        self.assertTrue(health["validation"]["valid"])
        self.assertIsNone(health["overall_score"])
        self.assertEqual(0, health["knowledge"]["confirmed"])
        core.validate_data(health, core.ASSET_ROOT / "schemas/knowledge-health.schema.json")

    def test_curation_exposes_evaluator_reports_without_promoting(self) -> None:
        self.initialize()
        fixture = {
            "schema_version": "2.5.0",
            "artifact_type": "knowledge-evaluation",
            "evaluation_id": "evaluation-fixture",
            "evaluated_at": "2026-07-24",
            "evaluator": "independent-review",
            "evaluations": [],
            "repository_changes_approved": False,
            "approval": {"required": True, "status": "pending", "approved_by": None, "approved_at": None},
        }
        target = self.repo / ".project-brain/evaluations/evaluation-fixture.yaml"
        target.write_text(core.dump_yaml(fixture))
        result = consumer_operation("get_curation", self.repo)
        self.assertEqual("succeeded", result["status"])
        self.assertEqual(1, len(result["data"]["evaluations"]))
        self.assertTrue(result["human_approval_required"])
        self.assertFalse(result["repository_files_changed"])

    def test_library_and_cli_envelopes_match(self) -> None:
        self.initialize()
        previous = os.environ.get("PROJECT_BRAIN_TIMESTAMP")
        os.environ["PROJECT_BRAIN_TIMESTAMP"] = "2026-07-24T00:00:00+00:00"
        try:
            library = consumer_operation("get_summary", self.repo)
        finally:
            if previous is None:
                os.environ.pop("PROJECT_BRAIN_TIMESTAMP", None)
            else:
                os.environ["PROJECT_BRAIN_TIMESTAMP"] = previous
        command = run(
            sys.executable,
            str(ROOT / "scripts/project_brain.py"),
            "consumer",
            "--operation",
            "get_summary",
            "--repo",
            str(self.repo),
            cwd=self.repo,
        )
        self.assertEqual(library, json.loads(command.stdout))

    def test_newer_repository_schema_is_rejected(self) -> None:
        self.initialize()
        proposal = self.repo / ".project-brain/lessons/proposed/newer.yaml"
        proposal.write_text(
            'schema_version: "9.0.0"\nartifact_type: proposed-learning\nid: newer\n'
            "title: Newer\nscope: [repository]\nstatus: proposed\nclaim: New schema\n"
            "evidence: [{kind: file, reference: README.md}]\nconfidence: medium\n"
            'observed_at: "2026-07-24"\nrecommended_future_behavior: Review\n'
            "proposed_by: test\nsource_mission: mission\nsuggested_disposition: human-review\n"
            "contradiction_check: pending\nduplicate_check: pending\n"
        )
        result = consumer_operation("validate_repository", self.repo)
        self.assertEqual("failed", result["status"])
        self.assertEqual("invalid_schema", result["exit_classification"])

    def test_capabilities_cli_json(self) -> None:
        result = run(
            sys.executable,
            str(ROOT / "scripts/project_brain.py"),
            "capabilities",
            "--json",
            cwd=self.repo,
        )
        self.assertEqual(capabilities()["operations"], json.loads(result.stdout)["operations"])


if __name__ == "__main__":
    unittest.main()
