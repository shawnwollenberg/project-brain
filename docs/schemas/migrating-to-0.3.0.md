# Migrating to Project Brain 0.3.0

Package 0.3.0 remains on artifact schema 2.5.0. Existing repository-local v1 schemas remain authoritative for their historical v1 artifacts. No automatic artifact rewrite is required.

New 2.5 evaluations include a proposal fingerprint and stricter evidence-kind contracts. Existing proposals must be reevaluated before curation when claim, scope, evidence, status, or source mission differs from the fingerprinted evaluation. Stored experience IDs must equal the canonical learning/event/evidence tuple.

Recommended sequence:

```bash
project-brain migrate --repo . --dry-run
project-brain validate --repo .
project-brain evaluate --repo . --learning LEARNING_ID
project-brain curate --repo .
```

Never fabricate missing evidence, SHAs, missions, reviewers, or experience events. Migration remains proposal-only and promotion remains human-gated.
