"""Standalone learning proposal workflow."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def propose_learning(
    repo_value: str | Path,
    *,
    mission_id: str | None = None,
    claim: str | None = None,
    scope: list[str] | None = None,
    evidence: list[str] | None = None,
    proposer: str = "agent",
    title: str | None = None,
    future_behavior: str | None = None,
    confidence: str = "medium",
    suggested_disposition: str = "human-review",
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
    mission_id = mission_id or supplied.get("mission_id") or supplied.get("source_mission")
    claim = claim or supplied.get("claim")
    scope = scope or supplied.get("scope") or ["repository"]
    evidence = evidence or supplied.get("evidence") or []
    proposer = str(supplied.get("proposed_by", proposer))
    title = title or supplied.get("title")
    future_behavior = future_behavior or supplied.get("recommended_future_behavior")
    confidence = str(supplied.get("confidence", confidence))
    suggested_disposition = str(supplied.get("suggested_disposition", suggested_disposition))
    if not mission_id or not claim:
        raise core.BrainError("Proposal requires mission_id and claim.")
    mission_path = _mission_path(repo, str(mission_id), core)
    mission = core.load_yaml(mission_path)
    core.validate_data(mission, core.ASSET_ROOT / "schemas" / "mission-result.schema.json")
    if str(mission.get("id")) != str(mission_id):
        raise core.BrainError(f"Mission ID does not match artifact: {mission_id}")
    core.require_commit(repo, str(mission["start_sha"]), "Mission starting SHA")
    core.require_commit(repo, str(mission["end_sha"]), "Mission ending SHA")
    evidence_items = _evidence_items(repo, evidence, core)
    canonical = {
        "schema_version": core.VERSION,
        "artifact_type": "proposed-learning",
        "id": "",
        "title": str(title or claim)[:80],
        "scope": core.canonical_scope(scope),
        "status": "proposed",
        "claim": str(claim),
        "evidence": evidence_items,
        "confidence": confidence,
        "observed_at": core.today(),
        "recommended_future_behavior": str(future_behavior or claim),
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
        existing = core.load_yaml(target)
        if core.proposal_fingerprint(existing) != canonical["proposal_fingerprint"]:
            raise core.BrainError(f"Stable proposal ID collision at {target.relative_to(repo)}")
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
    direct = repo / ".project-brain/missions" / f"{mission_id}.yaml"
    if direct.is_file():
        return direct
    for path in sorted((repo / ".project-brain/missions").glob("*.yaml")):
        if str(core.load_yaml(path).get("id")) == mission_id:
            return path
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
            kind, reference = (prefix, remainder) if separator and prefix in allowed else ("file", raw)
        if kind not in allowed:
            raise core.BrainError(f"Unsupported evidence kind: {kind}")
        reference = core.require_evidence_reference(repo, reference)
        result[reference] = {"kind": kind, "reference": reference}
    if not result:
        raise core.BrainError("Learning proposal requires at least one inspectable evidence reference.")
    return [result[key] for key in sorted(result)]
