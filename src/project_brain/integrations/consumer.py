"""Narrow consumer operations over existing Project Brain domains."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Callable

from .. import api, core
from .capabilities import capability_report
from .contract import CONTRACT_VERSION, OPERATIONS, compatibility
from .envelopes import artifact_descriptor, envelope


def execute(
    operation: str,
    repo_value: str | Path = ".",
    request: dict[str, Any] | None = None,
    *,
    contract_version: str = CONTRACT_VERSION,
) -> dict[str, Any]:
    """Execute one allowlisted operation and always return a structured envelope."""

    request = request or {}
    if operation not in OPERATIONS:
        return envelope(
            operation=operation,
            status="failed",
            repository=None,
            blockers=[f"Unsupported consumer operation: {operation}"],
            required_actions=["Discover available operations with `project-brain capabilities --json`."],
            exit_classification="unsupported_operation",
        )
    version_state = compatibility(contract_version)
    if version_state in {"unsupported", "older_installed"}:
        return envelope(
            operation=operation,
            status="failed",
            repository=None,
            blockers=[f"Consumer contract {contract_version} is {version_state}; installed contract is {CONTRACT_VERSION}."],
            required_actions=["Install a compatible Project Brain package or request a supported contract version."],
            exit_classification="incompatible_contract",
        )
    try:
        repo = core.repo_root(str(repo_value))
        start_sha = core.git_sha(repo)
        identity = core.repository_identity(repo)
        repository = {
            "id": identity["id"],
            "checkout_path": str(repo),
            "head_sha": start_sha,
        }
        result = _HANDLERS[operation](repo, request)
        artifacts = result.pop("artifacts", [])
        changed = bool(result.pop("repository_files_changed", False))
        human = bool(result.pop("human_approval_required", OPERATIONS[operation]["human_approval_gated"]))
        warnings = list(result.pop("warnings", []))
        if version_state == "older_compatible":
            warnings.append(f"Requested older compatible contract {contract_version}; response uses {CONTRACT_VERSION}.")
        repository["ending_head_sha"] = core.git_sha(repo)
        return envelope(
            operation=operation,
            status="succeeded",
            repository=repository,
            data=result,
            artifacts=artifacts,
            warnings=warnings,
            human_approval_required=human,
            repository_files_changed=changed,
        )
    except (core.BrainError, OSError, ValueError, json.JSONDecodeError) as exc:
        return envelope(
            operation=operation,
            status="failed",
            repository=locals().get("repository"),
            blockers=[str(exc)],
            required_actions=[_repair_action(str(exc))],
            human_approval_required=OPERATIONS[operation]["human_approval_gated"],
            exit_classification=_error_classification(str(exc)),
        )


def _detect(repo: Path, request: dict[str, Any]) -> dict[str, Any]:
    initialized = (repo / ".project-brain").is_dir()
    return {
        "initialized": initialized,
        "state": "detected" if initialized else "not_initialized",
        "profile_path": ".project-brain/project-profile.yaml" if initialized else None,
        "warnings": [] if initialized else ["Project Brain is not initialized; explicit approval is required before initialization."],
    }


def _initialize(repo: Path, request: dict[str, Any]) -> dict[str, Any]:
    if (repo / ".project-brain").exists():
        raise core.BrainError("Repository Project Brain is already initialized.")
    if core.git_dirty(repo):
        raise core.BrainError("Initializing Project Brain requires a clean worktree.")
    result = api.initialize(
        repo,
        dry_run=False,
        repository_id=str(request["repository_id"]) if request.get("repository_id") else None,
    )
    if result.exit_code:
        raise core.BrainError(result.text.strip())
    artifacts = [
        artifact_descriptor(repo, repo / path, "project_brain_initialization", core.VERSION)
        for path in result.changed_files
        if (repo / path).is_file()
    ]
    return {
        "initialization": result.data,
        "artifacts": artifacts,
        "repository_files_changed": bool(artifacts),
        "human_approval_required": True,
    }


def _validate(repo: Path, request: dict[str, Any]) -> dict[str, Any]:
    if not (repo / ".project-brain").is_dir():
        raise core.BrainError("Repository Project Brain is not initialized.")
    core.validate_repo(repo)
    return {"valid": True, "validated_at": core.timestamp(), "schema_versions": _schema_versions(repo)}


def _summary(repo: Path, request: dict[str, Any]) -> dict[str, Any]:
    health = _health(repo, request)
    return {
        "current_state": _read_optional(repo / ".project-brain/current-state.md"),
        "known_issues": _read_optional(repo / ".project-brain/known-issues.md"),
        "knowledge": health["knowledge"],
        "validation": health["validation"],
    }


def _prepare_context(repo: Path, request: dict[str, Any]) -> dict[str, Any]:
    required = ("objective", "role")
    missing = [key for key in required if not request.get(key)]
    if missing:
        raise core.BrainError(f"prepare_context requires: {', '.join(missing)}")
    options = {
        key: request[key]
        for key in (
            "mission_type", "component", "tag", "expected_file", "reference",
            "missing_context", "revision_count", "max_files", "max_bytes",
            "base_sha", "mission_id", "execution_id",
        )
        if key in request
    }
    prepared = api.prepare_context(repo, str(request["objective"]), str(request["role"]), **options)
    if prepared.exit_code:
        raise core.BrainError(prepared.text.strip())
    pack = prepared.data
    artifacts: list[dict[str, Any]] = []
    changed = False
    if request.get("write"):
        if core.git_dirty(repo):
            raise core.BrainError("Writing a context pack requires a clean worktree.")
        mission_id = str(request.get("mission_id") or core.slug(str(request["objective"])))
        target_value = str(request.get("output") or f".project-brain/context-packs/{mission_id}.yaml")
        target = _safe_target(repo, target_value)
        created: list[str] = []
        core.safe_write(target, core.dump_yaml(pack), repo, created)
        changed = bool(created)
        artifacts.append(artifact_descriptor(repo, target, "context_pack", str(pack["schema_version"])))
    return {
        "context_pack": pack,
        "artifacts": artifacts,
        "repository_files_changed": changed,
    }


def _read_context(repo: Path, request: dict[str, Any]) -> dict[str, Any]:
    path = _safe_target(repo, str(request.get("path", "")))
    data = core.load_yaml(path)
    core.validate_data(data, core.ASSET_ROOT / "schemas/context-pack.schema.json")
    return {
        "context_pack": data,
        "artifacts": [artifact_descriptor(repo, path, "context_pack", str(data["schema_version"]))],
    }


def _record_closure(repo: Path, request: dict[str, Any]) -> dict[str, Any]:
    options = dict(request)
    options.pop("context_checksum", None)
    result = api.close_mission(repo, **options)
    if result.exit_code:
        raise core.BrainError(result.text.strip())
    artifacts = [
        artifact_descriptor(repo, repo / path, "mission_result", core.VERSION)
        for path in result.changed_files
    ]
    return {"result": result.data, "artifacts": artifacts, "repository_files_changed": bool(artifacts)}


def _propose(repo: Path, request: dict[str, Any]) -> dict[str, Any]:
    result = api.propose_learning(repo, **request)
    if result.exit_code:
        raise core.BrainError(result.text.strip())
    artifacts = [
        artifact_descriptor(repo, repo / path, "proposed_learning", core.VERSION)
        for path in result.changed_files
    ]
    return {
        "result": result.data,
        "artifacts": artifacts,
        "repository_files_changed": bool(artifacts),
        "human_approval_required": True,
    }


def _evaluate(repo: Path, request: dict[str, Any]) -> dict[str, Any]:
    options = dict(request)
    target = _safe_target(repo, str(options["output"])) if options.get("output") else None
    if target:
        options["output"] = str(target)
    result = api.evaluate(repo, **options)
    if result.exit_code:
        raise core.BrainError(result.text.strip())
    artifacts = (
        [artifact_descriptor(repo, target, "knowledge_evaluation", core.VERSION)]
        if target and target.is_file()
        else []
    )
    return {
        "evaluation": result.data,
        "artifacts": artifacts,
        "repository_files_changed": bool(artifacts),
        "human_approval_required": True,
    }


def _curation(repo: Path, request: dict[str, Any]) -> dict[str, Any]:
    reviews = []
    evaluations = []
    for path in sorted((repo / ".project-brain/evaluations").glob("*.yaml")):
        data = core.load_yaml(path)
        if data.get("artifact_type") == "knowledge-review":
            reviews.append({
                "path": str(path.relative_to(repo)),
                "review": data,
                "sha256": artifact_descriptor(repo, path, "knowledge_review", str(data.get("schema_version")))["sha256"],
            })
        elif data.get("artifact_type") == "knowledge-evaluation":
            evaluations.append({
                "path": str(path.relative_to(repo)),
                "evaluation": data,
                "sha256": artifact_descriptor(
                    repo, path, "knowledge_evaluation", str(data.get("schema_version"))
                )["sha256"],
            })
    return {"reviews": reviews, "evaluations": evaluations, "human_approval_required": True}


def _list_knowledge(repo: Path, request: dict[str, Any]) -> dict[str, Any]:
    statuses = {"proposed": [], "confirmed": [], "stale": [], "superseded": [], "encoded": []}
    for path, data in core.load_knowledge(repo):
        status = str(data.get("status", ""))
        item = {
            "id": str(data.get("id", path.stem)),
            "status": status,
            "title": str(data.get("title", "")),
            "claim": str(data.get("claim", "")),
            "path": str(path.relative_to(repo)),
            "confidence": data.get("confidence"),
        }
        if status in statuses:
            statuses[status].append(item)
    return {"knowledge": statuses}


def _health(repo: Path, request: dict[str, Any]) -> dict[str, Any]:
    initialized = (repo / ".project-brain").is_dir()
    validation_errors: list[str] = []
    if initialized:
        try:
            core.validate_repo(repo)
        except core.BrainError as exc:
            validation_errors.append(str(exc))
    knowledge = _list_knowledge(repo, request)["knowledge"] if initialized else {
        key: [] for key in ("proposed", "confirmed", "stale", "superseded", "encoded")
    }
    evaluations: dict[str, list[dict[str, Any]]] = {}
    contradictions = 0
    awaiting_approval = 0
    confidence: list[float] = []
    if initialized:
        for path in sorted((repo / ".project-brain/evaluations").glob("*.yaml")):
            data = core.load_yaml(path)
            if data.get("artifact_type") != "knowledge-evaluation":
                continue
            for item in data.get("evaluations", []):
                evaluations.setdefault(str(item.get("learning_id")), []).append(item)
                contradictions += len(item.get("contradictions", []))
                if item.get("promotion", {}).get("human_approval") == "required":
                    awaiting_approval += 1
                score = item.get("confidence", {}).get("score")
                if isinstance(score, (int, float)):
                    confidence.append(float(score))
    context_metrics = []
    if initialized:
        for path in sorted((repo / ".project-brain").rglob("*.yaml")):
            try:
                data = core.load_yaml(path)
            except core.BrainError:
                continue
            if data.get("artifact_type") == "context-pack" and isinstance(data.get("context_quality"), dict):
                context_metrics.append(data["context_quality"])
    proposed_ids = {item["id"] for item in knowledge["proposed"]}
    return {
        "brain_initialized": initialized,
        "validation": {
            "valid": initialized and not validation_errors,
            "errors": validation_errors,
            "last_successful_validation": core.timestamp() if initialized and not validation_errors else None,
        },
        "current_state_freshness": _current_state_freshness(repo),
        "knowledge": {key: len(value) for key, value in knowledge.items()},
        "unresolved_contradictions": contradictions,
        "awaiting_evaluation": len(proposed_ids - set(evaluations)),
        "awaiting_human_approval": awaiting_approval,
        "confidence_distribution": _confidence_distribution(confidence),
        "context_pack_count": len(context_metrics),
        "average_context_reduction_percentage": (
            round(sum(float(item.get("reduction_percentage", 0)) for item in context_metrics) / len(context_metrics), 2)
            if context_metrics else None
        ),
        "context_revisions_from_missing_information": sum(
            int(item.get("revision_count", 0)) for item in context_metrics
        ),
        "schema_versions": _schema_versions(repo) if initialized else [],
        "overall_score": None,
    }


def _diagnostics(repo: Path, request: dict[str, Any]) -> dict[str, Any]:
    return {"capabilities": capability_report(), "doctor": core.runtime_report()}


def _schema_versions(repo: Path) -> list[str]:
    versions = set()
    for path in sorted((repo / ".project-brain").rglob("*.yaml")):
        try:
            value = core.load_yaml(path).get("schema_version")
        except core.BrainError:
            continue
        if value:
            versions.add(str(value))
    return sorted(versions)


def _read_optional(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.is_file() else None


def _safe_target(repo: Path, value: str) -> Path:
    candidate = Path(value)
    if not value or candidate.is_absolute() or ".." in candidate.parts:
        raise core.BrainError(f"Artifact path must be safe and repository-relative: {value!r}")
    resolved = (repo / candidate).resolve()
    try:
        resolved.relative_to(repo.resolve())
    except ValueError as exc:
        raise core.BrainError(f"Artifact path escapes repository: {value}") from exc
    return resolved


def _current_state_freshness(repo: Path) -> dict[str, Any]:
    path = repo / ".project-brain/current-state.md"
    if not path.is_file():
        return {"status": "missing", "age_days": None}
    age = max(0, (dt.datetime.now(dt.timezone.utc).timestamp() - path.stat().st_mtime) / 86400)
    return {"status": "current" if age <= 30 else "stale", "age_days": round(age, 2)}


def _confidence_distribution(values: list[float]) -> dict[str, Any]:
    return {
        "count": len(values),
        "low": sum(value < 0.4 for value in values),
        "medium": sum(0.4 <= value < 0.75 for value in values),
        "high": sum(value >= 0.75 for value in values),
        "average": round(sum(values) / len(values), 2) if values else None,
    }


def _error_classification(message: str) -> str:
    lowered = message.lower()
    if "not initialized" in lowered:
        return "not_initialized"
    if "dirty" in lowered or "clean worktree" in lowered:
        return "dirty_worktree"
    if "schema" in lowered:
        return "invalid_schema"
    if "evidence" in lowered:
        return "invalid_evidence"
    if "budget" in lowered or "explicit context source" in lowered:
        return "context_blocked"
    return "operation_failed"


def _repair_action(message: str) -> str:
    classification = _error_classification(message)
    return {
        "not_initialized": "Request explicit approval before running Project Brain initialization.",
        "dirty_worktree": "Commit or safely isolate repository changes, then retry.",
        "invalid_schema": "Validate repository artifacts and install a compatible Project Brain version.",
        "invalid_evidence": "Provide inspectable repository-relative evidence.",
        "context_blocked": "Resolve missing explicit sources or increase the bounded context budget.",
    }.get(classification, "Inspect the blocker and retry the same allowlisted operation.")


_HANDLERS: dict[str, Callable[[Path, dict[str, Any]], dict[str, Any]]] = {
    "detect_repository": _detect,
    "initialize_repository": _initialize,
    "validate_repository": _validate,
    "get_summary": _summary,
    "prepare_context": _prepare_context,
    "read_context": _read_context,
    "record_closure": _record_closure,
    "propose_learning": _propose,
    "evaluate_learning": _evaluate,
    "get_curation": _curation,
    "list_knowledge": _list_knowledge,
    "get_health": _health,
    "diagnostics": _diagnostics,
}
