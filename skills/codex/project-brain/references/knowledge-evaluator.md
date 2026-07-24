# Knowledge Evaluator

The evaluator sits between proposed and confirmed knowledge. It is
deterministic, repository-local, inspectable, and non-promoting.

## Inputs

- Proposed, confirmed, stale, superseded, and peer proposed lessons.
- Repository-relative evidence files.
- Optional recorded experience events: `observed`, `reused`, `contradicted`,
  and `superseded`.
- Repository SHA and scope.

Every experience event requires a repository-relative evidence file. Its stable
ID is derived from learning ID, event type, and evidence reference. Repeated
evaluation deduplicates the same event.

## Evidence quality

Score from:

- 45% inspectable evidence ratio.
- 30% bounded claim-term support in evidence.
- 15% evidence-kind diversity, capped at three kinds.
- 10% inspectable evidence quantity, capped at three items.

Classify scores below 0.50 as weak, 0.50–0.74 as adequate, and 0.75 or greater
as strong.

This score proves inspectability and lexical support. It does not claim causal
or semantic proof beyond those deterministic checks.

## Novelty and contradictions

Novelty is `1 - maximum same-scope Jaccard claim similarity`. Exact same-scope
claims are duplicates. Similar claims in disjoint scopes are not merged.

Contradiction detection is deliberately conservative: normalize equivalent
claim text, remove explicit negative operators, and flag opposite polarity only
within overlapping scope. Ambiguous semantic disagreements require human
review and are not invented by the evaluator.

## Confidence

Confidence comes from evidence and recorded experience:

```text
evidence_quality
× (observed + 2×reused + 1)
÷ (observed + 2×reused + 2×contradicted + 2×superseded + 3)
```

Every proposal starts with one originating observation. Reuse increases
confidence faster than another observation. Contradiction and supersession
decrease confidence.

## Encoding

Rank these targets:

- reusable lesson;
- ADR;
- playbook;
- regression test;
- policy;
- follow-up issue;
- mission-local evidence.

Ranking uses explicit claim keywords, evidence kinds, and evidence quality.
Return a primary encoding plus close alternatives so a human can choose the
strongest justified mechanism.

## Promotion recommendation

Recommend exactly one:

- `human_review`
- `merge`
- `mission_local`
- `needs_evidence`
- `resolve_contradiction`

Every result records `human_approval: required` and
`automatic_promotion: false`. The evaluator never moves or edits lesson
lifecycle files.
