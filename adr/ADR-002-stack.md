# ADR-002: Engine Technology Stack

**Status:** Accepted
**Date:** 2026-08-03

## Decision

FarmHouse company engine and supporting services:

- **Python 3.12+ / FastAPI** — engine API and workers. Matches Hermes ecosystem (uvicorn/FastAPI), Playwright and git tooling first-class.
- **PostgreSQL** — durable state, append-only event log, audit. Single DB, one schema per bounded area (`org`, `work`, `events`, `policy`).
- **Redis** — dispatch queue + pub/sub for live dashboard. (Postgres LISTEN/NOTIFY fallback if Redis proves unnecessary weight.)
- **httpx** client adapters: `hermes_client.py` (runtime), `ollama_client.py` (direct pool calls for engine-internal inference like scoring/routing).
- **React + Vite** dashboard (Slice 1: read-only). 2D engine choice deferred to Slice 3.
- **Docker Compose** for Postgres/Redis/engine; deployable to TrueNAS later.
- **Langfuse** self-hosted, deferred until after Slice 1 (Hermes has native Langfuse env hooks — free integration when enabled).

## Rejected

- **Node/NestJS** — second language for no gain; Playwright is the only draw and Python Playwright is fine.
- **LiteLLM now** — consultant phase only; Hermes providers + pool front cover local routing today.
- **Temporal/Celery** — Redis queue + engine dispatch loop is enough at 4-worker scale (`ponytail:` revisit if schedule complexity grows).
- **Microservices** — modular monolith per PRD §14.1.

## Versions pinned at adoption

- Hermes Agent 0.19.0 (TrueNAS, ports 30432/30433)
- Ollama pool front `192.168.1.5:4000` (workers 0.24.0 + 0.32.5)
- qwen3.5:9b Q4_K_M — capability-gated GO (benchmarks/RESULTS.md)
