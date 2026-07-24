"""Stable integration envelopes and artifact descriptors."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .contract import CONTRACT_VERSION


def artifact_descriptor(repo: Path, path: Path, kind: str, schema_version: str | None = None) -> dict[str, Any]:
    resolved = path.resolve()
    root = repo.resolve()
    try:
        relative = str(resolved.relative_to(root))
    except ValueError as exc:
        raise ValueError(f"Integration artifact must remain inside repository: {path}") from exc
    content = resolved.read_bytes()
    return {
        "kind": kind,
        "path": relative,
        "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
        **({"schema_version": schema_version} if schema_version else {}),
    }


def envelope(
    *,
    operation: str,
    status: str,
    repository: dict[str, Any] | None,
    data: Any = None,
    artifacts: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
    blockers: list[str] | None = None,
    required_actions: list[str] | None = None,
    human_approval_required: bool = False,
    repository_files_changed: bool = False,
    exit_classification: str = "success",
) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "operation": operation,
        "status": status,
        "repository": repository,
        "artifacts": artifacts or [],
        "warnings": warnings or [],
        "blockers": blockers or [],
        "required_actions": required_actions or [],
        "human_approval_required": human_approval_required,
        "repository_files_changed": repository_files_changed,
        "exit_classification": exit_classification,
        "data": data,
    }
