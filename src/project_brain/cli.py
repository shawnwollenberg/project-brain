"""Console entry point for Project Brain."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import api, core
from .integrations import capability_report, execute


ALIASES = {"prepare-context": "context", "close-mission": "close"}


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    output_format = "human"
    if "--json" in arguments:
        arguments.remove("--json")
        output_format = "json"
    if "--format" in arguments:
        index = arguments.index("--format")
        try:
            output_format = arguments[index + 1]
        except IndexError:
            print("Project Brain: --format requires human, yaml, or json", file=sys.stderr)
            return 2
        del arguments[index:index + 2]
    if arguments and arguments[0] == "capabilities":
        print(json.dumps(capability_report(), indent=2))
        return 0
    if arguments and arguments[0] == "consumer":
        return _consumer(arguments[1:])
    if arguments and arguments[0] == "profile":
        repo = arguments[arguments.index("--repo") + 1] if "--repo" in arguments else "."
        data = api.profile(repo)
        print(_render(data, output_format), end="")
        return 0
    if arguments:
        arguments[0] = ALIASES.get(arguments[0], arguments[0])
    if output_format in {"human", "yaml"}:
        return core.main(arguments)
    if output_format != "json":
        print(f"Project Brain: unsupported output format {output_format!r}", file=sys.stderr)
        return 2
    result = api.invoke(arguments)
    stream = sys.stdout if result.exit_code == 0 else sys.stderr
    print(json.dumps(result.data if result.data is not None else {"error": result.text.strip()}, indent=2), file=stream)
    return result.exit_code


def _render(data: object, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(data, indent=2) + "\n"
    core.require_runtime()
    return core.yaml.safe_dump(data, sort_keys=False)


def _consumer(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="project-brain consumer")
    parser.add_argument("--operation", required=True)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--contract-version", default="1.0")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--request")
    group.add_argument("--request-json")
    try:
        args = parser.parse_args(arguments)
        if args.request:
            request = json.loads(Path(args.request).expanduser().resolve().read_text(encoding="utf-8"))
        elif args.request_json:
            request = json.loads(args.request_json)
        else:
            request = {}
        if not isinstance(request, dict):
            raise ValueError("Consumer request must be a JSON object.")
        result = execute(args.operation, args.repo, request, contract_version=args.contract_version)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {
            "contract_version": "1.0",
            "operation": "consumer_request",
            "status": "failed",
            "repository": None,
            "artifacts": [],
            "warnings": [],
            "blockers": [str(exc)],
            "required_actions": ["Provide a valid bounded JSON consumer request."],
            "human_approval_required": False,
            "repository_files_changed": False,
            "exit_classification": "invalid_request",
            "data": None,
        }
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "succeeded" else 2


if __name__ == "__main__":
    raise SystemExit(main())
