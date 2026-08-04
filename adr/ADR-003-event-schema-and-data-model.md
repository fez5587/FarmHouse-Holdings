# ADR-003: Event Schema and Core Data Model

**Status:** Accepted
**Date:** 2026-08-03

## Decision

Sources of truth:

- `db/schema.sql` — DDL for the Slice 1 entity subset: company, employee, work_item, event, approval, artifact, tool_execution, cost_entry, policy_rule. Remaining PRD §14.3 entities (Schedule, KnowledgeItem, Incident, ConsultantEngagement, …) are added by the slice that needs them, not up front.
- `engine/schemas/events.py` — pydantic models. `AgentMessage` (agent→engine, enforced at inference via structured output) and `EventEnvelope` (immutable log record). The pydantic models ARE the schema; no parallel JSON-schema files to drift.

Key choices:

1. **Append-only event log in Postgres** with a trigger rejecting UPDATE/DELETE. Projections (work_item.status, employee.status) are ordinary tables updated in the same transaction as the event insert. No event-sourcing framework.
2. **Flat agent message schema.** One shape for all 12 agent message types, optional fields per type. Benchmarked at 100% validity on qwen3.5:9b under `format` enforcement; nested per-type schemas degrade small models and multiply retry logic.
3. **`task.blocked` is triage** (benchmark finding: model confuses blocked vs clarification vs approval). Engine manager step reclassifies before user-facing routing.
4. **Deny-by-default policy table.** `policy_rule` rows grant max authority per (company, employee, tool-glob, environment); most specific enabled rule wins; no matching rule = denied. Seeded globals: sandbox=2, internal=1, external/production=0. Every tool execution stores the decision it ran under.
5. **Runaway caps live in `work_item.budget`** (max_iterations 15, max_tokens 100k, max_wall_seconds 1800 default) and are engine-enforced; `run.capped` event fires when tripped (PRD_ADDENDUM §3).
6. **UUIDs everywhere, UTC timestamptz everywhere.** Display timezone (`America/Indiana/Indianapolis`) is a UI concern only.

## Rejected

- Kafka/NATS event bus — Postgres insert + Redis pub/sub notify covers 4-worker scale.
- Full event-sourcing (rebuild state from log) — projections are authoritative for current state; the log is authoritative for history and audit.
- Per-company database — schema-shared, row-scoped by company_id; revisit if isolation demands grow.
