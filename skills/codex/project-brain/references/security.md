# Security

- Never write secret values, access tokens, private keys, cookies, authorization headers, wallet seeds, environment dumps, or provider credential files.
- Scan proposed content before writing. Treat AWS access keys, GitHub tokens, private-key headers, high-entropy bearer tokens, and credential assignments as blocking findings.
- Record only the name of a required secret and where an operator should configure it.
- Never store hidden chain-of-thought or raw model transcripts. Store concise conclusions, decisions, evidence, and uncertainties.
- Keep author, proposer, reviewer, timestamps, and source evidence intact.
- Refuse ambiguous repository roots, unsupported schema majors, invalid YAML, missing required evidence, and mutating operations in dirty worktrees.
- Never follow symlinks outside the repository when scanning or writing.
- Migration must not synthesize evidence, overwrite historical artifacts, or
  promote learnings. Generate a reviewable proposal when human judgment is
  required.
