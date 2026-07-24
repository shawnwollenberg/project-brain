# Project Brain workflows

## Initialize

1. Resolve the Git root and record HEAD plus worktree state.
2. Inventory language, framework, package manager, build, test, lint, typecheck, CI, deployment signals, and documentation.
3. Classify each profile value as `observed` or `inferred`; include evidence and uncertainty.
4. Preview the proposed tree. On apply, refuse a dirty repository and never overwrite an existing file.
5. Copy versioned schemas and templates into `.project-brain/`.
6. Create a concise `AGENTS.md` only when absent. When present, create `evaluations/agents-merge-proposal.md`.
7. Validate all generated YAML and scan generated material for secrets.

## Prepare context

1. Accept objective, role, expected files, explicit references, component, tags, and mission type.
2. Enumerate version-controlled documentation plus Project Brain knowledge.
3. Score exact references first, then expected paths, known-issue relations, component/tag/role/mission matches, filename matches, and bounded content matches.
4. Select the smallest useful set within the requested file and byte limits.
5. Record repository SHA, inclusion reason, byte count, estimated tokens, and content hash.
6. Never include secret-like files or raw environment/config payloads.

## Close a mission

1. Record objective, role, status, start/end SHA, checks, results, evidence, artifacts, and follow-ups.
2. Reject missing evidence for completed work.
3. Store lessons as proposals with proposer attribution, never as confirmed truth.
4. Record recommended state updates as reviewable proposals.
5. Validate and secret-scan before writing.

## Curate

1. Load proposed, confirmed, stale, superseded, and Knowledge Evaluator reports.
2. Refuse to recommend promotion for a proposal without a structured
   evaluation; recommend running the evaluator instead.
3. Identify exact duplicates, likely overlaps, scope conflicts, missing evidence, and stale verification dates.
4. Recommend one of: reject as noise, keep mission-local, merge, confirm,
   encode as ADR, encode as playbook, encode as test, encode as policy, create
   a follow-up issue, mark stale, or supersede.
5. Include rationale, target, evidence, human-approval state, and resulting
   status for every recommendation.
6. Produce a machine-readable knowledge review and a human-readable patch proposal.
7. Never move or rewrite lesson files automatically or automatically apply a
   high-impact disposition.

## Evaluate knowledge

1. Load proposed learning plus confirmed, stale, superseded, and peer proposals.
2. Verify whether cited evidence is inspectable and whether bounded evidence
   text supports claim terms.
3. Score novelty from deterministic claim overlap within scope.
4. Flag same-scope claims with equivalent text and opposite polarity.
5. Classify repository or organizational scope from explicit scope values.
6. Compute confidence from evidence quality and recorded observed, reused,
   contradicted, and superseded experience.
7. Rank lesson, ADR, playbook, test, policy, follow-up issue, and mission-local
   encodings using documented signals.
8. Emit a structured promotion recommendation requiring human approval.
9. Never move, rewrite, confirm, or encode a lesson.

## Runtime and migration

Run `doctor` before first use to report the selected Python interpreter,
supported version, environment/virtualenv, package manager, required and
missing dependencies, exact install command, and whether only diagnostics are
available. Run `migrate --dry-run` before upgrading an initialized v1
repository. Migration is proposal-only until a human supplies or approves all
new required evidence.

## Dry-run rules

A dry run may inspect a dirty repository but must clearly report that application would be blocked. It must not create `.project-brain`, edit `AGENTS.md`, stage files, or change source code.
