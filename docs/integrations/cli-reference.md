# CLI reference

All repository commands accept `--repo`; mutation is non-interactive and requires a clean worktree. Add `--format json` for automation.

| Command | Purpose | Mutates |
|---|---|---|
| `init --dry-run` | Preview repository profile and brain files | No |
| `init` | Initialize without overwriting existing files | Yes |
| `profile` | Inspect repository identity and signals | No |
| `prepare-context` | Build deterministic budgeted context | Only with `--output` |
| `close-mission` | Record mission outcome and evidence | Yes |
| `propose-learning` | Create a mission-backed proposed lesson | Yes unless `--dry-run` |
| `evaluate` | Produce a deterministic recommendation | Only with `--output` |
| `curate` | Produce review and patch recommendations | Only with output paths |
| `validate` | Validate schemas, evidence, SHAs, and secrets | No |
| `migrate --dry-run` | Assess compatibility | No |
| `migrate` | Write a migration proposal only | Yes |
| `doctor` | Diagnose package, skill, schema, and runtime compatibility | No |

Compatibility aliases `context` and `close` remain available. Human-readable YAML is the default output; JSON preserves the same data contract.
