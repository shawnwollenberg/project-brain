# Artifact contracts

All structured artifacts use YAML and include:

```yaml
schema_version: "2.0.0"
artifact_type: "context-pack"
```

JSON Schemas use draft 2020-12 and live in `.project-brain/schemas/`.

## Knowledge lifecycle

`observation → proposed → reviewed → confirmed → encoded or retained → stale or superseded`

The proposer must not be the sole confirmer. A confirmed lesson requires a stable ID, title, scope, status, claim, evidence, confidence, observation date, verification date, optional `superseded_by`, and recommended future behavior.

Version 2 requires complete mission closure, review finding, proposed learning,
repository identity, and curation records. Version 1 repositories remain valid
against their Git-versioned local schemas. Use `migrate --dry-run` to inspect
impact; the tool creates a human-reviewable migration proposal and does not
invent missing historical evidence.

Repository identity precedence is explicit override, Git remote name, package
metadata, Git top-level name, then current-directory fallback. Profiles store
both a stable repository ID and the resolved checkout path.

## Evidence

Evidence entries are repository-relative references with a kind and optional SHA or command result. Evidence must be independently inspectable. A model assertion is not evidence.

For version 2 completed missions, Git SHAs must resolve to commits and file
evidence must be a safe repository-relative file that exists at validation
time. Explicit context references fail clearly when missing, unsupported, or
too large for the configured budget; expected sources may be listed under
`omitted_sources` with a reason.

## Deterministic retrieval order

1. Explicit references.
2. Expected files and parent paths.
3. Known issues related to those paths.
4. Component and tag matches.
5. Mission type and role matches.
6. Objective terms in filenames.
7. Objective terms in a bounded content sample.

Tie-break by score, then repository-relative path. Semantic retrieval may extend this later but must not silently replace deterministic selection.

Source retrieval includes Markdown and common implementation/config formats:
TypeScript/TSX, JavaScript/JSX, Go, Python, Rust, Java, Kotlin, SQL, GraphQL,
Protocol Buffers, shell, YAML, JSON, and TOML.

## Compatibility

Consumers must reject unsupported major schema versions and tolerate unknown optional fields in compatible minor versions.

## Knowledge evaluation

`knowledge-evaluation` artifacts are deterministic recommendations, not
promotion authority. They record the repository SHA, evaluator version,
inspectable experience events, per-proposal evidence/novelty/contradiction/
confidence/encoding results, and `human_approval: required`.

Confirmed v2.5 lessons store numeric confidence and experience counts. The
score changes only when inspectable evidence or recorded validation experience
changes.
