# Installed v2.5 to standalone 0.3.0 reconciliation

Date: 2026-07-24  
Standalone baseline: `612903f`  
Installed reference: `~/.codex/skills/project-brain`

## Method

The standalone and installed Python engines, JSON Schemas, templates, tests, skill instructions, and reference documentation were compared directly. Function names were not treated as proof of behavioral equivalence. Engine branches and every installed regression scenario were inspected.

## Findings

| Area | Classification | Finding |
|---|---|---|
| CLI commands | Behavior differs | Standalone adds aliases, JSON output, `profile`, and an importable facade. Neither distribution has the dedicated proposal command. |
| Library operations | Missing from installed / incomplete standalone | Standalone has an in-process facade; installed is CLI-only. Proposal creation is coupled to mission closure. |
| Evaluator lifecycle | Equivalent baseline, trust boundaries missing from standalone | Both are non-promoting and require human approval, but installed binds evaluations to proposal fingerprints. |
| Evaluation output | Schema differs | Installed requires `proposal_fingerprint`; standalone has richer confidence metadata not present in installed output. |
| Confidence calculation | Equivalent formula; standalone extension | Both use the v2.5 formula. Standalone additionally records level, basis, calculation time, algorithm version, and override history. |
| Schema versions | Schema differs | Both generate schema `2.5.0`; installed restricts evidence kinds and requires evaluation fingerprints. |
| Templates | Equivalent implementation confirmed | No template differences. |
| Curation rules | Missing from standalone | Installed propagates evaluator dispositions, invalidates stale fingerprints, and preserves the most conservative current blocker. |
| Evidence validation | Missing from standalone | Installed validates kinds, canonical paths, kind-to-artifact fit, duplicate references, and self-authored proposal evidence. |
| Proposal fingerprinting | Missing from standalone | Installed hashes ID, status, normalized claim, canonical scope, evidence kind/reference, and source mission. |
| Duplicate detection | Behavior differs | Installed validates knowledge artifacts first and canonicalizes scope before comparison. |
| Contradiction detection | Behavior differs | Installed normalizes contractions, punctuation, modal operators, negation, and scope. |
| Scope normalization | Missing from standalone | Installed lowercases, trims, deduplicates, and sorts scope. |
| Experience normalization | Missing from standalone | Installed derives canonical IDs, validates stored IDs, and deduplicates events by canonical tuple. |
| Migration behavior | Equivalent implementation confirmed | Both remain proposal-only and never fabricate evidence. |
| Secret detection | Equivalent implementation confirmed | Pattern set and write blocking are equivalent. |
| Dirty-worktree behavior | Equivalent implementation confirmed | Mutations require clean worktrees; dry runs are read-only. |
| Context retrieval | Equivalent implementation confirmed | Selection, explicit-source guarantees, budgets, hashes, and stable tie-breaking match. |
| Tests | Test coverage differs | Installed has 36 scenarios; standalone inherited 29 plus 4 architecture tests. Seven installed trust-boundary scenarios are absent. |
| Documentation | Documentation differs | Installed evaluator references describe the newer trust boundaries; standalone architecture and API docs describe package behavior. |
| Provider integration | Intentionally excluded | Mission Control integration and provider APIs remain outside this milestone. |

## Trust-boundary checklist

| Capability | Baseline status |
|---|---|
| Evidence path validation | Equivalent implementation confirmed |
| Evidence kind validation | Missing from standalone |
| Evidence deduplication | Missing from standalone |
| Self-authored assertion rejection | Missing from standalone |
| Canonical experience IDs | Missing from standalone |
| Confidence inflation prevention | Missing from standalone |
| Deterministic scope normalization | Missing from standalone |
| Modal/contraction/negation/punctuation normalization | Missing from standalone |
| Evaluation-to-proposal fingerprint binding | Missing from standalone |
| Claim/scope/evidence/status/source-mission invalidation | Missing from standalone |
| Conservative blocker preservation | Missing from standalone |
| Current evaluator required for promotion recommendation | Missing from standalone |
| Evaluation and curation never promote automatically | Equivalent implementation confirmed |

## Evaluator and encoding coverage

Both implementations emit novelty, duplicate matches, evidence quality, contradictions, repository/organization scope, experience-backed confidence, primary and alternative encodings, a promotion recommendation, and mandatory human approval. Both rank lesson, ADR, playbook, regression test, policy, follow-up issue, and mission-local evidence. Both accept observed, reused, contradicted, and superseded experience events.

## Installed scenario mapping at baseline

| Installed-skill scenario | Standalone baseline test | Status |
|---|---|---|
| initialization and profile detection | `test_new_repository_initialization_and_profile_detection` | Covered |
| mature AGENTS merge proposal | `test_existing_agents_creates_merge_proposal` | Covered |
| repeated initialization | `test_existing_brain_and_repeated_initialization_do_not_overwrite` | Covered |
| dirty apply / dry-run | `test_dirty_repository_blocks_apply_but_allows_dry_run` | Covered |
| invalid YAML | `test_invalid_yaml_is_reported` | Covered |
| secret detection | `test_secret_detection_blocks_validation` | Covered |
| deterministic explicit context | `test_context_selection_is_deterministic_and_prefers_explicit` | Covered |
| source-format retrieval | `test_source_context_includes_relevant_tsx_and_excludes_unrelated` | Covered |
| identity precedence | matching identity tests | Covered |
| stable worktree identity | `test_repository_identity_stable_in_worktree` | Covered |
| mission evidence and SHA checks | matching mission tests | Covered |
| proposal-only closure | `test_mission_closure_proposes_but_does_not_confirm_learning` | Covered |
| duplicate/conflict/disjoint-scope curation | matching curation tests | Covered, older expectations |
| explicit-source failure | `test_explicit_context_source_cannot_disappear_silently` | Covered |
| schema enforcement | `test_strengthened_schemas_accept_complete_and_reject_incomplete_records` | Covered |
| doctor modes | matching doctor tests | Covered |
| proposal-only migration | `test_migration_is_proposal_only` | Covered |
| duplicate evaluator | `test_evaluator_detects_duplicate_lessons` | Covered, fixture weaker |
| contradiction evaluator | `test_evaluator_detects_contradictory_lessons` | Covered, normalization absent |
| modal/contraction/punctuation normalization | none | Missing |
| weak/strong evidence | `test_evaluator_distinguishes_weak_and_strong_evidence` | Covered |
| evaluator-to-curator weak disposition | none | Missing |
| stale fingerprint rejection | none | Missing |
| conservative multiple-report blocker | none | Missing |
| scope classification | `test_evaluator_classifies_repository_and_organization_scope` | Covered |
| encoding alternatives | `test_evaluator_recommends_multiple_valid_encodings` | Covered |
| evidence dedupe and kind laundering | none | Missing |
| unsupported knowledge schema | none | Missing |
| noncanonical stored event ID | none | Missing |
| confidence after repeated validation | `test_confidence_increases_after_repeated_validation` | Covered |

## Port decision

All seven missing installed scenarios and their supporting trust boundaries are appropriate and will be ported into the standalone core. Standalone confidence metadata will be retained as a compatible extension. The installed engine will then be removed and replaced with a thin adapter installed from this repository. No installed-only implementation will remain authoritative.
