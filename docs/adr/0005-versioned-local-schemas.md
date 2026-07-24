# ADR 0005: Versioned repository-local schemas

Status: Accepted

The package owns schemas for new generation. Initialization copies them into each repository so historical artifacts remain reproducible after Project Brain upgrades. Unsupported majors are rejected; migrations remain proposal-only.
