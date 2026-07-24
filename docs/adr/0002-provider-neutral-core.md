# ADR 0002: Provider-neutral core with thin adapters

Status: Accepted

All profiling, retrieval, mission, evaluation, curation, migration, security, and validation behavior belongs to the Python core. Provider adapters explain invocation and artifact exchange only. This avoids behavioral forks and permits Mission Control and other consumers to use the library directly.
