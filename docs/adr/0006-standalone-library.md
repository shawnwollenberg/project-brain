# ADR 0006: Project Brain is a standalone library

Status: Accepted

Mission Control and other orchestrators will consume Project Brain rather than own its knowledge system. Independent packaging and versioning prevent an orchestrator-specific lifecycle from becoming the de facto contract and allow provider-neutral reuse.
