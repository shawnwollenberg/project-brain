# Install and use Project Brain

Project Brain is provider-neutral. It requires Git, Python 3.8+, PyYAML, and jsonschema.

Install dependencies:

```bash
python3 -m pip install PyYAML jsonschema
```

If `python3` is not the interpreter you expect, run:

```bash
python3 scripts/project_brain.py doctor
```

The report identifies the interpreter, supported version, virtual environment,
package manager, required and missing dependencies, exact install command, and
whether the CLI is limited to diagnostics.

Install the skill for Codex by copying this directory to:

```text
~/.codex/skills/project-brain
```

Other agents may call `scripts/project_brain.py` directly; no Codex API is required.

Start every repository with a dry run:

```bash
python3 scripts/project_brain.py init --repo /path/to/repository --dry-run
```

Run regression tests:

```bash
python3 scripts/test_project_brain.py
```

Validate the skill package:

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py ~/.codex/skills/project-brain
```
