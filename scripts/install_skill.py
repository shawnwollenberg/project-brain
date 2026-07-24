#!/usr/bin/env python3
"""Install, validate, or safely remove the Project Brain Codex skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PACKAGE_VERSION = "0.4.0"
SKILL_ADAPTER_VERSION = "0.4.0"
SUPPORTED_SCHEMAS = ["2.5.0"]
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills" / "codex" / "project-brain"
VALIDATOR = Path.home() / ".codex/skills/.system/skill-creator/scripts/quick_validate.py"
MANIFEST = ".project-brain-install.json"


def digest(path: Path) -> str:
    values = []
    for item in sorted(path.rglob("*")):
        if item.is_file() and item.name != MANIFEST:
            values.append(f"{item.relative_to(path)}:{hashlib.sha256(item.read_bytes()).hexdigest()}")
    return hashlib.sha256("\n".join(values).encode()).hexdigest()


def install(target: Path, force: bool) -> None:
    source_digest = digest(SOURCE)
    if target.exists():
        if digest(target) == source_digest:
            print(f"Project Brain Codex skill adapter {SKILL_ADAPTER_VERSION} already installed at {target}")
            return
        if not force:
            raise SystemExit(f"Refusing to overwrite modified/different skill at {target}; inspect it or rerun with --force.")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = target.with_name(f"{target.name}.backup-{stamp}")
        target.rename(backup)
        print(f"Preserved previous installation at {backup}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE, target)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True
    )
    manifest = {
        "project_brain_package_version": PACKAGE_VERSION,
        "skill_adapter_version": SKILL_ADAPTER_VERSION,
        "installation_source_commit": commit.stdout.strip() if commit.returncode == 0 else None,
        "installed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "supported_schema_versions": SUPPORTED_SCHEMAS,
        "source_digest": source_digest,
    }
    (target / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Installed Project Brain Codex skill adapter {SKILL_ADAPTER_VERSION} for package {PACKAGE_VERSION} at {target}")


def validate(target: Path) -> None:
    if not target.exists():
        raise SystemExit(f"Skill is not installed at {target}")
    if not VALIDATOR.exists():
        raise SystemExit(f"Official Codex skill validator not found at {VALIDATOR}")
    result = subprocess.run([sys.executable, str(VALIDATOR), str(target)], text=True)
    if result.returncode:
        raise SystemExit(result.returncode)
    print(f"Validated Project Brain Codex skill adapter {SKILL_ADAPTER_VERSION} at {target}")


def uninstall(target: Path, force: bool) -> None:
    manifest = target / MANIFEST
    if not target.exists():
        print(f"No Project Brain skill installed at {target}")
        return
    if not manifest.exists() and not force:
        raise SystemExit(f"Refusing to remove unrecognized directory {target}; use --force only after inspection.")
    if manifest.exists():
        expected = json.loads(manifest.read_text()).get("source_digest")
        if digest(target) != expected and not force:
            raise SystemExit(f"Refusing to remove locally modified skill at {target}; inspect it or use --force.")
    shutil.rmtree(target)
    print(f"Removed Project Brain Codex skill adapter {SKILL_ADAPTER_VERSION} from {target}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["install", "validate", "uninstall"])
    parser.add_argument("--target", type=Path, default=Path.home() / ".codex/skills/project-brain")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    target = args.target.expanduser().resolve()
    {"install": install, "validate": lambda path, _: validate(path), "uninstall": uninstall}[args.action](target, args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
