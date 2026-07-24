# Project Brain contributor instructions

- Run `python3 -m unittest discover -s tests -p 'test_*.py'` before committing.
- Run `project-brain validate --repo <fixture>` after changing schemas or generated artifacts.
- Keep `src/project_brain/resources/schemas/` authoritative; retain repository-local historical schemas.
- Preserve compatible minor fields and reject unsupported schema majors. Migrations propose changes and never fabricate evidence.
- Never automatically promote, merge, supersede, or encode knowledge. Human approval is mandatory.
- Update README/docs and `CHANGELOG.md` for public behavior changes.
- Add a migration proposal and tests for contract changes.
- Record consequential architecture choices as numbered ADRs in `docs/adr/`.
- Never commit secrets, full transcripts, hidden reasoning, real consumer data, or copied consumer repositories.
- Keep provider adapters thin; core behavior belongs in `src/project_brain/`.
