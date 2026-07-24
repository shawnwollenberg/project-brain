# Current state

Observed at `5674e9b0af66b5d70b100a8df87ead2dc751b68a` on 2026-07-24.

## Verified

- Project Brain is a Git-native, evidence-backed, provider-neutral knowledge system; it is not a transcript, chain-of-thought, vector, or autonomous authority. Evidence: `README.md`.
- The importable Python core and console CLI are package-owned under `src/project_brain/`; provider skills are thin adapters. Evidence: `pyproject.toml`, `src/project_brain/api.py`, `skills/codex/project-brain/SKILL.md`.
- Package version is 0.3.0 and generated artifact schema version is 2.5.0. Repository-local schemas preserve historical reproducibility. Evidence: `pyproject.toml`, `docs/schemas/versioning.md`.
- Knowledge promotion, merging, supersession, and stronger encoding require explicit human approval. Evaluator and curator never move proposals. Evidence: `docs/adr/0003-human-gated-promotion.md`.
- Context retrieval is deterministic, explainable, budgeted, and explicit references are guaranteed or rejected. Evidence: `docs/adr/0004-deterministic-retrieval.md`, `src/project_brain/core.py`.
- Secrets, unsafe evidence paths, unsupported schemas, fake SHAs, self-authored evidence, and dirty-worktree mutation are blocked. Evidence: `docs/security/model.md`, `tests/regression/test_legacy.py`.
- The six existing ADRs remain authoritative and are referenced rather than duplicated here. Evidence: `docs/adr/`.
- Compatibility target: Python 3.8+, package 0.3.x, skill adapter 0.3.x, and schema 2.5.x. Evidence: `pyproject.toml`, `project-brain doctor`.
- Tests run with `python3 -m unittest discover -s tests -p 'test_*.py'`; skill validation uses the official Codex quick validator through `scripts/install_skill.py validate`.
- Release constraint: prepare locally only; do not publish, tag, push, release, or modify real consumer repositories during the 0.3.0 milestone.
- The 0.3.0 self-hosted proposal mission passed 56 tests and a two-cycle independent review with zero unresolved blockers. Its lesson remains proposed with a mission-local recommendation. Evidence: `.project-brain/missions/2026-07-24-harden-document-and-independently-review-the-standalone-proposal.yaml`, `.project-brain/evaluations/lesson-9fb80a9be1ef-evaluation.yaml`.

## Uncertainties

- None recorded for local 0.3.0 readiness; publication and consumer integration remain intentionally unperformed.
