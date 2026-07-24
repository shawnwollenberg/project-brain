# Schema versioning and migration

Packaged schemas under `src/project_brain/resources/schemas/` define contracts used for newly generated artifacts. A release documents compatible schema changes independently from the package version.

Initialization copies schemas into `.project-brain/schemas/`. Those copies remain in Git so historical artifacts validate against their original contracts. Consumers reject unsupported major versions and tolerate unknown optional fields in compatible minor versions.

Migrations are proposals. They identify required human work, preserve old artifacts, and never invent missing evidence, commits, reviewers, dates, or outcomes. A repository adopts new schemas only after its artifacts are compatible and the migration is reviewed.
