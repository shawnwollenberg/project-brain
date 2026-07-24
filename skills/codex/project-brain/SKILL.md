---
name: project-brain
description: Initialize, retrieve, close, evaluate, curate, and validate a provider-neutral repository knowledge system stored as Git-versioned Markdown and YAML. Use when Codex needs to create or maintain a .project-brain directory, prepare a minimal task context pack, record mission results and proposed lessons, deterministically evaluate evidence, novelty, contradictions, confidence, and encoding choices, review knowledge lifecycle changes, validate Project Brain artifacts, or audit durable agent context without exposing secrets or hidden reasoning.
---

# Project Brain

Create durable repository knowledge without turning generated claims into truth. Keep Git as the source of truth, Markdown readable by humans, YAML machine-readable, and every promoted lesson reviewable and evidence-backed.

This skill is adapter version 0.3.0 for Project Brain package 0.3.x and schema 2.5.x. It contains no Project Brain engine. Invoke the installed `project-brain` command only.

## Operating rules

1. Inspect before writing. Run `git status --short`, resolve the repository root, and identify existing `AGENTS.md` and `.project-brain/` content.
2. Treat a dirty worktree as read-only unless the user explicitly authorizes scoped writes. Dry runs may inspect dirty repositories.
3. Never store secrets, credentials, environment dumps, private keys, raw model transcripts, or hidden chain-of-thought.
4. Separate observed facts from inferences. Cite repository-relative files, commands, commits, tests, or artifacts as evidence.
5. Write new learnings to `lessons/proposed/`. Never promote them automatically unless repository configuration explicitly permits it and the user authorizes the promotion.
6. Do not replace a mature `AGENTS.md`. Generate a concise merge proposal.
7. Keep task context minimal and deterministic. Record why every source was included, its size estimate, and the repository SHA.
8. Prefer encoding high-value confirmed lessons in tests, scripts, skills, or policies rather than prose alone.

## Choose a workflow

- Initialize or audit a repository: use `init`.
- Prepare task-specific context: use `context`.
- Close work and propose learnings: use `close`.
- Create a mission-backed proposal independently of closure: use `propose-learning`.
- Evaluate proposed learning without promoting it: use `evaluate`.
- Review proposed knowledge: use `curate`.
- Validate artifacts or detect secrets: use `validate`.
- Diagnose the local interpreter and dependencies: use `doctor`.
- Assess a v1-to-v2 upgrade without inventing evidence: use `migrate --dry-run`.

Read [workflows.md](references/workflows.md) before running a mutating workflow. Read [artifact-contracts.md](references/artifact-contracts.md) when changing schemas or templates. Read [security.md](references/security.md) whenever material may contain credentials or sensitive data.
Read [knowledge-evaluator.md](references/knowledge-evaluator.md) before changing
evaluation scores, contradiction rules, confidence evolution, or encoding
recommendations.

## Run the CLI

Use the standalone command:

```bash
project-brain --help
```

Dependencies:

```bash
python3 -m pip install PyYAML jsonschema
```

If `project-brain` is unavailable, stop before mutation and report:

```text
Project Brain package is unavailable. Install the matching standalone package,
then run `project-brain doctor`. Do not fall back to a bundled or copied engine.
```

Run `project-brain doctor` before first use or when it reports a version mismatch. Follow its repair command rather than silently invoking another implementation.

Discover the exact interpreter, environment, missing packages, and install command:

```bash
project-brain doctor
```

### Initialize

Preview first:

```bash
project-brain init --repo . --dry-run
```

Apply only in a clean repository:

```bash
project-brain init --repo .
```

Initialization is idempotent. It does not overwrite existing files. If `AGENTS.md` already exists, it writes a merge proposal inside `.project-brain/evaluations/`.

### Prepare context

```bash
project-brain prepare-context \
  --repo . --objective "Fix scheduler flakiness" --role "test engineer" \
  --mission-type bug-fix --expected-file src/scheduler.ts \
  --output /tmp/context-pack.yaml
```

Explicit references are guarantees: the command fails rather than silently
dropping a missing, unsupported, or over-budget explicit file. Expected sources
that cannot fit are reported with an omission reason.

### Close a mission

```bash
project-brain close-mission \
  --repo . --objective "Fix scheduler flakiness" --role "test engineer" \
  --status completed --start-sha START_SHA \
  --agent codex --acceptance-criterion "Scheduler tests are deterministic" \
  --acceptance-outcome passed --file src/scheduler.test.ts \
  --check "npm test=passed" --evidence "src/scheduler.test.ts" \
  --state-update "Scheduler validation is deterministic" \
  --learning "Scheduler tests require a frozen clock"
```

This creates a mission result and, when requested, a proposed learning. The proposer remains distinct from the reviewer.
Version 2 closure verifies that starting/ending SHAs resolve and that file
evidence is an inspectable repository-relative file.

### Evaluate proposed knowledge

```bash
project-brain evaluate \
  --repo . --learning lesson-id \
  --output .project-brain/evaluations/lesson-id-evaluation.yaml
```

Record evidence-backed experience when applicable:

```bash
project-brain evaluate \
  --repo . --learning lesson-id \
  --experience lesson-id:reused:path/to/evidence
```

The evaluator deterministically reports novelty, evidence quality,
contradictions, repository-versus-organization scope, confidence, encoding
options, and a promotion recommendation. It never moves or promotes a lesson.
Every promotion recommendation requires human approval.

### Curate knowledge

```bash
project-brain curate --repo .
```

Run `evaluate` and commit or retain its report before `curate`. Unevaluated
proposals receive a follow-up recommendation instead of a promotion
recommendation. Review the generated knowledge review and patch recommendation.
Apply promotions, merges, expirations, or supersessions only after human
approval.

Every recommendation records a rationale, target, evidence, human-approval
state, and resulting status. High-impact dispositions are never applied
automatically.

### Assess migration

```bash
project-brain migrate \
  --repo . --dry-run
```

Version 2 intentionally strengthens artifact contracts. Existing version 1
repositories continue validating against their Git-versioned schemas. The
migration command creates a proposal only; it never fabricates missing
historical evidence or rewrites artifacts automatically.

### Validate

```bash
project-brain validate --repo .
```

Stop and report exact files when schema validation, missing evidence, lifecycle rules, or secret detection fails.

## Output contract

Report:

- files created or proposed;
- facts, inferences, and uncertainties;
- repository SHA and worktree state;
- validation commands and results;
- knowledge changes requiring human review;
- any blocked write and the safe next action.

Do not claim initialization succeeded after a dry run. Do not summarize a validation failure as a generic error.

## Bundled resources

- The standalone `project-brain` package: deterministic core and CLI.
- `src/project_brain/resources/`: authoritative templates and JSON Schemas.
- `examples/`: representative generated artifacts.
- `references/workflows.md`: detailed operational workflows.
- `references/artifact-contracts.md`: schema, lifecycle, and retrieval contract.
- `references/security.md`: safety and secret-handling rules.
- `references/install-and-usage.md`: portable installation and usage.
- `references/knowledge-evaluator.md`: deterministic scoring and promotion contract.
