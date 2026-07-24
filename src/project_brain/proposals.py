"""Standalone learning proposal workflow."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any


def propose_learning(
    repo_value: str | Path,
    *,
    mission_id: str | None = None,
    claim: str | None = None,
    scope: list[str] | None = None,
    evidence: list[str] | None = None,
    proposer: str | None = None,
    title: str | None = None,
    future_behavior: str | None = None,
    confidence: str | None = None,
    suggested_disposition: str | None = None,
    input_file: str | Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Validate and create one deterministic, non-promoting learning proposal."""

    from . import core
    core.require_runtime()
    repo = core.repo_root(str(repo_value))
    supplied: dict[str, Any] = {}
    if input_file:
        supplied = core.load_yaml(Path(input_file).expanduser().resolve())
        if not isinstance(supplied, dict):
            raise core.BrainError("Structured proposal input must be a YAML mapping.")
    mission_id = mission_id if mission_id is not None else supplied.get("mission_id", supplied.get("source_mission"))
    claim = claim if claim is not None else supplied.get("claim")
    scope = scope if scope is not None else supplied.get("scope", ["repository"])
    evidence = evidence if evidence is not None else supplied.get("evidence", [])
    proposer = str(proposer if proposer is not None else supplied.get("proposed_by", "agent"))
    title = title if title is not None else supplied.get("title")
    future_behavior = future_behavior if future_behavior is not None else supplied.get("recommended_future_behavior")
    confidence = str(confidence if confidence is not None else supplied.get("confidence", "medium"))
    suggested_disposition = str(
        suggested_disposition if suggested_disposition is not None
        else supplied.get("suggested_disposition", "human-review")
    )
    if not mission_id or not claim:
        raise core.BrainError("Proposal requires mission_id and claim.")
    if not isinstance(scope, list) or not all(isinstance(item, str) for item in scope):
        raise core.BrainError("Proposal scope must be a YAML list of strings.")
    if not isinstance(evidence, list):
        raise core.BrainError("Proposal evidence must be a YAML list.")
    mission_path = _mission_path(repo, str(mission_id), core)
    core.ensure_safe(mission_path.read_text(encoding="utf-8"), "originating mission")
    mission = core.load_yaml(mission_path)
    core.validate_data(mission, core.ASSET_ROOT / "schemas" / "mission-result.schema.json")
    if str(mission.get("id")) != str(mission_id):
        raise core.BrainError(f"Mission ID does not match artifact: {mission_id}")
    core.require_commit(repo, str(mission["start_sha"]), "Mission starting SHA")
    core.require_commit(repo, str(mission["end_sha"]), "Mission ending SHA")
    for item in mission.get("evidence", []):
        if isinstance(item, dict) and item.get("kind") == "file":
            core.require_evidence_reference(repo, str(item.get("reference", "")))
    evidence_items = _evidence_items(repo, evidence, core)
    canonical = {
        "schema_version": core.VERSION,
        "artifact_type": "proposed-learning",
        "id": "",
        "title": str(title if title is not None else claim)[:80],
        "scope": core.canonical_scope(scope),
        "status": "proposed",
        "claim": str(claim),
        "evidence": evidence_items,
        "confidence": confidence,
        "observed_at": core.today(),
        "recommended_future_behavior": str(future_behavior if future_behavior is not None else claim),
        "proposed_by": proposer,
        "source_mission": str(mission_id),
        "suggested_disposition": suggested_disposition,
        "contradiction_check": "pending evaluator",
        "duplicate_check": "pending evaluator",
    }
    identity = hashlib.sha256(
        f"{mission_id}:{core.proposal_fingerprint(canonical)}".encode()
    ).hexdigest()[:12]
    canonical["id"] = f"lesson-{identity}"
    canonical["proposal_fingerprint"] = core.proposal_fingerprint(canonical)
    core.validate_data(canonical, core.ASSET_ROOT / "schemas" / "proposed-learning.schema.json")
    rendered = core.dump_yaml(canonical)
    core.ensure_safe(rendered, "proposed learning")
    target = repo / ".project-brain/lessons/proposed" / f"{canonical['id']}.yaml"
    if target.exists():
        existing_text = target.read_text(encoding="utf-8")
        core.ensure_safe(existing_text, "existing proposed learning")
        existing = core.load_yaml(target)
        core.validate_data(existing, core.ASSET_ROOT / "schemas" / "proposed-learning.schema.json")
        stored_fingerprint = str(existing.get("proposal_fingerprint", ""))
        calculated_fingerprint = core.proposal_fingerprint(existing)
        if stored_fingerprint and stored_fingerprint != calculated_fingerprint:
            raise core.BrainError(f"Existing proposal fingerprint is stale or tampered: {target.relative_to(repo)}")
        if core.proposal_fingerprint(existing) != canonical["proposal_fingerprint"]:
            raise core.BrainError(f"Stable proposal ID collision at {target.relative_to(repo)}")
        canonical["observed_at"] = existing.get("observed_at")
        if existing != canonical:
            raise core.BrainError(f"Existing proposal differs outside its stable identity: {target.relative_to(repo)}")
        return {
            "status": "no-op",
            "changed": False,
            "created": [],
            "proposal": canonical,
            "proposal_fingerprint": canonical["proposal_fingerprint"],
        }
    if dry_run:
        return {
            "status": "dry-run",
            "changed": False,
            "created": [],
            "proposed_files": [str(target.relative_to(repo))],
            "proposal": canonical,
            "proposal_fingerprint": canonical["proposal_fingerprint"],
        }
    if core.git_dirty(repo):
        raise core.BrainError("Learning proposal creation requires a clean worktree; use --dry-run to preview.")
    created: list[str] = []
    core.safe_write(target, rendered, repo, created)
    return {
        "status": "created",
        "changed": True,
        "created": created,
        "proposal": canonical,
        "proposal_fingerprint": canonical["proposal_fingerprint"],
        "note": "Proposal only; no evaluation or promotion was performed.",
    }


def _mission_path(repo: Path, mission_id: str, core: Any) -> Path:
    if Path(mission_id).name != mission_id or mission_id in {".", ".."}:
        raise core.BrainError(f"Mission ID must not contain path traversal or separators: {mission_id}")
    missions = (repo / ".project-brain/missions").resolve()
    direct = (missions / f"{mission_id}.yaml").resolve()
    if direct.parent != missions:
        raise core.BrainError(f"Mission path escapes the missions directory: {mission_id}")
    if direct.is_file():
        return direct
    for path in sorted((repo / ".project-brain/missions").glob("*.yaml")):
        resolved = path.resolve()
        if resolved.parent != missions:
            raise core.BrainError(f"Mission artifact escapes the missions directory: {path.relative_to(repo)}")
        if str(core.load_yaml(resolved).get("id")) == mission_id:
            return resolved
    raise core.BrainError(f"Originating mission not found: {mission_id}")


def _evidence_items(repo: Path, entries: list[Any], core: Any) -> list[dict[str, str]]:
    allowed = {"file", "test", "review", "mission", "command", "artifact"}
    result: dict[str, dict[str, str]] = {}
    for entry in entries:
        if isinstance(entry, dict):
            kind, reference = str(entry.get("kind", "")), str(entry.get("reference", ""))
        else:
            raw = str(entry)
            prefix, separator, remainder = raw.partition(":")
            if separator and "/" not in prefix and prefix not in allowed:
                raise core.BrainError(f"Unsupported evidence kind: {prefix}")
            kind, reference = (prefix, remainder) if separator else ("file", raw)
        if kind not in allowed:
            raise core.BrainError(f"Unsupported evidence kind: {kind}")
        reference = core.require_evidence_reference(repo, reference)
        canonical_reference = str((repo / reference).resolve().relative_to(repo.resolve()))
        reference = canonical_reference
        if reference.startswith(".project-brain/lessons/proposed/"):
            raise core.BrainError(f"Proposed or self-authored learning is not independent evidence: {reference}")
        lower_reference = reference.lower()
        if kind == "test" and not re.search(r"(?:^|[/_.-])(?:test|tests|spec|specs)(?:[/_.-]|$)", lower_reference):
            raise core.BrainError(f"Evidence kind test does not reference a recognizable test artifact: {reference}")
        if kind == "review" and not re.search(r"(?:review|evaluation)", lower_reference):
            raise core.BrainError(f"Evidence kind review does not reference a recognizable review artifact: {reference}")
        if kind == "mission" and not reference.startswith(".project-brain/missions/"):
            raise core.BrainError(f"Evidence kind mission must reference a Project Brain mission: {reference}")
        if reference in result and result[reference]["kind"] != kind:
            raise core.BrainError(f"Conflicting evidence kinds for one canonical reference: {reference}")
        result[reference] = {"kind": kind, "reference": reference}
    if not result:
        raise core.BrainError("Learning proposal requires at least one inspectable evidence reference.")
    return [result[key] for key in sorted(result)]
