"""Machine-readable consumer capability discovery."""

from __future__ import annotations

import sys
from typing import Any

from .. import core
from .contract import CONTRACT_VERSION, OPERATIONS, SUPPORTED_CONTRACT_VERSIONS


def capability_report() -> dict[str, Any]:
    runtime = core.runtime_report()
    return {
        "core_version": core.PACKAGE_VERSION,
        "consumer_contract_versions": list(SUPPORTED_CONTRACT_VERSIONS),
        "current_consumer_contract_version": CONTRACT_VERSION,
        "supported_artifact_schema_versions": [core.VERSION],
        "operations": OPERATIONS,
        "runtime": {
            "python_version": ".".join(map(str, sys.version_info[:3])),
            "interpreter": sys.executable,
            "supported": runtime["supported"],
            "dependencies_available": not runtime["missing_dependencies"],
        },
        "adapter_compatibility": {
            "skill_adapter_version": runtime["skill_adapter_version"],
            "compatible": runtime["versions_compatible"],
        },
        "feature_flags": {
            "deterministic_context": True,
            "context_quality_metrics": True,
            "knowledge_health": True,
            "automatic_initialization": False,
            "automatic_promotion": False,
            "semantic_retrieval": False,
            "network_service": False,
        },
        "deprecated_interfaces": ["close --learning"],
    }
