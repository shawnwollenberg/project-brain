"""Canonical knowledge identity and comparison primitives."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any


def normalized_claim(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def claim_terms(value: str) -> set[str]:
    stop = {
        "about", "after", "again", "also", "and", "before", "between", "from",
        "have", "into", "only", "should", "that", "the", "their", "this", "when",
        "where", "while", "with",
    }
    return {term for term in re.findall(r"[a-z0-9_-]{3,}", value.lower()) if term not in stop}


def similarity(left: str, right: str) -> float:
    left_terms, right_terms = claim_terms(left), claim_terms(right)
    if not left_terms and not right_terms:
        return 1.0
    union = left_terms | right_terms
    return len(left_terms & right_terms) / len(union) if union else 0.0


def contradiction_key(value: str) -> tuple[str, bool]:
    normalized = (
        normalized_claim(value)
        .replace("don't", "do not")
        .replace("mustn't", "must not")
        .replace("shouldn't", "should not")
        .replace("cannot", "can not")
    )
    tokens = re.findall(r"[a-z0-9_-]+", normalized)
    negative = any(token in {"not", "never", "avoid"} for token in tokens)
    operators = {"always", "avoid", "can", "do", "must", "never", "not", "should"}
    return " ".join(token for token in tokens if token not in operators), negative


def canonical_scope(values: Any) -> list[str]:
    return sorted({str(item).strip().lower() for item in values or [] if str(item).strip()})


def canonical_event_id(learning_id: str, event_type: str, reference: str) -> str:
    return hashlib.sha256(f"{learning_id}:{event_type}:{reference}".encode()).hexdigest()[:16]


def proposal_fingerprint(lesson: dict[str, Any]) -> str:
    evidence_items = sorted(
        (
            str(item.get("kind", "")).strip().lower(),
            str(item.get("reference", "")).strip(),
        )
        for item in lesson.get("evidence", [])
        if isinstance(item, dict)
    )
    payload = {
        "id": str(lesson.get("id", "")).strip(),
        "status": str(lesson.get("status", "")).strip().lower(),
        "claim": normalized_claim(str(lesson.get("claim", ""))),
        "scope": canonical_scope(lesson.get("scope", [])),
        "evidence": evidence_items,
        "source_mission": str(lesson.get("source_mission", "")).strip(),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
