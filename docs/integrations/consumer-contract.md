# Project Brain consumer contract 1.0

Project Brain owns repository knowledge, deterministic context selection, artifact contracts, evidence validation, knowledge evaluation, and lifecycle state. Consumers orchestrate missions, permissions, execution, user workflows, display projections, notifications, and audit history.

Git-versioned Project Brain artifacts remain authoritative. A consumer may index paths, checksums, and display projections but must not copy knowledge into a competing authority, invent evidence, mutate confirmed knowledge directly, or promote proposals automatically.

## Operations

| Operation | Classification | Automatic | Clean worktree | Git-visible artifact | Human approval |
|---|---|---:|---:|---:|---:|
| `detect_repository` | Read-only | Yes | No | No | No |
| `validate_repository` | Read-only | Yes | No | No | No |
| `get_summary` | Read-only | Yes | No | No | No |
| `prepare_context` | Read-only preview or repository-writing finalization | Yes | For write | Optional | No |
| `read_context` | Read-only | Yes | No | No | No |
| `record_closure` | Repository-writing | Yes after verified input | Yes | Yes | No |
| `propose_learning` | Proposal-producing | Yes | Yes | Yes | Required for later promotion |
| `evaluate_learning` | Proposal-producing recommendation | Yes | No unless output is written | Optional | Required |
| `get_curation` | Read-only recommendation | Yes | No | No | Required |
| `list_knowledge` | Read-only | Yes | No | No | No |
| `get_health` | Read-only | Yes | No | No | No |
| `diagnostics` | Read-only | Yes | No | No | No |

Machine-readable operation metadata is returned by `project-brain capabilities --json`.

## Envelope

Every operation returns contract version, operation, success/failure status, stable repository identity, checkout path, starting and ending HEAD, artifact paths/checksums/schema versions, warnings, blockers, required actions, human-approval requirement, mutation flag, automation exit classification, and operation data.

```json
{
  "contract_version": "1.0",
  "operation": "prepare_context",
  "status": "succeeded",
  "repository": {
    "id": "mission-control",
    "checkout_path": "/registered/worktree",
    "head_sha": "0123456789abcdef0123456789abcdef01234567",
    "ending_head_sha": "0123456789abcdef0123456789abcdef01234567"
  },
  "artifacts": [{
    "kind": "context_pack",
    "path": ".project-brain/context-packs/mission-1.yaml",
    "sha256": "...",
    "bytes": 4096,
    "schema_version": "2.5.0"
  }],
  "warnings": [],
  "blockers": [],
  "required_actions": [],
  "human_approval_required": false,
  "repository_files_changed": true,
  "exit_classification": "success",
  "data": {}
}
```

The Python boundary is `project_brain.consumer_operation`. The structured CLI boundary is:

```bash
project-brain consumer \
  --operation get_summary \
  --repo /explicit/registered/checkout \
  --contract-version 1.0 \
  --request-json '{}'
```

Failures use the same envelope and never use a traceback as their primary response.

## Compatibility

- Exact `1.0`: compatible.
- Older contract with the same major: accepted with a warning.
- Newer minor than installed: `older_installed`; operation fails before repository access.
- Different major or malformed version: incompatible.
- Missing CLI/package: the consumer reports diagnostics unavailable and does not fall back to another engine.
- Invalid repository brain: validation fails visibly; cached “valid” state must be cleared.
- Newer artifact schema: reject until a supporting package is installed.
- Older checked-in schema: validate historical artifacts against repository-local schemas when supported.

Consumers discover rather than infer these rules. Repository HEAD must be rebound or the operation retried when it changes between preview, execution, and closure.

## Security

Consumers invoke only allowlisted operations against an explicit registered checkout. They must use a known executable path, fixed working directory, argument arrays without shell interpolation, bounded timeout/output, environment allowlisting, local-only execution where applicable, captured stdout/stderr, envelope schema validation, and audit events. User-supplied arbitrary Project Brain commands are prohibited.

No operation grants knowledge-promotion authority.
