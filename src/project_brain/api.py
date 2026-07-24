"""Stable, in-process library facade over the provider-neutral core."""

from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import core


@dataclass(frozen=True)
class CommandResult:
    """A scriptable operation result with parsed and rendered output."""

    exit_code: int
    data: Any
    text: str

    @property
    def changed_files(self) -> tuple[str, ...]:
        if isinstance(self.data, dict):
            return tuple(self.data.get("created", ()))
        return ()


def invoke(arguments: list[str]) -> CommandResult:
    """Execute the same parser and core used by the CLI, without a subprocess."""

    output = io.StringIO()
    errors = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
        code = core.main(arguments)
    text = output.getvalue() if code == 0 else errors.getvalue()
    try:
        data = core.yaml.safe_load(text) if text and core.yaml is not None else None
    except Exception:
        data = None
    return CommandResult(code, data, text)


def initialize(repo: str | Path = ".", *, dry_run: bool = False, repository_id: str | None = None) -> CommandResult:
    args = ["init", "--repo", str(repo)]
    if dry_run:
        args.append("--dry-run")
    if repository_id:
        args.extend(["--repository-id", repository_id])
    return invoke(args)


def profile(repo: str | Path = ".", *, repository_id: str | None = None) -> dict[str, Any]:
    root = core.repo_root(str(repo))
    result, _ = core.detect_profile(root, repository_id)
    return result


def prepare_context(repo: str | Path, objective: str, role: str, **options: Any) -> CommandResult:
    args = ["context", "--repo", str(repo), "--objective", objective, "--role", role]
    scalar = {"mission_type": "--mission-type", "component": "--component", "max_files": "--max-files", "max_bytes": "--max-bytes", "base_sha": "--base-sha", "output": "--output"}
    repeated = {"tag": "--tag", "expected_file": "--expected-file", "reference": "--reference"}
    for key, flag in scalar.items():
        if options.get(key) is not None:
            args.extend([flag, str(options[key])])
    for key, flag in repeated.items():
        for value in options.get(key, ()):
            args.extend([flag, str(value)])
    return invoke(args)


def close_mission(repo: str | Path, **options: Any) -> CommandResult:
    required = ("objective", "role", "status", "start_sha", "acceptance_outcome")
    args = ["close", "--repo", str(repo)]
    mapping = {key: "--" + key.replace("_", "-") for key in options}
    for key in required:
        if key not in options:
            raise ValueError(f"Missing required close_mission option: {key}")
    for key, value in options.items():
        flag = mapping[key]
        if isinstance(value, (list, tuple)):
            for item in value:
                args.extend([flag, str(item)])
        elif value is not None:
            args.extend([flag, str(value)])
    return invoke(args)


def evaluate(repo: str | Path = ".", **options: Any) -> CommandResult:
    return _simple("evaluate", repo, options, repeated={"learning", "experience"})


def curate(repo: str | Path = ".", **options: Any) -> CommandResult:
    return _simple("curate", repo, options)


def validate(repo: str | Path = ".") -> CommandResult:
    return invoke(["validate", "--repo", str(repo)])


def migrate(repo: str | Path = ".", *, dry_run: bool = True) -> CommandResult:
    return invoke(["migrate", "--repo", str(repo)] + (["--dry-run"] if dry_run else []))


def doctor() -> CommandResult:
    return invoke(["doctor"])


def _simple(command: str, repo: str | Path, options: dict[str, Any], repeated: set[str] | None = None) -> CommandResult:
    args = [command, "--repo", str(repo)]
    repeated = repeated or set()
    for key, value in options.items():
        flag = "--" + key.replace("_", "-")
        if key in repeated:
            for item in value:
                args.extend([flag, str(item)])
        elif value is not None:
            args.extend([flag, str(value)])
    return invoke(args)
