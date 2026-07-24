# Architecture

Project Brain separates durable repository knowledge from the provider that consumes it:

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

Git is the source of truth because it makes knowledge changes diffable, attributable, reviewable, and reproducible beside the code they describe. Markdown and YAML remain readable without this package. JSON Schema supplies machine contracts.

Retrieval is deterministic by default so inclusion can be explained, repeated, and bounded. Semantic retrieval may become an opt-in extension but cannot silently replace deterministic selection.

Agents cannot approve their own lessons because proposal and confirmation are different trust decisions. High-value lessons should become stronger mechanisms—tests, policies, playbooks, scripts, or ADRs—after human review.

Obsidian is an optional viewer for Markdown. It is neither required nor authoritative. Project Brain stores concise conclusions, evidence, and uncertainty, never chain-of-thought or transcripts.

Mission Control should consume the core because knowledge contracts need independent versioning and reuse across orchestrators, providers, and repositories.
