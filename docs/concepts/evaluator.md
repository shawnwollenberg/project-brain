# Knowledge Evaluator

The evaluator is deterministic, local, inspectable, and non-promoting. It checks required fields, cited evidence, bounded lexical support, mission linkage, same-scope Jaccard similarity, conservative opposite-polarity conflicts, freshness signals, and encoding cues.

Recommendations include human review, merge, mission-local retention, more evidence, or conflict resolution. Encoding candidates cover reusable lessons, ADRs, playbooks, regression tests, policies, follow-up issues, stale/superseded states, and mission-local evidence. Every result records `human_approval: required`.

An optional future `ModelAssistedEvaluator` may add labeled judgments with cited inputs. It must remain an adapter, distinguish its judgments from deterministic findings, require no core model dependency, and possess no promotion authority.

## Confidence calculation

Evidence quality is 45% inspectable-evidence ratio, 30% bounded claim-term support, 15% evidence-kind diversity (capped at three), and 10% inspectable evidence quantity (capped at three). Confidence then uses:

```text
evidence_quality × (observed + 2×reused + 1)
÷ (observed + 2×reused + 2×contradicted + 2×superseded + 3)
```

Scores below 0.40 are low, 0.40–0.74 medium, and 0.75 or higher high. The report preserves inputs, repository-derived calculation time, algorithm version, and manual override history. Independent reviews and stronger encodings are visible basis signals but do not silently alter this version's score. A human override must append history rather than erase the calculated value.
