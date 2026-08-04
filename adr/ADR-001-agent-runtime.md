# ADR-001: Agent Runtime — Build on Hermes Agent

**Status:** Accepted
**Date:** 2026-08-03

## Context

PRD §13.1 separates the company engine from the agent runtime. Checklist Step 2 required evaluating the existing Hermes Agent deployment before deciding build-vs-integrate.

Discovery of the running instance (TrueNAS, `192.168.1.5`, dashboard :30433, OpenAI-compatible API server :30432, version 0.19.0) found far more capability than assumed:

- **Kanban orchestration plugin:** boards, tasks, auto-decomposition, dispatch loop (60s tick), worker runs, per-profile in-progress limits, reassignment, run inspection/termination
- **Profiles:** persistent personas with own soul (system prompt), model, setup command — direct fit for FarmHouse employees
- **Git integration:** worktree add/remove, branches, staged review, commit, push, PR creation
- **MCP server management:** catalog install, per-server enable/auth/test
- **Toolsets** with per-toolset config/env/model; tool-loop guardrails built in
- **Cron jobs** with blueprints and delivery targets
- **Memory providers**, session store, session search/export
- **Messaging platforms** incl. Discord (bot token slot present, unset)
- **Webhooks** (outbound events), gateway drain/restart, checkpoints/backup, Langfuse env hooks

Model: qwen3.5:9b (matches pool). Gateway `api_server.max_concurrent_runs: 10`. Kanban `auto_decompose: true`, `dispatch_in_gateway: true`.

## Decision

**Use Hermes Agent as the agent runtime and tool executor. Build the FarmHouse company engine as a separate service that is the sole source of truth.**

Layer mapping (PRD §13.1):

| PRD layer | Implementation |
|---|---|
| Company engine | **New FastAPI service** — companies, employees, work items, events, policy, budgets, approvals |
| Agent runtime | **Hermes Agent** — reasoning loop, tool selection, guardrails |
| Model gateway | Hermes providers + Ollama pool front (`192.168.1.5:4000`); LiteLLM deferred until consultant phase |
| Load balancer | Existing HAProxy front |
| Tool workers | Hermes toolsets + MCP servers |

Integration contract:

1. FarmHouse employee ↔ Hermes **profile** (engine creates/updates profiles via `/api/profiles`).
2. FarmHouse work item execution ↔ Hermes **kanban task** dispatch (`/api/plugins/kanban/*`) or direct `api_server` run — engine chooses per task type.
3. Events back via Hermes **webhooks** → engine event log. Engine polls run status as fallback.
4. Engine holds all durable state. Hermes sessions/kanban are execution artifacts, never the record. If Hermes is wiped, companies and history survive; only in-flight runs are lost.
5. Engine-side policy checks gate every dispatch (authority levels, budgets) before anything reaches Hermes.

## Consequences

- Months of runtime work avoided (agent loop, worktrees, MCP, Discord path, cron).
- Risk: Hermes is a moving dependency (0.19.0, fast release cadence) — pin the deployed version; integration goes through a thin `hermes_client.py` adapter so the engine never calls Hermes endpoints directly from business logic.
- Hermes auto-decompose/orchestrator overlaps with FarmHouse manager employees — disable kanban auto-decompose for engine-managed boards; decomposition is a manager (engine) responsibility.
- `API_SERVER_KEY` for :30432 lives in the container env (unset in UI env store) — needs to be set/read on TrueNAS for engine → api_server auth. Open item.
- Discord later rides Hermes messaging (set `DISCORD_BOT_TOKEN`) instead of a new bot service — revisit at Milestone 5.
