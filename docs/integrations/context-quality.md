# Context-quality accounting

Context packs distinguish the candidate repository corpus, initial selection, final selection, explicit sources, automatic sources, sources added after missing-context discovery, budget omissions, and unrelated-source exclusions.

```yaml
context_quality:
  completeness_status: revised
  candidate_bytes: 223062
  initial_selected_bytes: 28608
  final_selected_bytes: 88673
  reduction_percentage: 60.25
  missing_context_detected:
    - src/project_brain/core.py
  sources_added_after_missing_context_discovery:
    - src/project_brain/core.py
  revision_count: 1
  final_explicit_sources_complete: true
  relevant_source_precision: null
  optimality_claimed: false
```

`relevant_source_precision` remains null unless relevance has an inspectable ground truth. A small pack is never labeled optimal merely because it is small.

Consumers bind final packs to mission ID, execution ID, starting SHA, contract version, artifact checksum, and schema version.
