# Security model

Project Brain scans generated and stored material for private keys, common access tokens, bearer headers, and credential assignments. It rejects unsafe or missing evidence references, symlink escapes, fake Git SHAs, invalid YAML, unsupported contracts, and mutation in dirty repositories.

Store secret names and operator instructions, never values. Do not store environment dumps, raw transcripts, cookies, authorization headers, hidden reasoning, or provider credentials. Evidence must be independently inspectable and repository-relative.

These deterministic checks reduce risk but do not replace secret-scanning infrastructure or human review.
