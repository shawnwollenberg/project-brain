# Project Brain

Project Brain is a Git-native, evidence-backed, provider-neutral system for preserving, validating, retrieving, and improving durable project knowledge used by AI agents and human engineering teams.

It keeps knowledge readable as Markdown and YAML, validates machine contracts with JSON Schema, builds small deterministic context packs, and requires human approval before proposed knowledge becomes confirmed knowledge.

Project Brain is not a conversational-memory database, transcript or chain-of-thought archive, vector database, autonomous knowledge authority, or replacement for Git, documentation, tests, and review.

## Install

Project Brain requires Python 3.9 or newer:

```bash
python3 -m pip install -e '.[dev]'
project-brain doctor
```

For a runtime-only editable install, use `python3 -m pip install -e .`. The runtime dependencies are PyYAML and jsonschema.

## Five-minute quick start

Run these commands in a clean Git repository:

```bash
project-brain init --repo . --dry-run
project-brain init --repo .
git add .project-brain AGENTS.md && git commit -m "Initialize Project Brain"
project-brain prepare-context --repo . --objective "Fix scheduler flakiness" --role implementer
project-brain validate --repo .
```

Use `--format json` on scriptable commands for structured JSON. The default is readable YAML. Initialization never overwrites files and mutation is blocked in a dirty worktree.

## Core workflows

- `init`: profile and initialize a repository, with a read-only preview.
- `profile`: inspect language, framework, commands, and stable repository identity.
- `prepare-context` (`context`): select deterministic, budgeted task context.
- `close-mission` (`close`): record outcomes, evidence, and optional learning proposals.
- `evaluate`: inspect evidence, novelty, duplicates, conflicts, confidence, and encoding.
- `curate`: recommend human-gated lifecycle changes without applying them.
- `validate`: check YAML, schemas, evidence, SHAs, lifecycle rules, and likely secrets.
- `migrate`: propose compatibility work; `--dry-run` is non-mutating.
- `doctor`: report interpreter and dependency health.

The importable API exposes the same operations:

```python
from project_brain import initialize, prepare_context, validate

preview = initialize(".", dry_run=True)
context = prepare_context(".", "Fix scheduler flakiness", "implementer")
assert validate(".").exit_code == 0
```

## Knowledge lifecycle and approval

Knowledge moves through `observation → proposed → reviewed → confirmed → encoded or retained → stale or superseded`. Agents may propose knowledge but cannot approve their own lessons. Every promotion or stronger encoding requires explicit human approval and inspectable evidence.

The deterministic evaluator checks schema completeness, evidence existence and lexical support, mission linkage, same-scope duplication and contradiction, freshness signals, and existing encoding cues. It never promotes or rewrites a lesson. Optional model-assisted evaluation is an adapter interface for future work, not a runtime dependency.

Confidence is evidence-derived:

```text
evidence_quality × (observed + 2×reused + 1)
÷ (observed + 2×reused + 2×contradicted + 2×superseded + 3)
```

The report includes every input, the formula, and experience events. Confidence never bypasses approval.

## Architecture

```text
Repository
    ↓
Project Brain core
    ↓
Context pack / mission result / learning proposal
    ↓
Provider adapter
    ↓
Agent
```

The Python package contains the provider-neutral core and CLI. Packaged resources under `src/project_brain/resources/` are authoritative for new releases; initialized repositories receive copies for reproducible historical validation. Provider adapters contain guidance only and do not duplicate repository knowledge.

See [architecture](docs/architecture/overview.md), [schema compatibility](docs/schemas/versioning.md), [security](docs/security/model.md), and the [ADRs](docs/adr/).

## Codex skill

Install into the normal Codex skills directory:

```bash
python3 scripts/install_skill.py install
python3 scripts/install_skill.py validate
python3 scripts/install_skill.py uninstall
```

Set `--target` to validate a disposable installation. The installer refuses to overwrite a different installation unless `--force` is explicitly provided, reports version 0.2.0, and writes an install manifest for safe removal.

## Tests

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

The suite preserves the installed v2 regression scenarios and covers API/CLI parity, packaged resources, skill lifecycle, editable installation, deterministic evaluation, migration, and disposable consumer fixtures.

## Security and limitations

Project Brain rejects likely credentials, unsafe evidence paths, unsupported schema majors, invalid YAML, fake commit SHAs, and mutating operations in dirty repositories. It stores conclusions and evidence—not secrets, environment dumps, transcripts, or hidden reasoning.

Current limitations: retrieval is lexical and repository-local; there is no database, vector store, background worker, web UI, model API, autonomous promotion, or cross-repository organizational memory. Obsidian can view the Markdown knowledge tree but is optional and never the source of truth.

Mission Control, OfficeAnywhere, Aegis, and other applications should consume Project Brain as a library or CLI. Mission Control may orchestrate the workflow but does not own the knowledge contracts.

## Repository map

- `src/project_brain/`: library, CLI, evaluator, validation, and packaged resources
- `skills/codex/project-brain/`: thin Codex adapter
- `adapters/`: provider guidance without provider APIs
- `examples/`: generated and disposable consumer examples
- `tests/`: unit, integration, fixture, and inherited regression coverage
- `docs/`: architecture, contracts, security, workflows, and decisions

Licensed under Apache-2.0. Version 0.2.0 imports the validated Project Brain v2.5 artifact behavior into a standalone pre-1.0 package.
