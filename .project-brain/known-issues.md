# Known issues

## Current technical debt

- `src/project_brain/core.py` still combines repository inspection, context retrieval, mission closure, evaluation, curation, migration, validation, and CLI argument construction. Knowledge normalization and proposal creation have been extracted; further decomposition should follow behavior-driven boundaries.
- Mission closure can still create a learning proposal for compatibility. The dedicated `propose-learning` workflow is preferred because it independently validates the recorded mission.
- Semantic retrieval, organizational memory, model-assisted evaluation, provider APIs, Mission Control integration, web UI, databases, vectors, and background workers remain intentionally out of scope.
- The repository has a configured remote inherited from its initial creation. The 0.3.0 milestone must not push to it.
