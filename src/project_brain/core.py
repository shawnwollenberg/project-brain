#!/usr/bin/env python3
"""Provider-neutral, Git-backed Project Brain command line tool."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .knowledge import (
    canonical_event_id,
    canonical_scope,
    claim_terms,
    contradiction_key,
    normalized_claim,
    proposal_fingerprint,
    similarity,
)

try:
    import yaml
    from jsonschema import Draft202012Validator, FormatChecker
    DEPENDENCY_ERROR: ImportError | None = None
except ImportError as exc:
    yaml = None  # type: ignore[assignment]
    Draft202012Validator = None  # type: ignore[assignment]
    FormatChecker = None  # type: ignore[assignment]
    DEPENDENCY_ERROR = exc

VERSION = "2.5.0"
PACKAGE_VERSION = "0.3.0"
SKILL_ADAPTER_VERSION = "0.3.0"
PACKAGE_ROOT = Path(__file__).resolve().parent
ASSET_ROOT = PACKAGE_ROOT / "resources"
SECRET_PATTERNS = [
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[opusr]_[A-Za-z0-9_]{30,}\b")),
    ("bearer token", re.compile(r"(?i)\bauthorization\s*:\s*bearer\s+\S+")),
    ("credential assignment", re.compile(r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*[\"']?[A-Za-z0-9+/=_-]{16,}")),
]
SKIP_PARTS = {".git", "node_modules", "vendor", ".venv", "dist", "build", "coverage"}
TEXT_SUFFIXES = {
    ".md", ".txt", ".ts", ".tsx", ".js", ".jsx", ".go", ".py", ".rs",
    ".java", ".kt", ".sql", ".graphql", ".proto", ".sh", ".yaml", ".yml",
    ".json", ".toml", ".ini", ".rst",
}


class BrainError(RuntimeError):
    pass


def require_runtime() -> None:
    minimum = tuple(int(part) for part in os.environ.get("PROJECT_BRAIN_MIN_PYTHON", "3.8").split(".")[:2])
    if sys.version_info < minimum:
        raise BrainError(
            f"Unsupported Python {sys.version_info.major}.{sys.version_info.minor}; "
            f"Project Brain requires Python {minimum[0]}.{minimum[1]} or newer."
        )
    if DEPENDENCY_ERROR:
        raise BrainError(
            "Missing Python dependencies: PyYAML and jsonschema. Install with "
            f"`{sys.executable} -m pip install PyYAML jsonschema`."
        )


def runtime_report() -> dict[str, Any]:
    missing = []
    if yaml is None:
        missing.append("PyYAML")
    if Draft202012Validator is None:
        missing.append("jsonschema")
    manager = "pip"
    if os.environ.get("VIRTUAL_ENV"):
        manager = "venv + pip"
    elif shutil.which("uv"):
        manager = "uv/pip"
    minimum = tuple(int(part) for part in os.environ.get("PROJECT_BRAIN_MIN_PYTHON", "3.8").split(".")[:2])
    supported = sys.version_info >= minimum
    skill_path = Path(os.environ.get("PROJECT_BRAIN_SKILL_PATH", Path.home() / ".codex/skills/project-brain")).expanduser().resolve()
    manifest_path = skill_path / ".project-brain-install.json"
    manifest: dict[str, Any] = {}
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            manifest = {}
    implementation_files = [
        str(path.relative_to(skill_path))
        for folder in ("scripts", "assets")
        if (skill_path / folder).exists()
        for path in sorted((skill_path / folder).rglob("*"))
        if path.is_file()
    ]
    adapter_version = str(manifest.get("skill_adapter_version", "unknown"))
    compatible = adapter_version == SKILL_ADAPTER_VERSION and not implementation_files
    schema_names = sorted(path.name for path in (ASSET_ROOT / "schemas").glob("*.schema.json"))
    return {
        "core_package_version": PACKAGE_VERSION,
        "skill_adapter_version": adapter_version,
        "versions_compatible": compatible,
        "skill_installation_path": str(skill_path),
        "skill_installed": skill_path.is_dir(),
        "supported_schema_versions": [VERSION],
        "schema_availability": {"available": bool(schema_names), "count": len(schema_names), "schemas": schema_names},
        "implementation_drift": implementation_files,
        "recommended_repair_command": "python3 scripts/install_skill.py install --force",
        "required_python": f">={minimum[0]}.{minimum[1]}",
        "interpreter": sys.executable,
        "python_version": ".".join(map(str, sys.version_info[:3])),
        "supported": supported,
        "environment": "virtualenv" if os.environ.get("VIRTUAL_ENV") else "system",
        "package_manager": manager,
        "dependencies": ["PyYAML", "jsonschema"],
        "missing_dependencies": missing,
        "install_command": f"{sys.executable} -m pip install PyYAML jsonschema",
        "mode": "ready" if supported and not missing else "diagnostic-only",
    }


def run(cmd: list[str], cwd: Path, check: bool = True) -> str:
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if check and result.returncode:
        raise BrainError(result.stderr.strip() or result.stdout.strip() or f"Command failed: {' '.join(cmd)}")
    return result.stdout.strip()


def repo_root(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.exists():
        raise BrainError(f"Repository does not exist: {path}")
    root = run(["git", "rev-parse", "--show-toplevel"], path)
    resolved = Path(root).resolve()
    if resolved != path and not str(path).startswith(str(resolved) + os.sep):
        raise BrainError("Ambiguous repository root")
    return resolved


def git_sha(repo: Path) -> str:
    return run(["git", "rev-parse", "HEAD"], repo)


def require_commit(repo: Path, value: str, label: str) -> str:
    resolved = run(["git", "rev-parse", "--verify", f"{value}^{{commit}}"], repo, check=False)
    if not re.fullmatch(r"[0-9a-f]{40}", resolved):
        raise BrainError(f"{label} does not resolve to a Git commit: {value}")
    return resolved


def require_evidence_reference(repo: Path, value: str) -> str:
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise BrainError(f"Evidence must be a safe repository-relative path: {value}")
    resolved = (repo / candidate).resolve()
    if not str(resolved).startswith(str(repo.resolve()) + os.sep) or not resolved.is_file():
        raise BrainError(f"Evidence reference is not an inspectable repository file: {value}")
    return str(candidate)


def git_dirty(repo: Path) -> list[str]:
    output = run(["git", "status", "--porcelain"], repo)
    return output.splitlines() if output else []


def git_commit_time(repo: Path) -> str:
    return run(["git", "show", "-s", "--format=%cI", "HEAD"], repo)


def today() -> str:
    return os.environ.get("PROJECT_BRAIN_DATE", dt.date.today().isoformat())


def timestamp() -> str:
    return os.environ.get("PROJECT_BRAIN_TIMESTAMP", dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat())


def slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned[:64] or "mission"


def scan_secrets(text: str) -> list[str]:
    return [name for name, pattern in SECRET_PATTERNS if pattern.search(text)]


def ensure_safe(content: str, label: str) -> None:
    findings = scan_secrets(content)
    if findings:
        raise BrainError(f"Refusing to write {label}; likely secret material detected: {', '.join(findings)}")


def dump_yaml(data: dict[str, Any]) -> str:
    require_runtime()
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def safe_write(path: Path, content: str, repo: Path, created: list[str]) -> None:
    resolved_parent = path.parent.resolve()
    if not str(resolved_parent).startswith(str(repo.resolve())):
        raise BrainError(f"Refusing write outside repository: {path}")
    if path.exists():
        return
    ensure_safe(content, str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    created.append(str(path.relative_to(repo)))


def evidence(path: str, kind: str = "file") -> dict[str, str]:
    return {"kind": kind, "reference": path}


def repository_identity(repo: Path, override: str | None = None) -> dict[str, str]:
    remote = run(["git", "remote", "get-url", "origin"], repo, check=False)
    package_name = ""
    package_json = repo / "package.json"
    if package_json.exists():
        try:
            package_name = str(json.loads(package_json.read_text(encoding="utf-8")).get("name", ""))
        except json.JSONDecodeError:
            package_name = ""
    remote_name = ""
    if remote:
        remote_name = re.sub(r"\.git$", "", remote.rstrip("/").split("/")[-1].split(":")[-1])
    source, name = next(
        (pair for pair in (
            ("cli_override", override or ""),
            ("git_remote", remote_name),
            ("package_metadata", package_name),
            ("git_top_level", repo.name),
            ("cwd_fallback", Path.cwd().name),
        ) if pair[1]),
        ("cwd_fallback", "repository"),
    )
    stable_id = slug(name)
    return {
        "id": stable_id,
        "name": name,
        "identity_source": source,
        "checkout_path": str(repo),
        "remote_url": remote,
    }


def detect_profile(repo: Path, identity_override: str | None = None) -> tuple[dict[str, Any], list[str]]:
    signals: list[tuple[str, str, str]] = []
    inferred: list[dict[str, Any]] = []
    commands: dict[str, str] = {}
    languages: list[str] = []
    frameworks: list[str] = []
    package_managers: list[str] = []

    package_json = repo / "package.json"
    if package_json.exists():
        signals.append(("runtime", "Node.js", "package.json"))
        languages.append("JavaScript/TypeScript")
        package = json.loads(package_json.read_text(encoding="utf-8"))
        scripts = package.get("scripts", {})
        for name in ("build", "test", "lint", "typecheck", "deploy"):
            if name in scripts:
                commands[name] = f"npm run {name}"
        deps = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
        for name, label in (("next", "Next.js"), ("react", "React"), ("vite", "Vite"), ("express", "Express")):
            if name in deps:
                frameworks.append(label)
        for lock, manager in (("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"), ("package-lock.json", "npm")):
            if (repo / lock).exists():
                package_managers.append(manager)
                signals.append(("package_manager", manager, lock))
                break
        if not package_managers:
            declared_manager = str(package.get("packageManager", "")).split("@", 1)[0]
            manager = declared_manager if declared_manager else "npm"
            package_managers.append(manager)
            inferred.append({
                "claim": f"package_manager: {manager}",
                "classification": "inferred",
                "evidence": [evidence("package.json")],
                "uncertainty": "No matching lockfile was found; confirm the intended package manager.",
            })
    for marker, language, manager in (
        ("pyproject.toml", "Python", "pip"),
        ("go.mod", "Go", "go"),
        ("Cargo.toml", "Rust", "cargo"),
        ("Gemfile", "Ruby", "bundler"),
    ):
        if (repo / marker).exists():
            languages.append(language)
            package_managers.append(manager)
            signals.append(("language", language, marker))
    if (repo / "Makefile").exists():
        signals.append(("build_system", "Make", "Makefile"))
    docs = sorted(str(p.relative_to(repo)) for p in repo.glob("*.md"))
    docs += sorted(str(p.relative_to(repo)) for p in (repo / "docs").rglob("*.md")) if (repo / "docs").exists() else []
    ci = []
    workflows = repo / ".github" / "workflows"
    if workflows.exists():
        ci = sorted(str(p.relative_to(repo)) for p in workflows.glob("*.y*ml"))
    deploy = [p for p in ("Dockerfile", "docker-compose.yml", "vercel.json", "serverless.yml", "terraform") if (repo / p).exists()]
    profile = {
        "schema_version": VERSION,
        "artifact_type": "project-profile",
        "repository": {**repository_identity(repo, identity_override), "root": ".", "head_sha": git_sha(repo)},
        "detected": {
            "languages": sorted(set(languages)),
            "frameworks": sorted(set(frameworks)),
            "package_managers": sorted(set(package_managers)),
            "commands": commands,
            "ci": ci,
            "deployment": deploy,
            "documentation": docs[:100],
        },
        "observations": [
            {"claim": f"{kind}: {value}", "classification": "observed", "evidence": [evidence(source)]}
            for kind, value, source in signals
        ],
        "inferences": inferred,
        "uncertainties": [] if signals else ["No standard language or build markers were detected."],
        "updated_at": timestamp(),
    }
    return profile, docs


def agents_text() -> str:
    return """# Project Brain

- Treat Git and repository documentation as the source of truth.
- Read `.project-brain/current-state.md` and only task-relevant knowledge before work.
- Separate observed facts from inferences and cite repository evidence.
- Store mission outcomes under `.project-brain/missions/`.
- Store new lessons under `.project-brain/lessons/proposed/`; never self-confirm them.
- Never store secrets, credential values, hidden reasoning, or raw model transcripts.
- Validate Project Brain YAML before completing work.
- Encode durable confirmed lessons in tests, scripts, skills, or policies when practical.
"""


def init_command(args: argparse.Namespace) -> int:
    require_runtime()
    repo = repo_root(args.repo)
    dirty = git_dirty(repo)
    profile, docs = detect_profile(repo, args.repository_id)
    brain = repo / ".project-brain"
    planned = [
        ".project-brain/README.md", ".project-brain/project-profile.yaml",
        ".project-brain/current-state.md", ".project-brain/known-issues.md",
        ".project-brain/schemas/*", ".project-brain/templates/*",
    ]
    existing_agents = (repo / "AGENTS.md").exists()
    planned.append(".project-brain/evaluations/agents-merge-proposal.md" if existing_agents else "AGENTS.md")
    report = {
        "mode": "dry-run" if args.dry_run else "apply",
        "repository": str(repo),
        "head_sha": git_sha(repo),
        "worktree": "dirty" if dirty else "clean",
        "dirty_entries": dirty,
        "planned": planned,
        "detected": profile["detected"],
        "facts": profile["observations"],
        "inferences": profile["inferences"],
        "uncertainties": profile["uncertainties"],
        "would_block_apply": bool(dirty),
    }
    if args.dry_run:
        print(dump_yaml(report), end="")
        return 0
    if dirty:
        raise BrainError("Initialization requires a clean worktree. Commit or stash changes, or run with --dry-run.")
    created: list[str] = []
    safe_write(brain / "README.md", (ASSET_ROOT / "README.md").read_text(), repo, created)
    safe_write(brain / "project-profile.yaml", dump_yaml(profile), repo, created)
    state = f"# Current state\n\nObserved at `{git_sha(repo)}` on {today()}.\n\n## Verified\n\n- Repository profile generated from tracked configuration and documentation signals.\n\n## Uncertainties\n\n" + "".join(f"- {item}\n" for item in profile["uncertainties"]) if profile["uncertainties"] else f"# Current state\n\nObserved at `{git_sha(repo)}` on {today()}.\n\n## Verified\n\n- Repository profile generated from tracked configuration and documentation signals.\n\n## Uncertainties\n\n- None recorded.\n"
    safe_write(brain / "current-state.md", state, repo, created)
    safe_write(brain / "known-issues.md", "# Known issues\n\nNo evidence-backed issues have been recorded.\n", repo, created)
    for directory in ("architecture", "decisions", "lessons/confirmed", "lessons/proposed", "lessons/stale", "lessons/superseded", "playbooks", "evaluations", "missions"):
        (brain / directory).mkdir(parents=True, exist_ok=True)
    for source in (ASSET_ROOT / "schemas").glob("*.json"):
        safe_write(brain / "schemas" / source.name, source.read_text(), repo, created)
    for source in (ASSET_ROOT / "templates").glob("*"):
        safe_write(brain / "templates" / source.name, source.read_text(), repo, created)
    if existing_agents:
        proposal = "# AGENTS.md merge proposal\n\nPreserve the existing file. Consider adding this scoped section:\n\n```markdown\n" + agents_text() + "```\n"
        safe_write(brain / "evaluations" / "agents-merge-proposal.md", proposal, repo, created)
    else:
        safe_write(repo / "AGENTS.md", agents_text(), repo, created)
    validate_repo(repo)
    print(dump_yaml({"status": "initialized", "repository": str(repo), "created": created, "head_sha": git_sha(repo)}), end="")
    return 0


def candidate_files(repo: Path) -> list[Path]:
    tracked = run(["git", "ls-files"], repo).splitlines()
    result = []
    for value in tracked:
        path = repo / value
        if any(part in SKIP_PARTS for part in path.parts) or not path.is_file():
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in {"AGENTS.md", "Makefile"}:
            result.append(path)
    return result


def context_command(args: argparse.Namespace) -> int:
    require_runtime()
    repo = repo_root(args.repo)
    terms = set(re.findall(r"[a-z0-9_-]{3,}", f"{args.objective} {args.role} {args.mission_type or ''} {args.component or ''} {' '.join(args.tag)}".lower()))
    explicit = {str(Path(p)) for p in args.reference}
    expected = {str(Path(p)) for p in args.expected_file}
    available = {str(path.relative_to(repo)) for path in candidate_files(repo)}
    missing_explicit = sorted(explicit - available)
    if missing_explicit:
        raise BrainError(f"Explicit context source is missing or unsupported: {', '.join(missing_explicit)}")
    expected_dirs = {
        value.rstrip("/") for value in expected
        if value.endswith("/") or (repo / value).is_dir()
    }
    changed = set(run(["git", "diff", "--name-only", f"{args.base_sha}...HEAD"], repo, check=False).splitlines()) if args.base_sha else set()
    ranked = []
    for path in candidate_files(repo):
        rel = str(path.relative_to(repo))
        if scan_secrets(rel):
            continue
        score, reasons = 0, []
        if rel in explicit:
            score += 1000; reasons.append("explicit reference")
        if rel in expected:
            score += 700; reasons.append("expected file")
        if any(rel.startswith(f"{directory}/") for directory in expected_dirs):
            score += 350; reasons.append("expected parent path")
        if rel in changed:
            score += 600; reasons.append("changed file")
        lower = rel.lower()
        filename_hits = sorted(term for term in terms if term in lower)
        if filename_hits:
            score += 100 + len(filename_hits); reasons.append("objective terms in path")
        try:
            sample = path.read_text(encoding="utf-8", errors="ignore")[:8000].lower()
        except OSError:
            continue
        content_hits = sorted(term for term in terms if term in sample)
        if content_hits:
            score += min(50, len(content_hits) * 5); reasons.append("objective terms in bounded content")
        if args.component and args.component.lower() in rel.lower() and score:
            score += 80; reasons.append("component match")
        if rel.startswith(".project-brain/") and score:
            score += 100; reasons.append("repository knowledge")
        if rel in {"package.json", "pyproject.toml", "go.mod", "Cargo.toml"}:
            score += 180; reasons.append("project metadata")
        if rel in {"AGENTS.md", ".project-brain/current-state.md", ".project-brain/project-profile.yaml"}:
            score += 300; reasons.append("repository operating context")
        if score:
            ranked.append((-score, rel, path, reasons))
    ranked.sort()
    selected, omitted, total = [], [], 0
    for neg_score, rel, path, reasons in ranked:
        size = path.stat().st_size
        if len(selected) >= args.max_files or total + size > args.max_bytes:
            if rel in explicit or rel in expected:
                omitted.append({"path": rel, "reason": "file or byte budget exceeded"})
            continue
        selected.append({
            "path": rel, "reason": "; ".join(reasons), "bytes": size,
            "estimated_tokens": max(1, (size + 3) // 4),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
        total += size
    omitted_explicit = sorted(explicit - {item["path"] for item in selected})
    if omitted_explicit:
        raise BrainError(f"Explicit context source could not fit the configured budget: {', '.join(omitted_explicit)}")
    pack = {
        "schema_version": VERSION, "artifact_type": "context-pack",
        "objective": args.objective, "role": args.role, "repository_sha": git_sha(repo),
        "selection": {"strategy": "deterministic-v2", "sources": selected, "omitted_sources": omitted, "total_bytes": total, "estimated_tokens": (total + 3) // 4},
        "created_at": git_commit_time(repo),
    }
    validate_data(pack, ASSET_ROOT / "schemas" / "context-pack.schema.json")
    output = dump_yaml(pack)
    ensure_safe(output, "context pack")
    if args.output:
        Path(args.output).expanduser().resolve().write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


def close_command(args: argparse.Namespace) -> int:
    require_runtime()
    repo = repo_root(args.repo)
    dirty = git_dirty(repo)
    if dirty:
        raise BrainError("Mission closure requires a clean worktree so the end SHA and evidence are unambiguous.")
    if args.status == "completed" and not args.evidence:
        raise BrainError("Completed missions require at least one evidence reference.")
    start_sha = require_commit(repo, args.start_sha, "Starting SHA")
    checked_evidence = [require_evidence_reference(repo, item) for item in args.evidence]
    mission_id = f"{today()}-{slug(args.objective)}"
    checks = []
    for item in args.check:
        command, sep, result = item.rpartition("=")
        checks.append({"command": command if sep else item, "result": result if sep else "recorded"})
    result = {
        "schema_version": VERSION, "artifact_type": "mission-result", "id": mission_id,
        "objective": args.objective, "role": args.role, "agent": args.agent, "status": args.status,
        "start_sha": start_sha, "end_sha": require_commit(repo, "HEAD", "Ending SHA"),
        "acceptance_criteria": args.acceptance_criterion,
        "acceptance_outcome": args.acceptance_outcome,
        "files_changed": args.file,
        "checks": checks, "review_cycles": args.review_cycle,
        "findings_and_resolutions": args.finding_resolution,
        "risks": args.risk,
        "evidence": [evidence(item) for item in checked_evidence],
        "artifacts": args.artifact, "state_updates": args.state_update,
        "follow_ups": args.follow_up, "completed_at": timestamp(),
    }
    validate_data(result, ASSET_ROOT / "schemas" / "mission-result.schema.json")
    created: list[str] = []
    brain = repo / ".project-brain"
    safe_write(brain / "missions" / f"{mission_id}.yaml", dump_yaml(result), repo, created)
    if args.learning:
        lesson_id = f"lesson-{hashlib.sha256((args.learning + args.objective).encode()).hexdigest()[:12]}"
        lesson = {
            "schema_version": VERSION, "artifact_type": "proposed-learning", "id": lesson_id,
            "title": args.learning[:80], "scope": args.scope or ["repository"], "status": "proposed",
            "claim": args.learning, "evidence": [evidence(item) for item in checked_evidence],
            "confidence": args.confidence, "observed_at": today(), "verified_at": None,
            "superseded_by": None, "recommended_future_behavior": args.future_behavior or args.learning,
            "proposed_by": args.proposer, "source_mission": mission_id,
            "suggested_disposition": args.suggested_disposition,
            "contradiction_check": "pending independent curation",
            "duplicate_check": "pending independent curation",
        }
        validate_data(lesson, ASSET_ROOT / "schemas" / "proposed-learning.schema.json")
        safe_write(brain / "lessons" / "proposed" / f"{lesson_id}.yaml", dump_yaml(lesson), repo, created)
    print(dump_yaml({"status": "closed", "created": created, "mission_id": mission_id}), end="")
    return 0


def load_yaml(path: Path) -> dict[str, Any]:
    require_runtime()
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise BrainError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise BrainError(f"Expected YAML mapping in {path}")
    return value


def curate_command(args: argparse.Namespace) -> int:
    require_runtime()
    repo = repo_root(args.repo)
    brain = repo / ".project-brain"
    proposals = [(p, load_yaml(p)) for p in sorted((brain / "lessons" / "proposed").glob("*.yaml"))]
    confirmed = [
        (p, load_yaml(p))
        for folder in ("confirmed", "stale", "superseded")
        for p in sorted((brain / "lessons" / folder).glob("*.yaml"))
    ]
    recommendations = []
    seen: dict[tuple[str, tuple[str, ...]], str] = {}
    dispositions = {
        "reject", "mission_local", "merge", "confirm", "adr", "playbook",
        "test", "policy", "followup_issue", "stale", "supersede",
    }
    evaluated: dict[str, list[dict[str, Any]]] = {}
    for evaluation_path in sorted((brain / "evaluations").glob("*.yaml")):
        evaluation = load_yaml(evaluation_path)
        if evaluation.get("artifact_type") == "knowledge-evaluation":
            validate_data(evaluation, ASSET_ROOT / "schemas" / "knowledge-evaluation.schema.json")
            for item in evaluation.get("evaluations", []):
                evaluated.setdefault(str(item.get("learning_id")), []).append(item)
    for path, lesson in proposals:
        claim = re.sub(r"\s+", " ", str(lesson.get("claim", "")).strip().lower())
        scope = tuple(sorted(str(item).strip().lower() for item in lesson.get("scope", [])))
        scoped_claim = (claim, scope)
        suggested = str(lesson.get("suggested_disposition", "confirm"))
        action = suggested if suggested in dispositions else "confirm"
        reason = f"Evidence-backed proposal suggests {action}; no exact duplicate was found."
        learning_id = str(lesson.get("id", path.stem))
        expected_fingerprint = proposal_fingerprint(lesson)
        candidates = evaluated.get(learning_id, [])
        current_candidates = [
            item for item in candidates
            if item.get("proposal_fingerprint") == expected_fingerprint
        ]
        evaluator_priority = {
            "resolve_contradiction": 0,
            "needs_evidence": 1,
            "mission_local": 2,
            "merge": 3,
            "human_review": 4,
        }
        evaluation = min(
            current_candidates,
            key=lambda item: (
                evaluator_priority.get(str(item.get("promotion", {}).get("recommendation")), -1),
                str(item.get("proposal_fingerprint", "")),
            ),
            default=None,
        )
        evaluator_lock = False
        if not evaluation:
            if candidates:
                action, reason, evaluator_lock = (
                    "followup_issue",
                    "The proposal changed after evaluation; rerun the Knowledge Evaluator before curation.",
                    True,
                )
            else:
                action, reason = "followup_issue", "Run the deterministic Knowledge Evaluator before making a curation recommendation."
                evaluator_lock = True
        if evaluation:
            promotion = evaluation.get("promotion", {})
            evaluator_recommendation = promotion.get("recommendation")
            evaluator_reason = str(promotion.get("rationale", "Knowledge Evaluator recommendation."))
            encoding_target = str(evaluation.get("encoding", {}).get("primary", "lesson"))
            encoding_action = {
                "lesson": "confirm",
                "adr": "adr",
                "playbook": "playbook",
                "test": "test",
                "policy": "policy",
                "followup_issue": "followup_issue",
                "mission_local": "mission_local",
            }.get(encoding_target, "confirm")
            if evaluator_recommendation == "resolve_contradiction":
                action, reason, evaluator_lock = "followup_issue", evaluator_reason, True
            elif evaluator_recommendation == "needs_evidence":
                action, reason, evaluator_lock = "mission_local", evaluator_reason, True
            elif evaluator_recommendation == "mission_local":
                action, reason, evaluator_lock = "mission_local", evaluator_reason, True
            elif evaluator_recommendation == "merge":
                action, reason, evaluator_lock = "merge", evaluator_reason, True
            elif evaluator_recommendation == "human_review":
                action, reason = encoding_action, evaluator_reason
            else:
                action, reason, evaluator_lock = "followup_issue", "Evaluator result is unsupported; human inspection is required.", True
        if evaluator_lock:
            pass
        elif not lesson.get("evidence"):
            action, reason = "reject", "Evidence is missing."
        elif scoped_claim in seen:
            action, reason = "merge", f"Exact duplicate of {seen[scoped_claim]} in the same scope."
        else:
            canonical = re.sub(r"\b(?:do not|don't|never|not)\b", "", claim)
            canonical = re.sub(r"\s+", " ", canonical).strip()
            conflict_id = next(
                (prior_id for (prior_claim, prior_scope), prior_id in seen.items()
                 if set(scope).intersection(prior_scope)
                 and re.sub(r"\s+", " ", re.sub(r"\b(?:do not|don't|never|not)\b", "", prior_claim)).strip() == canonical
                 and prior_claim != claim),
                None,
            )
            if conflict_id:
                action, reason = "followup_issue", f"Potential conflict with {conflict_id}; human resolution required."
            for other_path, other in confirmed:
                other_claim = re.sub(r"\s+", " ", str(other.get("claim", "")).strip().lower())
                other_scope = tuple(sorted(str(item).strip().lower() for item in other.get("scope", [])))
                if claim == other_claim and scope == other_scope:
                    lifecycle = other_path.parent.name
                    if lifecycle == "stale":
                        action, reason = "confirm", f"Matches stale knowledge in {other_path.name}; human revalidation is required."
                    elif lifecycle == "superseded":
                        action, reason = "reject", f"Matches superseded knowledge in {other_path.name}; inspect its replacement before reconsidering."
                    else:
                        action, reason = "reject", f"Already confirmed in {other_path.name}."
                    break
        seen.setdefault(scoped_claim, str(lesson.get("id", path.stem)))
        target = {
            "confirm": "lessons/confirmed",
            "merge": "existing learning",
            "followup_issue": "issue tracker",
            "reject": "none",
            "mission_local": "originating mission",
            "adr": "decisions",
            "playbook": "playbooks",
            "test": "repository test suite",
            "policy": "repository policy",
            "stale": "lessons/stale",
            "supersede": "superseded learning",
        }.get(action, "human-selected target")
        recommendations.append({
            "learning_id": learning_id,
            "action": action,
            "rationale": reason,
            "target": target,
            "human_approval": "required",
            "resulting_status": "proposed",
            "evidence": lesson.get("evidence", []),
        })
    review = {
        "schema_version": VERSION, "artifact_type": "knowledge-review",
        "repository_sha": git_sha(repo), "reviewer": args.reviewer,
        "recommendations": recommendations, "generated_at": timestamp(),
        "note": "Recommendations only; no lesson lifecycle files were modified.",
    }
    validate_data(review, ASSET_ROOT / "schemas" / "knowledge-review.schema.json")
    if args.output:
        Path(args.output).expanduser().resolve().write_text(dump_yaml(review), encoding="utf-8")
    else:
        print(dump_yaml(review), end="")
    if args.patch_output:
        lines = ["# Knowledge review patch proposal", "", "No lifecycle files were changed.", ""]
        for item in recommendations:
            lines += [f"## {item['learning_id']}", "", f"- Recommended action: `{item['action']}`", f"- Rationale: {item['rationale']}", f"- Human approval: `{item['human_approval']}`", ""]
        Path(args.patch_output).expanduser().resolve().write_text("\n".join(lines), encoding="utf-8")
    return 0


def load_knowledge(repo: Path) -> list[tuple[Path, dict[str, Any]]]:
    brain = repo / ".project-brain" / "lessons"
    result = []
    for folder in ("proposed", "confirmed", "stale", "superseded"):
        for path in sorted((brain / folder).glob("*.yaml")):
            data = load_yaml(path)
            major = str(data.get("schema_version", "0")).split(".", 1)[0]
            if major not in {"1", "2"}:
                raise BrainError(f"Unsupported knowledge schema major in {path}: {data.get('schema_version')!r}")
            artifact = str(data.get("artifact_type", ""))
            if artifact not in {"proposed-learning", "confirmed-learning"}:
                raise BrainError(f"Unsupported knowledge artifact in {path}: {artifact!r}")
            local_schema = repo / ".project-brain" / "schemas" / f"{artifact}.schema.json"
            schema = local_schema if major == "1" and local_schema.exists() else ASSET_ROOT / "schemas" / f"{artifact}.schema.json"
            validate_data(data, schema)
            result.append((path, data))
    return result


def experience_events(repo: Path, raw_events: list[str]) -> list[dict[str, str]]:
    events: dict[str, dict[str, str]] = {}
    for path in sorted((repo / ".project-brain" / "evaluations").glob("*.yaml")):
        data = load_yaml(path)
        if data.get("artifact_type") != "knowledge-evaluation":
            continue
        validate_data(data, ASSET_ROOT / "schemas" / "knowledge-evaluation.schema.json")
        for event in data.get("experience_events", []):
            if isinstance(event, dict) and event.get("id"):
                learning_id = str(event.get("learning_id", ""))
                event_type = str(event.get("event", ""))
                reference = require_evidence_reference(repo, str(event.get("evidence", "")))
                expected_id = canonical_event_id(learning_id, event_type, reference)
                if str(event["id"]) != expected_id:
                    raise BrainError(f"Experience event ID does not match its canonical evidence tuple: {event['id']}")
                events[expected_id] = {
                    "id": expected_id,
                    "learning_id": learning_id,
                    "event": event_type,
                    "evidence": reference,
                }
    for raw in raw_events:
        parts = raw.split(":", 2)
        if len(parts) != 3:
            raise BrainError("Experience must use learning-id:event:repository-relative-evidence")
        learning_id, event_type, reference = parts
        if event_type not in {"observed", "reused", "contradicted", "superseded"}:
            raise BrainError(f"Unsupported experience event: {event_type}")
        reference = require_evidence_reference(repo, reference)
        event_id = canonical_event_id(learning_id, event_type, reference)
        events[event_id] = {
            "id": event_id,
            "learning_id": learning_id,
            "event": event_type,
            "evidence": reference,
        }
    return [events[key] for key in sorted(events)]


def evaluate_evidence(repo: Path, lesson_path: Path, lesson: dict[str, Any]) -> dict[str, Any]:
    entries = lesson.get("evidence", [])
    inspectable, kinds, support_terms, issues = 0, set(), set(), []
    seen_references = set()
    allowed_kinds = {"file", "test", "review", "mission", "command", "artifact"}
    terms = claim_terms(str(lesson.get("claim", "")))
    for item in entries:
        if not isinstance(item, dict):
            issues.append("Evidence entry is not structured.")
            continue
        kind, reference = str(item.get("kind", "")), str(item.get("reference", ""))
        if kind not in allowed_kinds:
            issues.append(f"Unsupported evidence kind: {kind or '<missing kind>'}")
            continue
        candidate = repo / reference
        resolved = candidate.resolve()
        unsafe = (
            not reference
            or Path(reference).is_absolute()
            or ".." in Path(reference).parts
            or not str(resolved).startswith(str(repo.resolve()) + os.sep)
            or not resolved.is_file()
        )
        if unsafe:
            issues.append(f"Evidence is not inspectable: {reference or '<missing reference>'}")
            continue
        canonical_reference = str(resolved.relative_to(repo.resolve()))
        if canonical_reference in seen_references:
            issues.append(f"Duplicate evidence reference does not add independent support: {reference}")
            continue
        if resolved == lesson_path.resolve() or canonical_reference.startswith(".project-brain/lessons/proposed/"):
            issues.append(f"Proposed or self-authored learning is not independent evidence: {reference}")
            continue
        lower_reference = canonical_reference.lower()
        if kind == "test" and not re.search(r"(?:^|[/_.-])(?:test|tests|spec|specs)(?:[/_.-]|$)", lower_reference):
            issues.append(f"Evidence kind test does not reference a recognizable test artifact: {reference}")
            continue
        if kind == "review" and not re.search(r"(?:review|evaluation)", lower_reference):
            issues.append(f"Evidence kind review does not reference a recognizable review artifact: {reference}")
            continue
        if kind == "mission" and not canonical_reference.startswith(".project-brain/missions/"):
            issues.append(f"Evidence kind mission must reference a Project Brain mission: {reference}")
            continue
        seen_references.add(canonical_reference)
        kinds.add(kind)
        inspectable += 1
        try:
            support_terms |= terms & claim_terms(candidate.read_text(encoding="utf-8", errors="ignore")[:16000])
        except OSError:
            issues.append(f"Evidence could not be read: {reference}")
    total = len(entries)
    inspect_ratio = inspectable / total if total else 0.0
    support_ratio = len(support_terms) / len(terms) if terms else 0.0
    diversity = min(1.0, len(kinds) / 3)
    quantity = min(1.0, inspectable / 3)
    score = round(0.45 * inspect_ratio + 0.3 * support_ratio + 0.15 * diversity + 0.1 * quantity, 2)
    classification = "strong" if score >= 0.75 else "adequate" if score >= 0.5 else "weak"
    return {
        "score": score,
        "classification": classification,
        "inspectable": inspectable,
        "total": total,
        "evidence_kinds": sorted(kinds),
        "claim_terms_supported": sorted(support_terms),
        "issues": issues,
    }


def encoding_recommendations(lesson: dict[str, Any], evidence_review: dict[str, Any]) -> dict[str, Any]:
    claim = normalized_claim(str(lesson.get("claim", "")))
    tokens = claim_terms(claim)
    scores = {
        "lesson": 0.5,
        "adr": 0.2,
        "playbook": 0.2,
        "test": 0.2,
        "policy": 0.2,
        "followup_issue": 0.1,
        "mission_local": 0.1,
    }
    keywords = {
        "adr": ("architecture", "decision", "tradeoff", "choose", "selected"),
        "playbook": ("workflow", "process", "onboarding", "operate", "procedure", "steps"),
        "test": ("test", "regression", "failure", "bug", "deterministic"),
        "policy": ("must", "never", "approval", "security", "prohibit", "require"),
        "followup_issue": ("todo", "follow-up", "incomplete", "missing"),
    }
    for target, words in keywords.items():
        scores[target] += 0.18 * sum(
            1 for word in words
            if (
                any(token in {word, f"{word}s", f"{word}es"} for token in tokens)
                if " " not in word
                else bool(re.search(rf"\b{re.escape(word)}\b", claim))
            )
        )
    evidence_kinds = set(evidence_review["evidence_kinds"])
    if "test" in evidence_kinds:
        scores["test"] += 0.35
    if evidence_review["score"] < 0.5:
        scores["mission_local"] += 0.6
        scores["followup_issue"] += 0.25
    ranked = sorted(((round(min(score, 1.0), 2), target) for target, score in scores.items()), key=lambda item: (-item[0], item[1]))
    primary_score, primary = ranked[0]
    alternatives = [
        {"target": target, "score": score, "rationale": f"Deterministic encoding signals support {target}."}
        for score, target in ranked[1:4] if score >= max(0.45, primary_score - 0.25)
    ]
    return {
        "primary": primary,
        "primary_score": primary_score,
        "rationale": f"{primary} has the strongest deterministic keyword, evidence-kind, and evidence-quality signals.",
        "alternatives": alternatives,
    }


def evaluate_command(args: argparse.Namespace) -> int:
    require_runtime()
    repo = repo_root(args.repo)
    knowledge = load_knowledge(repo)
    proposals = [(path, lesson) for path, lesson in knowledge if lesson.get("status") == "proposed"]
    if args.learning:
        requested = set(args.learning)
        proposals = [(path, lesson) for path, lesson in proposals if str(lesson.get("id")) in requested or path.name in requested]
        missing = requested - {str(lesson.get("id")) for _, lesson in proposals} - {path.name for path, _ in proposals}
        if missing:
            raise BrainError(f"Proposed learning not found: {', '.join(sorted(missing))}")
    events = experience_events(repo, args.experience)
    evaluations = []
    for path, lesson in proposals:
        learning_id = str(lesson.get("id", path.stem))
        claim = str(lesson.get("claim", ""))
        scope = canonical_scope(lesson.get("scope", []))
        evidence_review = evaluate_evidence(repo, path, lesson)
        matches, contradictions = [], []
        canonical, negative = contradiction_key(claim)
        for other_path, other in knowledge:
            if other_path == path:
                continue
            other_claim = str(other.get("claim", ""))
            overlap = similarity(claim, other_claim)
            same_scope = bool(set(scope) & set(canonical_scope(other.get("scope", []))))
            if overlap >= 0.45:
                matches.append({
                    "learning_id": str(other.get("id", other_path.stem)),
                    "status": str(other.get("status", "unknown")),
                    "similarity": round(overlap, 2),
                    "same_scope": same_scope,
                })
            other_canonical, other_negative = contradiction_key(other_claim)
            if canonical == other_canonical and negative != other_negative and same_scope:
                contradictions.append({
                    "learning_id": str(other.get("id", other_path.stem)),
                    "claim": other_claim,
                    "status": str(other.get("status", "unknown")),
                    "evidence": other.get("evidence", []),
                })
        max_similarity = max((item["similarity"] for item in matches if item["same_scope"]), default=0.0)
        novelty_score = round(max(0.0, 1.0 - max_similarity), 2)
        novelty_class = "new" if novelty_score >= 0.75 else "overlap" if novelty_score >= 0.35 else "duplicate"
        lesson_events = [event for event in events if event["learning_id"] == learning_id]
        counts = {
            event: sum(1 for item in lesson_events if item["event"] == event)
            for event in ("observed", "reused", "contradicted", "superseded")
        }
        counts["observed"] += 1
        positive = counts["observed"] + 2 * counts["reused"] + 1
        negative_count = 2 * counts["contradicted"] + 2 * counts["superseded"] + 2
        confidence_score = round(evidence_review["score"] * positive / (positive + negative_count), 2)
        confidence_level = "high" if confidence_score >= 0.75 else "medium" if confidence_score >= 0.4 else "low"
        organization_terms = {"organization", "organizational", "cross-repository", "shared", "company", "all-repositories"}
        scope_kind = "organization" if organization_terms & {item.lower() for item in scope} else "repository"
        encoding = encoding_recommendations(lesson, evidence_review)
        exact_duplicate = any(item["same_scope"] and item["similarity"] == 1.0 for item in matches)
        if contradictions:
            recommendation, rationale = "resolve_contradiction", "A same-scope knowledge claim has the opposite polarity."
        elif exact_duplicate or novelty_score < 0.25:
            recommendation, rationale = "merge", "The claim is already represented in the same scope."
        elif evidence_review["score"] < 0.45:
            recommendation, rationale = "needs_evidence", "Inspectable evidence does not yet adequately support the claim."
        elif confidence_score < 0.4:
            recommendation, rationale = "mission_local", "The claim has limited evidence-backed validation experience."
        else:
            recommendation, rationale = "human_review", "The proposal is evidence-backed and distinct enough for human promotion review."
        evaluations.append({
            "learning_id": learning_id,
            "proposal_fingerprint": proposal_fingerprint(lesson),
            "claim": claim,
            "scope": scope,
            "scope_classification": scope_kind,
            "novelty": {"score": novelty_score, "classification": novelty_class, "matches": matches},
            "evidence_quality": evidence_review,
            "contradictions": contradictions,
            "confidence": {
                "level": confidence_level,
                "score": confidence_score,
                "observed": counts["observed"],
                "reused": counts["reused"],
                "contradicted": counts["contradicted"],
                "superseded": bool(counts["superseded"]),
                "basis": {
                    "supporting_missions": counts["observed"],
                    "successful_reuses": counts["reused"],
                    "contradictions": counts["contradicted"],
                    "independent_reviews": 0,
                    "encoded_as_test": encoding["primary"] == "test",
                    "freshness": "superseded" if counts["superseded"] else "current",
                    "evidence_quality": evidence_review["score"],
                },
                "calculated_at": git_commit_time(repo),
                "algorithm_version": 1,
                "manual_override_history": [],
                "formula": "evidence_quality * (observed + 2*reused + 1) / (observed + 2*reused + 2*contradicted + 2*superseded + 3)",
            },
            "encoding": encoding,
            "promotion": {
                "recommendation": recommendation,
                "rationale": rationale,
                "human_approval": "required",
                "automatic_promotion": False,
            },
        })
    digest = hashlib.sha256(dump_yaml({"sha": git_sha(repo), "evaluations": evaluations, "events": events}).encode()).hexdigest()[:16]
    contradiction_pairs = {
        tuple(sorted((item["learning_id"], contradiction["learning_id"])))
        for item in evaluations
        for contradiction in item["contradictions"]
    }
    report = {
        "schema_version": VERSION,
        "artifact_type": "knowledge-evaluation",
        "evaluation_id": f"knowledge-evaluation-{digest}",
        "repository_sha": git_sha(repo),
        "evaluator": "project-brain-deterministic-v1",
        "reviewer": args.reviewer,
        "experience_events": events,
        "evaluations": evaluations,
        "summary": {
            "proposals_evaluated": len(evaluations),
            "need_human_review": sum(1 for item in evaluations if item["promotion"]["recommendation"] == "human_review"),
            "duplicates_or_merges": sum(1 for item in evaluations if item["promotion"]["recommendation"] == "merge"),
            "contradictions": len(contradiction_pairs),
            "weak_evidence": sum(1 for item in evaluations if item["evidence_quality"]["classification"] == "weak"),
        },
        "generated_at": git_commit_time(repo),
        "note": "Deterministic recommendation only. No lesson was promoted or moved.",
    }
    validate_data(report, ASSET_ROOT / "schemas" / "knowledge-evaluation.schema.json")
    output = dump_yaml(report)
    ensure_safe(output, "knowledge evaluation")
    if args.output:
        Path(args.output).expanduser().resolve().write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


def validate_data(data: dict[str, Any], schema_path: Path) -> None:
    require_runtime()
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(data), key=lambda e: list(e.path))
    if errors:
        details = "; ".join(f"{'/'.join(map(str, err.path)) or '<root>'}: {err.message}" for err in errors)
        raise BrainError(f"Schema validation failed ({schema_path.name}): {details}")


def validate_repo(repo: Path) -> list[str]:
    require_runtime()
    brain = repo / ".project-brain"
    errors = []
    schemas = ASSET_ROOT / "schemas"
    for path in sorted(brain.rglob("*.yaml")):
        if "templates" in path.relative_to(brain).parts:
            continue
        try:
            content = path.read_text(encoding="utf-8")
            findings = scan_secrets(content)
            if findings:
                errors.append(f"{path.relative_to(repo)}: likely secrets: {', '.join(findings)}")
                continue
            data = load_yaml(path)
            artifact = data.get("artifact_type")
            major = str(data.get("schema_version", "0")).split(".", 1)[0]
            repository_schema = brain / "schemas" / f"{artifact}.schema.json"
            schema = repository_schema if major == "1" and repository_schema.exists() else schemas / f"{artifact}.schema.json"
            if schema.exists():
                validate_data(data, schema)
                if major == "2" and artifact == "mission-result":
                    require_commit(repo, str(data["start_sha"]), f"{path.name} start_sha")
                    require_commit(repo, str(data["end_sha"]), f"{path.name} end_sha")
                    for item in data["evidence"]:
                        if item.get("kind") == "file":
                            require_evidence_reference(repo, str(item.get("reference", "")))
                if major == "2" and artifact == "knowledge-evaluation":
                    require_commit(repo, str(data["repository_sha"]), f"{path.name} repository_sha")
                    for event in data["experience_events"]:
                        require_evidence_reference(repo, str(event.get("evidence", "")))
            elif path.name not in {"project-profile.yaml"}:
                errors.append(f"{path.relative_to(repo)}: unknown artifact_type {artifact!r}")
        except BrainError as exc:
            errors.append(str(exc))
    if errors:
        raise BrainError("Project Brain validation failed:\n- " + "\n- ".join(errors))
    return errors


def validate_command(args: argparse.Namespace) -> int:
    repo = repo_root(args.repo)
    validate_repo(repo)
    print(dump_yaml({"status": "valid", "repository": str(repo), "head_sha": git_sha(repo)}), end="")
    return 0


def doctor_command(args: argparse.Namespace) -> int:
    report = runtime_report()
    if yaml is not None and report["mode"] == "ready":
        print(dump_yaml(report), end="")
    else:
        print(json.dumps(report, indent=2))
    return 0 if report["mode"] == "ready" else 2


def migrate_command(args: argparse.Namespace) -> int:
    require_runtime()
    repo = repo_root(args.repo)
    brain = repo / ".project-brain"
    versions = sorted({
        str(load_yaml(path).get("schema_version", "unknown"))
        for path in brain.rglob("*.yaml") if "templates" not in path.parts
    })
    plan = {
        "mode": "dry-run" if args.dry_run else "proposal",
        "repository": str(repo),
        "current_versions": versions,
        "target_version": VERSION,
        "impact": "Version 2 strengthens closure, review, learning, identity, and curation contracts.",
        "automatic_changes": [],
        "manual_steps": [
            "Review legacy artifacts and add evidence-backed required fields.",
            "Regenerate repository schemas and templates only after artifacts are compatible.",
            "Commit migration separately and run validate.",
        ],
    }
    if args.dry_run:
        print(dump_yaml(plan), end="")
        return 0
    if git_dirty(repo):
        raise BrainError("Migration proposal requires a clean worktree.")
    output = brain / "evaluations" / f"{today()}-schema-v2-migration-plan.md"
    created: list[str] = []
    body = "# Project Brain schema v2 migration plan\n\n" + "\n".join(
        f"- {key.replace('_', ' ').title()}: {value}" for key, value in plan.items() if key != "manual_steps"
    ) + "\n\n## Manual steps\n\n" + "".join(f"- {step}\n" for step in plan["manual_steps"])
    safe_write(output, body, repo, created)
    print(dump_yaml({"status": "migration-proposed", "created": created, **plan}), end="")
    return 0


def propose_command(args: argparse.Namespace) -> int:
    from .proposals import propose_learning

    result = propose_learning(
        args.repo,
        mission_id=args.mission_id,
        claim=args.claim,
        scope=args.scope,
        evidence=args.evidence,
        proposer=args.proposer,
        title=args.title,
        future_behavior=args.future_behavior,
        confidence=args.confidence,
        suggested_disposition=args.suggested_disposition,
        input_file=args.input,
        dry_run=args.dry_run,
    )
    print(dump_yaml(result), end="")
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init"); init.add_argument("--repo", default="."); init.add_argument("--dry-run", action="store_true"); init.add_argument("--repository-id"); init.set_defaults(func=init_command)
    context = sub.add_parser("context")
    context.add_argument("--repo", default="."); context.add_argument("--objective", required=True); context.add_argument("--role", required=True)
    context.add_argument("--mission-type"); context.add_argument("--component"); context.add_argument("--tag", action="append", default=[]); context.add_argument("--expected-file", action="append", default=[])
    context.add_argument("--reference", action="append", default=[]); context.add_argument("--max-files", type=int, default=12); context.add_argument("--max-bytes", type=int, default=120000)
    context.add_argument("--base-sha"); context.add_argument("--output"); context.set_defaults(func=context_command)
    close = sub.add_parser("close")
    close.add_argument("--repo", default="."); close.add_argument("--objective", required=True); close.add_argument("--role", required=True)
    close.add_argument("--status", choices=["completed", "failed", "blocked", "cancelled"], required=True); close.add_argument("--start-sha", required=True)
    close.add_argument("--agent", default="unspecified-agent"); close.add_argument("--acceptance-criterion", action="append", default=[])
    close.add_argument("--acceptance-outcome", required=True); close.add_argument("--file", action="append", default=[])
    close.add_argument("--review-cycle", action="append", default=[]); close.add_argument("--finding-resolution", action="append", default=[])
    close.add_argument("--risk", action="append", default=[])
    close.add_argument("--check", action="append", default=[]); close.add_argument("--evidence", action="append", default=[]); close.add_argument("--artifact", action="append", default=[])
    close.add_argument("--state-update", action="append", default=[]); close.add_argument("--follow-up", action="append", default=[]); close.add_argument("--learning"); close.add_argument("--scope", action="append", default=[])
    close.add_argument("--confidence", choices=["low", "medium", "high"], default="medium"); close.add_argument("--future-behavior")
    close.add_argument("--proposer", default="agent"); close.set_defaults(func=close_command)
    close.add_argument("--suggested-disposition", default="human-review")
    curate = sub.add_parser("curate"); curate.add_argument("--repo", default="."); curate.add_argument("--reviewer", default="human-review-required"); curate.add_argument("--output"); curate.add_argument("--patch-output"); curate.set_defaults(func=curate_command)
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--repo", default=".")
    evaluate.add_argument("--learning", action="append", default=[])
    evaluate.add_argument("--experience", action="append", default=[])
    evaluate.add_argument("--reviewer", default="human-approval-required")
    evaluate.add_argument("--output")
    evaluate.set_defaults(func=evaluate_command)
    propose = sub.add_parser("propose-learning")
    propose.add_argument("--repo", default=".")
    propose.add_argument("--mission-id")
    propose.add_argument("--claim")
    propose.add_argument("--scope", action="append", default=[])
    propose.add_argument("--evidence", action="append", default=[])
    propose.add_argument("--proposer", default="agent")
    propose.add_argument("--title")
    propose.add_argument("--future-behavior")
    propose.add_argument("--confidence", choices=["low", "medium", "high"], default="medium")
    propose.add_argument("--suggested-disposition", default="human-review")
    propose.add_argument("--input")
    propose.add_argument("--dry-run", action="store_true")
    propose.set_defaults(func=propose_command)
    validate = sub.add_parser("validate"); validate.add_argument("--repo", default="."); validate.set_defaults(func=validate_command)
    doctor = sub.add_parser("doctor"); doctor.set_defaults(func=doctor_command)
    migrate = sub.add_parser("migrate"); migrate.add_argument("--repo", default="."); migrate.add_argument("--dry-run", action="store_true"); migrate.set_defaults(func=migrate_command)
    return root


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        if args.command != "doctor":
            require_runtime()
        return args.func(args)
    except (BrainError, OSError, json.JSONDecodeError) as exc:
        print(f"Project Brain: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
