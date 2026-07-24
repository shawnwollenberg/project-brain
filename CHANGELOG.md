# Changelog

This project follows Semantic Versioning. Artifact schema versions are independent from the package version.

## [0.2.0] - 2026-07-24

### Added

- Standalone importable library and thin `project-brain` CLI.
- Validated Project Brain v2.5 initialization, profiling, deterministic retrieval, mission closure, curation, validation, migration, evaluator, and confidence behavior.
- Packaged schemas/templates, Codex skill, provider-neutral adapters, installer, fixtures, governance, and ADRs.

### Changed

- Reorganized the installed Codex skill implementation into a provider-neutral package.
- Kept repository-local schemas for historical reproducibility while making packaged resources authoritative for new initialization.

### Security

- Preserved secret scanning, safe evidence paths, Git SHA validation, dirty-worktree protection, and human-gated promotion.
