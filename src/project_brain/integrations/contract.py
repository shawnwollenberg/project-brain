"""Consumer contract metadata and compatibility rules."""

from __future__ import annotations

from typing import Any

CONTRACT_VERSION = "1.0"
SUPPORTED_CONTRACT_VERSIONS = ("1.0",)

def _op(
    classification: str,
    safe_automatic: bool,
    clean_worktree: bool,
    human_approval: bool,
    git_visible: bool,
) -> dict[str, Any]:
    return {
        "classification": classification,
        "read_only": classification == "read-only",
        "proposal_producing": classification == "proposal-producing",
        "repository_writing": classification == "repository-writing" or git_visible,
        "human_approval_gated": human_approval,
        "safe_for_automatic_execution": safe_automatic,
        "requires_clean_worktree": clean_worktree,
        "creates_git_visible_artifact": git_visible,
    }


OPERATIONS: dict[str, dict[str, Any]] = {
    "detect_repository": _op("read-only", True, False, False, False),
    "initialize_repository": _op("repository-writing", False, True, True, True),
    "validate_repository": _op("read-only", True, False, False, False),
    "get_summary": _op("read-only", True, False, False, False),
    "prepare_context": _op("repository-writing", True, True, False, True),
    "read_context": _op("read-only", True, False, False, False),
    "record_closure": _op("repository-writing", True, True, False, True),
    "propose_learning": _op("proposal-producing", True, True, True, True),
    "evaluate_learning": _op("proposal-producing", True, False, True, False),
    "get_curation": _op("read-only", True, False, True, False),
    "list_knowledge": _op("read-only", True, False, False, False),
    "get_health": _op("read-only", True, False, False, False),
    "diagnostics": _op("read-only", True, False, False, False),
}
OPERATIONS["prepare_context"].update({
    "supports_read_only_preview": True,
    "preview_requires_clean_worktree": False,
    "preview_creates_git_visible_artifact": False,
    "write_request_field": "write",
})


def compatibility(requested: str) -> str:
    """Classify a requested contract without assuming exact package versions."""

    try:
        requested_major, requested_minor = (int(part) for part in requested.split(".", 1))
        current_major, current_minor = (int(part) for part in CONTRACT_VERSION.split(".", 1))
    except (TypeError, ValueError):
        return "unsupported"
    if requested_major != current_major:
        return "unsupported"
    if requested_minor > current_minor:
        return "older_installed"
    if requested_minor < current_minor:
        return "older_compatible"
    return "compatible"
