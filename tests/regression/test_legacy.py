#!/usr/bin/env python3
"""Deterministic regression tests for Project Brain."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
import json
import sys
import shutil
import re
from pathlib import Path

CLI = Path(__file__).resolve().parents[2] / "scripts" / "project_brain.py"
FIXED_ENV = {**os.environ, "PROJECT_BRAIN_DATE": "2026-01-02", "PROJECT_BRAIN_TIMESTAMP": "2026-01-02T03:04:05+00:00"}


def compatible_python() -> str:
    candidates = [
        os.environ.get("PROJECT_BRAIN_TEST_PYTHON"),
        str(Path.home() / "opt/miniconda3/bin/python3"),
        str(Path.home() / "miniconda3/bin/python3"),
        shutil.which("python3"),
        sys.executable,
    ]
    for candidate in filter(None, candidates):
        result = subprocess.run([candidate, "-c", "import yaml, jsonschema"], capture_output=True)
        if result.returncode == 0:
            return str(candidate)
    return sys.executable


PYTHON = compatible_python()


def parse_yaml(text: str) -> dict:
    result = subprocess.run(
        [PYTHON, "-c", "import json,sys,yaml; print(json.dumps(yaml.safe_load(sys.stdin.read())))"],
        input=text,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def command(*args: str, cwd: Path, ok: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run([PYTHON, str(CLI), *args], cwd=cwd, env=FIXED_ENV, text=True, capture_output=True)
    if ok and result.returncode:
        raise AssertionError(result.stderr)
    return result


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True)
    return result.stdout.strip()


class ProjectBrainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "Project Brain Test")
        (self.repo / "README.md").write_text("# Sample\n\nScheduler architecture.\n")
        (self.repo / "package.json").write_text('{"scripts":{"test":"node --test","lint":"eslint ."},"dependencies":{"react":"1"}}\n')
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "initial")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def initialize(self) -> None:
        command("init", "--repo", str(self.repo), cwd=self.repo)

    def commit_all(self, message: str = "brain") -> None:
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", message)

    def write_proposal(
        self,
        learning_id: str,
        claim: str,
        scope: str = "repository",
        evidence: str = "[{kind: file, reference: README.md}]",
    ) -> None:
        folder = self.repo / ".project-brain/lessons/proposed"
        (folder / f"{learning_id}.yaml").write_text(f"""schema_version: "2.5.0"
artifact_type: proposed-learning
id: {learning_id}
title: Evaluator fixture
scope: [{scope}]
status: proposed
claim: {claim}
evidence: {evidence}
confidence: medium
observed_at: "2026-01-02"
recommended_future_behavior: Apply after review
proposed_by: test-agent
source_mission: mission-1
suggested_disposition: human-review
contradiction_check: pending evaluator
duplicate_check: pending evaluator
""")

    def record_evaluation(self, name: str = "evaluation.yaml") -> None:
        command(
            "evaluate", "--repo", str(self.repo),
            "--output", str(self.repo / ".project-brain/evaluations" / name),
            cwd=self.repo,
        )

    def write_confirmed(self, learning_id: str, claim: str, scope: str = "repository") -> None:
        path = self.repo / ".project-brain/lessons/confirmed" / f"{learning_id}.yaml"
        path.write_text(f"""schema_version: "2.5.0"
artifact_type: confirmed-learning
id: {learning_id}
title: Confirmed fixture
scope: [{scope}]
status: confirmed
claim: {claim}
evidence: [{{kind: file, reference: README.md}}]
confidence:
  score: 0.75
validation:
  observed: 2
  reused: 1
  contradicted: 0
  superseded: false
last_verified: "2026-01-02"
observed_at: "2026-01-02"
verified_at: "2026-01-02"
superseded_by: null
recommended_future_behavior: Apply after review
proposed_by: test-agent
reviewed_by: human-reviewer
source_mission: mission-1
""")

    def test_new_repository_initialization_and_profile_detection(self) -> None:
        self.initialize()
        self.assertTrue((self.repo / ".project-brain/project-profile.yaml").exists())
        profile = (self.repo / ".project-brain/project-profile.yaml").read_text()
        self.assertIn("React", profile)
        self.assertTrue((self.repo / "AGENTS.md").exists())

    def test_existing_agents_creates_merge_proposal(self) -> None:
        (self.repo / "AGENTS.md").write_text("# Mature instructions\n")
        git(self.repo, "add", "AGENTS.md"); git(self.repo, "commit", "-qm", "agents")
        self.initialize()
        self.assertEqual((self.repo / "AGENTS.md").read_text(), "# Mature instructions\n")
        self.assertTrue((self.repo / ".project-brain/evaluations/agents-merge-proposal.md").exists())

    def test_existing_brain_and_repeated_initialization_do_not_overwrite(self) -> None:
        self.initialize()
        state = self.repo / ".project-brain/current-state.md"
        state.write_text("# Custom state\n")
        self.commit_all()
        second = command("init", "--repo", str(self.repo), cwd=self.repo)
        self.assertIn("agents-merge-proposal.md", second.stdout)
        self.commit_all("proposal")
        result = command("init", "--repo", str(self.repo), cwd=self.repo)
        self.assertEqual(state.read_text(), "# Custom state\n")
        self.assertIn("created: []", result.stdout)

    def test_dirty_repository_blocks_apply_but_allows_dry_run(self) -> None:
        (self.repo / "README.md").write_text("dirty\n")
        result = command("init", "--repo", str(self.repo), cwd=self.repo, ok=False)
        self.assertEqual(result.returncode, 2)
        dry = command("init", "--repo", str(self.repo), "--dry-run", cwd=self.repo)
        self.assertIn("would_block_apply: true", dry.stdout)
        self.assertFalse((self.repo / ".project-brain").exists())

    def test_invalid_yaml_is_reported(self) -> None:
        self.initialize(); self.commit_all()
        path = self.repo / ".project-brain/missions/bad.yaml"
        path.write_text("artifact_type: [\n")
        result = command("validate", "--repo", str(self.repo), cwd=self.repo, ok=False)
        self.assertIn("Invalid YAML", result.stderr)

    def test_secret_detection_blocks_validation(self) -> None:
        self.initialize(); self.commit_all()
        path = self.repo / ".project-brain/missions/leak.yaml"
        path.write_text("password: verylongsecretvalue12345\n")
        result = command("validate", "--repo", str(self.repo), cwd=self.repo, ok=False)
        self.assertIn("likely secrets", result.stderr)

    def test_context_selection_is_deterministic_and_prefers_explicit(self) -> None:
        self.initialize()
        first = command("context", "--repo", str(self.repo), "--objective", "scheduler", "--role", "engineer", "--reference", "README.md", cwd=self.repo).stdout
        altered_env = {**FIXED_ENV, "PROJECT_BRAIN_TIMESTAMP": "2030-12-31T23:59:59+00:00"}
        delayed = subprocess.run(
            [PYTHON, str(CLI), "context", "--repo", str(self.repo), "--objective", "scheduler", "--role", "engineer", "--reference", "README.md"],
            cwd=self.repo, env=altered_env, text=True, capture_output=True, check=True,
        ).stdout
        second = command("context", "--repo", str(self.repo), "--objective", "scheduler", "--role", "engineer", "--reference", "README.md", cwd=self.repo).stdout
        self.assertEqual(first, second)
        self.assertEqual(first, delayed)
        self.assertIn("explicit reference", first)

    def test_source_context_includes_relevant_tsx_and_excludes_unrelated(self) -> None:
        (self.repo / "src").mkdir()
        (self.repo / "src/onboarding.tsx").write_text("export const Onboarding = () => 'customer signup checklist';\n")
        (self.repo / "src/unrelated.ts").write_text("export const MathOnly = 42;\n")
        git(self.repo, "add", "."); git(self.repo, "commit", "-qm", "source")
        self.initialize()
        output = command(
            "context", "--repo", str(self.repo), "--objective", "improve customer signup checklist",
            "--role", "engineer", "--expected-file", "src/onboarding.tsx", cwd=self.repo,
        ).stdout
        self.assertIn("src/onboarding.tsx", output)
        self.assertNotIn("src/unrelated.ts", output)

    def test_repository_identity_precedence(self) -> None:
        git(self.repo, "remote", "add", "origin", "git@github.com:example/remote-name.git")
        self.initialize()
        profile = (self.repo / ".project-brain/project-profile.yaml").read_text()
        self.assertIn("name: remote-name", profile)
        self.assertIn("identity_source: git_remote", profile)
        self.assertIn(f"checkout_path: {self.repo.resolve()}", profile)

    def test_repository_identity_package_fallback_and_override(self) -> None:
        self.initialize()
        profile = (self.repo / ".project-brain/project-profile.yaml").read_text()
        self.assertIn("identity_source: git_top_level", profile)
        package_repo = Path(tempfile.mkdtemp())
        git(package_repo, "init", "-q"); git(package_repo, "config", "user.email", "test@example.com"); git(package_repo, "config", "user.name", "Test")
        (package_repo / "package.json").write_text('{"name":"package-identity"}\n')
        git(package_repo, "add", "."); git(package_repo, "commit", "-qm", "initial")
        command("init", "--repo", str(package_repo), cwd=package_repo)
        package_profile = (package_repo / ".project-brain/project-profile.yaml").read_text()
        self.assertIn("name: package-identity", package_profile)
        self.assertIn("identity_source: package_metadata", package_profile)
        other = Path(tempfile.mkdtemp())
        git(other, "init", "-q"); git(other, "config", "user.email", "test@example.com"); git(other, "config", "user.name", "Test")
        (other / "package.json").write_text('{"name":"package-identity"}\n')
        git(other, "add", "."); git(other, "commit", "-qm", "initial")
        command("init", "--repo", str(other), "--repository-id", "explicit-id", cwd=other)
        explicit = (other / ".project-brain/project-profile.yaml").read_text()
        self.assertIn("name: explicit-id", explicit)
        self.assertIn("identity_source: cli_override", explicit)

    def test_repository_identity_stable_in_worktree(self) -> None:
        git(self.repo, "remote", "add", "origin", "https://github.com/example/stable-name.git")
        worktree = Path(tempfile.mkdtemp()) / "checkout"
        git(self.repo, "worktree", "add", "-q", "-b", "test-worktree", str(worktree))
        command("init", "--repo", str(worktree), cwd=worktree)
        profile = (worktree / ".project-brain/project-profile.yaml").read_text()
        self.assertIn("id: stable-name", profile)
        self.assertIn(f"checkout_path: {worktree.resolve()}", profile)

    def test_completed_mission_requires_evidence(self) -> None:
        self.initialize(); self.commit_all()
        sha = git(self.repo, "rev-parse", "HEAD")
        result = command("close", "--repo", str(self.repo), "--objective", "Fix tests", "--role", "engineer", "--status", "completed", "--start-sha", sha, "--acceptance-outcome", "not evaluated", cwd=self.repo, ok=False)
        self.assertIn("require at least one evidence", result.stderr)

    def test_completed_mission_rejects_fake_sha_and_missing_evidence(self) -> None:
        self.initialize(); self.commit_all()
        fake = command("close", "--repo", str(self.repo), "--objective", "Fake", "--role", "engineer",
                       "--status", "completed", "--start-sha", "deadbee", "--acceptance-outcome", "passed",
                       "--acceptance-criterion", "done", "--check", "test=passed", "--evidence", "README.md",
                       cwd=self.repo, ok=False)
        self.assertIn("does not resolve to a Git commit", fake.stderr)
        sha = git(self.repo, "rev-parse", "HEAD")
        missing = command("close", "--repo", str(self.repo), "--objective", "Missing", "--role", "engineer",
                          "--status", "completed", "--start-sha", sha, "--acceptance-outcome", "passed",
                          "--acceptance-criterion", "done", "--check", "test=passed",
                          "--evidence", "missing/not-real.ts", cwd=self.repo, ok=False)
        self.assertIn("not an inspectable repository file", missing.stderr)

    def test_mission_closure_proposes_but_does_not_confirm_learning(self) -> None:
        self.initialize(); self.commit_all()
        sha = git(self.repo, "rev-parse", "HEAD")
        command("close", "--repo", str(self.repo), "--objective", "Fix tests", "--role", "engineer", "--status", "completed", "--start-sha", sha,
                "--acceptance-criterion", "Tests pass", "--acceptance-outcome", "passed", "--check", "node --test=passed",
                "--evidence", "README.md", "--learning", "Freeze the clock in scheduler tests", cwd=self.repo)
        self.assertEqual(len(list((self.repo / ".project-brain/lessons/proposed").glob("*.yaml"))), 1)
        self.assertEqual(len(list((self.repo / ".project-brain/lessons/confirmed").glob("*.yaml"))), 0)

    def test_duplicate_curator_recommends_merge_without_mutation(self) -> None:
        self.initialize(); self.commit_all()
        base = """schema_version: "2.5.0"
artifact_type: proposed-learning
id: {id}
title: Freeze clock
scope: [repository]
status: proposed
claim: Freeze the clock in scheduler tests
evidence: [{{kind: file, reference: README.md}}]
confidence: high
observed_at: "2026-01-02"
verified_at: null
superseded_by: null
recommended_future_behavior: Freeze the clock
proposed_by: agent
source_mission: mission-1
suggested_disposition: confirm
contradiction_check: pending evaluator
duplicate_check: pending evaluator
"""
        folder = self.repo / ".project-brain/lessons/proposed"
        (folder / "one.yaml").write_text(base.format(id="one"))
        (folder / "two.yaml").write_text(base.format(id="two"))
        self.record_evaluation()
        before = sorted(p.read_text() for p in folder.glob("*.yaml"))
        result = command("curate", "--repo", str(self.repo), cwd=self.repo)
        self.assertIn("action: merge", result.stdout)
        self.assertEqual(before, sorted(p.read_text() for p in folder.glob("*.yaml")))

    def test_curator_requires_knowledge_evaluation(self) -> None:
        self.initialize(); self.commit_all()
        self.write_proposal("unevaluated", "Require approval before production changes")
        result = command("curate", "--repo", str(self.repo), cwd=self.repo)
        self.assertIn("action: followup_issue", result.stdout)
        self.assertIn("Run the deterministic Knowledge Evaluator", result.stdout)

    def test_conflicting_lessons_require_human_resolution(self) -> None:
        self.initialize(); self.commit_all()
        template = """schema_version: "2.5.0"
artifact_type: proposed-learning
id: {id}
title: Scheduler policy
scope: [scheduler]
status: proposed
claim: {claim}
evidence: [{{kind: file, reference: README.md}}]
confidence: medium
observed_at: "2026-01-02"
verified_at: null
superseded_by: null
recommended_future_behavior: Review scheduler policy
proposed_by: agent
source_mission: mission-1
suggested_disposition: policy
contradiction_check: pending evaluator
duplicate_check: pending evaluator
"""
        folder = self.repo / ".project-brain/lessons/proposed"
        (folder / "use.yaml").write_text(template.format(id="use", claim="Use wall clock"))
        (folder / "avoid.yaml").write_text(template.format(id="avoid", claim="Do not use wall clock"))
        self.record_evaluation()
        result = command("curate", "--repo", str(self.repo), cwd=self.repo)
        self.assertIn("action: followup_issue", result.stdout)
        self.assertIn("opposite polarity", result.stdout)

    def test_identical_claims_in_disjoint_scopes_are_not_merged(self) -> None:
        self.initialize(); self.commit_all()
        template = """schema_version: "2.0.0"
artifact_type: proposed-learning
id: {id}
title: Scoped policy
scope: [{scope}]
status: proposed
claim: Use a bounded retry
evidence: [{{kind: file, reference: README.md}}]
confidence: medium
observed_at: "2026-01-02"
recommended_future_behavior: Review retries
proposed_by: agent
source_mission: mission-1
suggested_disposition: policy
contradiction_check: none
duplicate_check: none
"""
        folder = self.repo / ".project-brain/lessons/proposed"
        (folder / "ui.yaml").write_text(template.format(id="ui", scope="frontend"))
        (folder / "api.yaml").write_text(template.format(id="api", scope="backend"))
        self.record_evaluation()
        result = command("curate", "--repo", str(self.repo), cwd=self.repo)
        self.assertNotIn("action: merge", result.stdout)
        self.assertEqual(result.stdout.count("action: mission_local"), 2)

    def test_explicit_context_source_cannot_disappear_silently(self) -> None:
        self.initialize()
        result = command("context", "--repo", str(self.repo), "--objective", "scheduler",
                         "--role", "engineer", "--reference", "README.md", "--max-bytes", "1",
                         cwd=self.repo, ok=False)
        self.assertIn("could not fit the configured budget", result.stderr)

    def test_strengthened_schemas_accept_complete_and_reject_incomplete_records(self) -> None:
        self.initialize(); self.commit_all()
        sha = git(self.repo, "rev-parse", "HEAD")
        command("close", "--repo", str(self.repo), "--objective", "Complete record", "--role", "engineer",
                "--agent", "codex", "--status", "completed", "--start-sha", sha,
                "--acceptance-criterion", "Evidence exists", "--acceptance-outcome", "passed",
                "--file", "README.md", "--check", "test=passed", "--review-cycle", "cycle 1 passed",
                "--finding-resolution", "none", "--risk", "low", "--evidence", "README.md", cwd=self.repo)
        self.commit_all("close")
        command("validate", "--repo", str(self.repo), cwd=self.repo)
        bad = self.repo / ".project-brain/missions/incomplete.yaml"
        bad.write_text('schema_version: "2.0.0"\nartifact_type: mission-result\nid: incomplete\n')
        result = command("validate", "--repo", str(self.repo), cwd=self.repo, ok=False)
        self.assertIn("acceptance_criteria", result.stderr)

    def test_doctor_reports_interpreter_and_dependencies(self) -> None:
        output = command("doctor", cwd=self.repo).stdout
        self.assertIn("required_python", output)
        self.assertIn("install_command", output)
        self.assertIn("PyYAML", output)

    def test_doctor_reports_venv_unsupported_and_missing_dependency_modes(self) -> None:
        venv_env = {**FIXED_ENV, "VIRTUAL_ENV": "/tmp/example-venv"}
        venv = subprocess.run([PYTHON, str(CLI), "doctor"], cwd=self.repo, env=venv_env, text=True, capture_output=True, check=True)
        self.assertIn("virtualenv", venv.stdout)
        unsupported_env = {**FIXED_ENV, "PROJECT_BRAIN_MIN_PYTHON": "99.0"}
        unsupported = subprocess.run([PYTHON, str(CLI), "doctor"], cwd=self.repo, env=unsupported_env, text=True, capture_output=True)
        self.assertEqual(unsupported.returncode, 2)
        self.assertIn("diagnostic-only", unsupported.stdout)
        missing = subprocess.run([PYTHON, "-S", str(CLI), "doctor"], cwd=self.repo, env=FIXED_ENV, text=True, capture_output=True)
        self.assertEqual(missing.returncode, 2)
        self.assertIn("missing_dependencies", missing.stdout)

    def test_migration_is_proposal_only(self) -> None:
        self.initialize(); self.commit_all()
        dry = command("migrate", "--repo", str(self.repo), "--dry-run", cwd=self.repo)
        self.assertIn("automatic_changes: []", dry.stdout)
        command("migrate", "--repo", str(self.repo), cwd=self.repo)
        self.assertTrue(any((self.repo / ".project-brain/evaluations").glob("*schema-v2-migration-plan.md")))

    def test_evaluator_detects_duplicate_lessons(self) -> None:
        self.initialize()
        self.write_proposal("candidate", "Freeze the scheduler clock", "scheduler")
        self.write_confirmed("existing", "Freeze the scheduler clock", "scheduler")
        report = parse_yaml(command("evaluate", "--repo", str(self.repo), cwd=self.repo).stdout)
        item = report["evaluations"][0]
        self.assertEqual(item["novelty"]["classification"], "duplicate")
        self.assertEqual(item["promotion"]["recommendation"], "merge")
        self.assertFalse(item["promotion"]["automatic_promotion"])

    def test_evaluator_detects_contradictory_lessons(self) -> None:
        self.initialize()
        self.write_proposal("candidate", "Do not use wall clock", "scheduler")
        self.write_confirmed("existing", "Use wall clock", "scheduler")
        report = parse_yaml(command("evaluate", "--repo", str(self.repo), cwd=self.repo).stdout)
        item = report["evaluations"][0]
        self.assertEqual(len(item["contradictions"]), 1)
        self.assertEqual(item["promotion"]["recommendation"], "resolve_contradiction")

    def test_contradiction_normalizes_modals_contractions_punctuation_and_scope(self) -> None:
        self.initialize()
        cases = [
            ("Must not use wall clock.", "Must use wall clock"),
            ("Should not cache credentials!", "Should cache credentials"),
            ("Don't publish automatically.", "Do publish automatically"),
            ("Caching credentials is not allowed.", "Caching credentials is allowed"),
        ]
        for index, (negative, positive) in enumerate(cases):
            with self.subTest(negative=negative):
                self.write_proposal(f"candidate-{index}", negative, " Scheduler ")
                self.write_confirmed(f"existing-{index}", positive, "scheduler")
                item = parse_yaml(command(
                    "evaluate", "--repo", str(self.repo), "--learning", f"candidate-{index}", cwd=self.repo,
                ).stdout)["evaluations"][0]
                self.assertEqual(len(item["contradictions"]), 1)
                for path in (self.repo / ".project-brain/lessons/proposed").glob("*.yaml"):
                    path.unlink()
                for path in (self.repo / ".project-brain/lessons/confirmed").glob("*.yaml"):
                    path.unlink()

    def test_evaluator_distinguishes_weak_and_strong_evidence(self) -> None:
        self.initialize()
        self.write_proposal("weak", "Missing evidence cannot support promotion", evidence="[{kind: file, reference: missing.md}]")
        weak = parse_yaml(command("evaluate", "--repo", str(self.repo), "--learning", "weak", cwd=self.repo).stdout)["evaluations"][0]
        self.assertEqual(weak["evidence_quality"]["classification"], "weak")
        self.assertEqual(weak["promotion"]["recommendation"], "needs_evidence")
        (self.repo / "evidence.md").write_text("Security approval policy workflow must require regression test steps.\n")
        (self.repo / "regression.test.ts").write_text("// Security approval policy workflow must require regression test steps.\n")
        (self.repo / "review.md").write_text("Security approval policy workflow must require regression test steps.\n")
        self.write_proposal(
            "strong",
            "Security approval policy workflow must require regression test steps",
            evidence="[{kind: file, reference: evidence.md}, {kind: test, reference: regression.test.ts}, {kind: review, reference: review.md}]",
        )
        strong = parse_yaml(command("evaluate", "--repo", str(self.repo), "--learning", "strong", cwd=self.repo).stdout)["evaluations"][0]
        self.assertEqual(strong["evidence_quality"]["classification"], "strong")
        self.assertEqual(strong["promotion"]["recommendation"], "human_review")

    def test_curator_honors_evaluator_weak_evidence_disposition(self) -> None:
        self.initialize()
        self.write_proposal("weak", "Missing evidence cannot support promotion", evidence="[{kind: file, reference: missing.md}]")
        self.record_evaluation()
        review = parse_yaml(command("curate", "--repo", str(self.repo), cwd=self.repo).stdout)
        recommendation = review["recommendations"][0]
        self.assertEqual(recommendation["action"], "mission_local")
        self.assertIn("does not yet adequately support", recommendation["rationale"])

    def test_curator_rejects_stale_evaluations_after_proposal_changes(self) -> None:
        self.initialize()
        self.write_proposal("claim-change", "Require approval before production changes")
        self.write_proposal("scope-change", "Use repository validation", "repository")
        self.write_proposal("evidence-change", "Preserve inspectable evidence")
        self.record_evaluation()
        claim_path = self.repo / ".project-brain/lessons/proposed/claim-change.yaml"
        claim_path.write_text(claim_path.read_text().replace(
            "Require approval before production changes",
            "Allow production changes without approval",
        ))
        scope_path = self.repo / ".project-brain/lessons/proposed/scope-change.yaml"
        scope_path.write_text(scope_path.read_text().replace("scope: [repository]", "scope: [organization]"))
        evidence_path = self.repo / ".project-brain/lessons/proposed/evidence-change.yaml"
        evidence_path.write_text(evidence_path.read_text().replace("reference: README.md", "reference: missing.md"))
        review = parse_yaml(command("curate", "--repo", str(self.repo), cwd=self.repo).stdout)
        self.assertEqual({item["action"] for item in review["recommendations"]}, {"followup_issue"})
        self.assertTrue(all("changed after evaluation" in item["rationale"] for item in review["recommendations"]))

    def test_curator_preserves_blocker_across_multiple_current_evaluations(self) -> None:
        self.initialize()
        self.write_proposal("weak", "Missing evidence cannot support promotion", evidence="[{kind: file, reference: missing.md}]")
        blocker = self.repo / ".project-brain/evaluations/blocker.yaml"
        command("evaluate", "--repo", str(self.repo), "--output", str(blocker), cwd=self.repo)
        favorable = self.repo / ".project-brain/evaluations/favorable.yaml"
        favorable.write_text(
            blocker.read_text()
            .replace("recommendation: needs_evidence", "recommendation: human_review")
            .replace("primary: mission_local", "primary: policy")
        )
        review = parse_yaml(command("curate", "--repo", str(self.repo), cwd=self.repo).stdout)
        self.assertEqual(review["recommendations"][0]["action"], "mission_local")

    def test_evaluator_classifies_repository_and_organization_scope(self) -> None:
        self.initialize()
        self.write_proposal("repo-lesson", "Use repository fixture", "repository")
        self.write_proposal("org-lesson", "Use shared review policy", "organization")
        report = parse_yaml(command("evaluate", "--repo", str(self.repo), cwd=self.repo).stdout)
        classes = {item["learning_id"]: item["scope_classification"] for item in report["evaluations"]}
        self.assertEqual(classes, {"org-lesson": "organization", "repo-lesson": "repository"})

    def test_evaluator_recommends_multiple_valid_encodings(self) -> None:
        self.initialize()
        (self.repo / "evidence.md").write_text("Security approval policy workflow must require regression test steps.\n")
        (self.repo / "regression.test.ts").write_text("// Security approval policy workflow must require regression test steps.\n")
        (self.repo / "review.md").write_text("Security approval policy workflow must require regression test steps.\n")
        self.write_proposal(
            "multi",
            "Security approval policy workflow must require regression test steps",
            evidence="[{kind: file, reference: evidence.md}, {kind: test, reference: regression.test.ts}, {kind: review, reference: review.md}]",
        )
        item = parse_yaml(command("evaluate", "--repo", str(self.repo), cwd=self.repo).stdout)["evaluations"][0]
        targets = {item["encoding"]["primary"], *(entry["target"] for entry in item["encoding"]["alternatives"])}
        self.assertIn("test", targets)
        self.assertIn("policy", targets)

    def test_evidence_quality_deduplicates_references_and_rejects_kind_laundering(self) -> None:
        self.initialize()
        claim = "Security approval policy requires review"
        (self.repo / "evidence.md").write_text(f"{claim}\n")
        self.write_proposal(
            "laundered",
            claim,
            evidence="[{kind: file, reference: evidence.md}, {kind: test, reference: evidence.md}]",
        )
        item = parse_yaml(command("evaluate", "--repo", str(self.repo), cwd=self.repo).stdout)["evaluations"][0]
        self.assertEqual(item["evidence_quality"]["inspectable"], 1)
        self.assertEqual(item["evidence_quality"]["evidence_kinds"], ["file"])
        self.assertNotEqual(item["evidence_quality"]["classification"], "strong")
        self.assertTrue(any("Duplicate evidence" in issue for issue in item["evidence_quality"]["issues"]))
        self.write_proposal("unsupported-kind", claim, evidence="[{kind: imaginary, reference: evidence.md}]")
        result = command("evaluate", "--repo", str(self.repo), "--learning", "unsupported-kind", cwd=self.repo, ok=False)
        self.assertIn("is not one of", result.stderr)

    def test_evaluator_rejects_unsupported_knowledge_schema(self) -> None:
        self.initialize()
        self.write_proposal("unsupported", "Use repository evidence")
        path = self.repo / ".project-brain/lessons/proposed/unsupported.yaml"
        path.write_text(path.read_text().replace('schema_version: "2.5.0"', 'schema_version: "9.0.0"'))
        result = command("evaluate", "--repo", str(self.repo), cwd=self.repo, ok=False)
        self.assertIn("Unsupported knowledge schema major", result.stderr)

    def test_evaluator_rejects_noncanonical_stored_experience_id(self) -> None:
        self.initialize()
        self.write_proposal("repeatable", "Scheduler validation uses repository evidence", "scheduler")
        report = self.repo / ".project-brain/evaluations/reuse.yaml"
        command(
            "evaluate", "--repo", str(self.repo), "--learning", "repeatable",
            "--experience", "repeatable:reused:README.md", "--output", str(report), cwd=self.repo,
        )
        report.write_text(re.sub(r"(?m)^- id: [a-f0-9]+$", "- id: caller-controlled", report.read_text(), count=1))
        result = command("evaluate", "--repo", str(self.repo), "--learning", "repeatable", cwd=self.repo, ok=False)
        self.assertIn("does not match its canonical evidence tuple", result.stderr)

    def test_confidence_increases_after_repeated_validation(self) -> None:
        self.initialize()
        self.write_proposal("repeatable", "Scheduler validation uses repository evidence", "scheduler")
        first = parse_yaml(command("evaluate", "--repo", str(self.repo), "--learning", "repeatable", cwd=self.repo).stdout)
        first_score = first["evaluations"][0]["confidence"]["score"]
        recorded = self.repo / ".project-brain/evaluations/repeatable-reuse.yaml"
        command(
            "evaluate", "--repo", str(self.repo), "--learning", "repeatable",
            "--experience", "repeatable:reused:README.md", "--output", str(recorded), cwd=self.repo,
        )
        second = parse_yaml(command(
            "evaluate", "--repo", str(self.repo), "--learning", "repeatable", cwd=self.repo,
        ).stdout)
        second_score = second["evaluations"][0]["confidence"]["score"]
        self.assertGreater(second_score, first_score)
        self.assertEqual(second["evaluations"][0]["confidence"]["reused"], 1)
        third = parse_yaml(command("evaluate", "--repo", str(self.repo), "--learning", "repeatable", cwd=self.repo).stdout)
        self.assertEqual(third["evaluations"][0]["confidence"]["reused"], 1)

    def test_status_and_source_mission_changes_require_reevaluation(self) -> None:
        self.initialize()
        self.write_proposal("status-change", "Status changes invalidate evaluation")
        self.write_proposal("mission-change", "Source mission changes invalidate evaluation")
        self.record_evaluation()
        status_path = self.repo / ".project-brain/lessons/proposed/status-change.yaml"
        status_path.write_text(status_path.read_text().replace("status: proposed", "status: confirmed"))
        mission_path = self.repo / ".project-brain/lessons/proposed/mission-change.yaml"
        mission_path.write_text(mission_path.read_text().replace("source_mission: mission-1", "source_mission: mission-2"))
        review = parse_yaml(command("curate", "--repo", str(self.repo), cwd=self.repo).stdout)
        changed = {
            item["learning_id"]: item
            for item in review["recommendations"]
            if item["learning_id"] in {"status-change", "mission-change"}
        }
        self.assertEqual({"followup_issue"}, {item["action"] for item in changed.values()})
        self.assertTrue(all("changed after evaluation" in item["rationale"] for item in changed.values()))

    def test_repeated_evaluation_is_byte_identical(self) -> None:
        self.initialize()
        self.write_proposal("deterministic", "Repository validation uses inspectable evidence")
        first = command("evaluate", "--repo", str(self.repo), "--learning", "deterministic", cwd=self.repo).stdout
        second = command("evaluate", "--repo", str(self.repo), "--learning", "deterministic", cwd=self.repo).stdout
        self.assertEqual(first, second)

    def test_self_authored_proposal_is_not_independent_evidence(self) -> None:
        self.initialize()
        self.write_proposal("source", "Self authored claims are not independent evidence")
        source = ".project-brain/lessons/proposed/source.yaml"
        self.write_proposal(
            "candidate",
            "Self authored claims are not independent evidence",
            evidence=f"[{{kind: file, reference: {source}}}]",
        )
        item = parse_yaml(command(
            "evaluate", "--repo", str(self.repo), "--learning", "candidate", cwd=self.repo,
        ).stdout)["evaluations"][0]
        self.assertEqual(0, item["evidence_quality"]["inspectable"])
        self.assertTrue(any("not independent evidence" in issue for issue in item["evidence_quality"]["issues"]))

    def test_duplicate_experience_input_cannot_inflate_confidence(self) -> None:
        self.initialize()
        self.write_proposal("repeatable", "Repository evidence supports repeatable validation")
        single = parse_yaml(command(
            "evaluate", "--repo", str(self.repo), "--learning", "repeatable",
            "--experience", "repeatable:reused:README.md", cwd=self.repo,
        ).stdout)["evaluations"][0]["confidence"]
        duplicate = parse_yaml(command(
            "evaluate", "--repo", str(self.repo), "--learning", "repeatable",
            "--experience", "repeatable:reused:README.md",
            "--experience", "repeatable:reused:README.md", cwd=self.repo,
        ).stdout)["evaluations"][0]["confidence"]
        self.assertEqual(single["score"], duplicate["score"])
        self.assertEqual(1, duplicate["reused"])

    def test_numeric_confidence_remains_compatible_with_confirmed_lessons(self) -> None:
        self.initialize()
        self.write_confirmed("numeric", "Numeric confidence remains schema compatible")
        result = command("validate", "--repo", str(self.repo), cwd=self.repo)
        self.assertIn("status: valid", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
