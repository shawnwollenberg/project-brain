# Python library API

All public operations execute the same in-process parser and core as the console command; consumers do not need to shell out.

```python
from project_brain import propose_learning

preview = propose_learning(
    ".",
    mission_id="2026-07-24-add-proposal-command",
    claim="Mission-backed proposals preserve inspectable evidence",
    scope=["repository"],
    evidence=["test:tests/test_proposals.py"],
    proposer="implementer",
    dry_run=True,
)

assert preview.exit_code == 0
assert preview.data["status"] == "dry-run"
assert preview.data["proposal"]["status"] == "proposed"
```

`CommandResult` exposes `exit_code`, parsed `data`, rendered `text`, and `changed_files`. Validation failures return exit code 2 and diagnostic text. Library and CLI operations share mutation, dirty-worktree, schema, evidence, secret, and human-approval boundaries.
