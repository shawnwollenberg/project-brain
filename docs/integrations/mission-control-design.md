# Mission Control consumer design

Mission Control is an example consumer of contract 1.0, not a co-owner of Project Brain.

## Registration

Registration may detect `.project-brain/`, discover capabilities, validate it, store a display projection, and link artifact checksums. Initialization always requires an explicit repository workflow outside automatic registration.

## Preparation

1. Request context preview.
2. Display selected sources, reasons, quality metrics, warnings, and blockers.
3. Stop when preview fails.
4. Generate a final Git-visible pack.
5. Bind checksum, mission, execution, repository, starting SHA, contract, and schema.
6. Supply immutable verified contents to the assigned agent.

## Closure and learning

Mission Control passes verified SHAs and evidence to `record_closure`, indexes the returned artifact, and keeps failures visible. After closure it may request `propose_learning` and `evaluate_learning`, then display evidence, confidence, duplicates, contradictions, and recommended disposition. Promotion remains an explicit repository change workflow outside the initial UI.

## Failure states

- Missing CLI/package → diagnostics unavailable; show repair instructions.
- Not initialized → show status; never initialize automatically.
- Invalid artifact or unsupported schema → mark invalid/incompatible and block preparation.
- Dirty worktree → block writes while permitting read-only inspection.
- Missing explicit context or exceeded budget → show blocker; do not launch mission.
- Stale fingerprint → require reevaluation.
- Evidence unavailable → reject closure/proposal.
- HEAD mismatch → discard binding and regenerate context.

The first implementation is read-only except for explicitly requested mission-bound context generation. It adds no background synchronization or promotion action.
