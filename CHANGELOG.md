# Changelog

This project follows Semantic Versioning. Artifact schema versions are independent from the package version.

## [Unreleased]

### Added

- Explicit approval-gated `initialize_repository` support in consumer contract 1.0.
- Repository-contained, checksummed evaluation-output artifact descriptors.
- Explicit mission-closure `end_sha` binding for reviewed commits created in isolated worktrees.

### Changed

- Final context persistence now requires an explicit `write: true`; omitted write intent remains read-only.

### Security

- Initialization remains opt-in, evaluation outputs cannot escape the repository, and no operation promotes knowledge.

## [0.3.0] - 2026-07-24

### Added

- Dedicated mission-backed `propose-learning` CLI and Python API with dry-run, structured input, stable identity, proposal fingerprinting, secret/evidence validation, and duplicate no-op behavior.
- Proposal fingerprint invalidation across claim, scope, evidence, status, and source mission.
- Canonical scope, contradiction, evidence, and experience-event normalization.
- Evaluator-to-curator disposition propagation with conservative blocker preservation.
- Package/skill/schema drift diagnostics and a thin Codex skill adapter.
- Self-hosted `.project-brain/` repository knowledge and lifecycle evidence.

### Changed

- Made the standalone package the sole authoritative implementation.
- Unified all 36 installed reference scenarios with standalone architecture, proposal, and additional trust-boundary tests.
- Restricted evidence kinds and rejected duplicated, laundered, unsafe, or self-authored proposal evidence.

### Compatibility

- Package and skill adapter version 0.3.0 continue generating schema 2.5.0.
- Numeric confidence in older confirmed lessons remains valid.
- Migration remains proposal-only; changed proposals require reevaluation.

### Security

- Canonical experience IDs prevent duplicate confidence inflation.
- Current proposal fingerprints are required before curation can recommend promotion or encoding.

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
