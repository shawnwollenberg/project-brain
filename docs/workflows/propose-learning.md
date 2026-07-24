# Propose learning

Create a learning proposal only after its originating mission has been recorded and committed:

```bash
project-brain propose-learning \
  --repo . \
  --mission-id 2026-07-24-add-proposal-command \
  --claim "Mission-backed proposals preserve inspectable evidence" \
  --scope repository \
  --evidence file:src/project_brain/proposals.py \
  --proposer implementer \
  --dry-run
```

Remove `--dry-run` only in a clean worktree. Add `--format json` for automation.

For complex proposals, pass a YAML file:

```yaml
mission_id: 2026-07-24-add-proposal-command
claim: Mission-backed proposals preserve inspectable evidence
scope: [repository]
evidence:
  - kind: test
    reference: tests/test_proposals.py
proposed_by: implementer
recommended_future_behavior: Use the dedicated proposal operation after mission closure.
```

```bash
project-brain propose-learning --repo . --input proposal.yaml --dry-run
```

The operation validates the mission artifact, its starting and ending commits, evidence kinds and repository-relative paths, schema contracts, and likely secrets. It canonicalizes scope and evidence, derives a stable proposal ID, records a fingerprint covering lifecycle-relevant fields, and returns a no-op for an identical existing proposal. It never evaluates, curates, confirms, or promotes the proposal.
