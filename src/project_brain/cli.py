"""Console entry point for Project Brain."""

from __future__ import annotations

import json
import sys

from . import api, core


ALIASES = {"prepare-context": "context", "close-mission": "close"}


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    output_format = "human"
    if "--format" in arguments:
        index = arguments.index("--format")
        try:
            output_format = arguments[index + 1]
        except IndexError:
            print("Project Brain: --format requires human, yaml, or json", file=sys.stderr)
            return 2
        del arguments[index:index + 2]
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


if __name__ == "__main__":
    raise SystemExit(main())
