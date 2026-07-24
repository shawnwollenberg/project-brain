# ADR 0007: Require explicit consumer write intent

Status: accepted

## Context

Mission Control needs to initialize Project Brain and persist lifecycle artifacts through the provider-neutral consumer
contract. Inferring write intent from a missing preview flag makes remote authorization ambiguous and weakens exact
approval binding.

## Decision

Consumer contract 1.0 exposes `initialize_repository` as an explicit, approval-gated repository-writing operation.
`prepare_context` remains read-only unless `write: true` is present. Optional evaluation output must be a
repository-relative contained path and is returned as a checksummed artifact.

## Consequences

Consumers can bind policy and approval to an exact write operation and scope. Existing callers that omitted both
`preview` and `write` now receive an in-memory context result and must explicitly opt into persistence. No operation
receives general repository-write or knowledge-promotion authority.
