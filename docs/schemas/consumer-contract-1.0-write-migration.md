# Consumer contract 1.0 explicit-write migration proposal

This is a proposal for consumer-call migration; it does not rewrite repository knowledge or fabricate evidence.

## Affected calls

- Replace implicit final context requests with `{"write": true, ...}`.
- Request `initialize_repository` only after exact repository-write approval.
- Keep context previews read-only by omitting `write` or setting it to `false`.
- Supply only repository-relative `output` paths to `evaluate_learning`.

## Compatibility and rollback

The contract version remains 1.0 because the response envelope and operation negotiation remain compatible.
Consumers discover operation metadata through `capabilities`. Rolling back the caller means omitting the new
initialization operation and explicit write request; existing repository artifacts remain authoritative and untouched.

## Validation

Run the consumer integration tests, validate an initialized disposable repository, and confirm initialization,
context, and evaluation artifacts remain within that repository. Human review is required before adopting this
migration in a consumer.
