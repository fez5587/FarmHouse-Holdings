# PRD Addendum — Improvements and Reality Checks

**Companion to:** FarmHouse_Holdings_Product_Requirements.md v1.0
**Purpose:** Corrections, constraints, and additions based on the actual deployed environment (4-instance Ollama pool running qwen3.5:9b behind an API redirect, Hermes orchestration already set up, GitHub org created but empty).

---

## 1. Environment corrections to PRD Section 3

The PRD assumes Hermes 3 as the employee reasoning engine. Actual workforce is **qwen3.5:9b across 4 pooled Ollama instances**. This changes several design assumptions:

| PRD assumption | Reality | Consequence |
|---|---|---|
| "Hermes 3 or similar" reasoning engine | qwen3.5:9b (9B params) | Weaker multi-step reasoning; tasks must be decomposed smaller than PRD implies |
| Scheduler balances many workers | Hard cap: **4 concurrent inferences**, period | Scheduler v1 is a simple priority queue with 4 slots, not a complex placement engine |
| Long employee context/memory | ~11 GB VRAM per instance limits usable context (likely 8k–32k tokens depending on quant + KV cache) | Memory layers (PRD §15) must compress aggressively; no "dump the whole knowledge base" prompts |
| Employees run long agent loops | Small models drift, loop, and hallucinate tool calls over long horizons | Every task needs max-iteration caps, token budgets, and repetition detection (see §3 below) |

**Action:** run the capability gate in `PRE_IMPLEMENTATION_CHECKLIST.md` before building any org-model code. If qwen3.5:9b can't reliably emit valid structured messages or working code diffs, the whole employee model needs rethinking (bigger model, tighter task shapes, or heavier consultant reliance).

## 2. Strengthen PRD §13.4 — structured output must be *enforced*, not requested

The PRD says "do not rely on parsing free-form chat." Go further:

- Use Ollama's `format` parameter (JSON schema enforcement) for **every** agent→engine message. The model physically cannot emit non-conforming output.
- Keep schemas small and flat. 9B models degrade on deeply nested schemas.
- Validate server-side anyway; on failure, retry once with the error appended, then mark task blocked. Never silently accept malformed output.
- Version schemas from day one (`schema_version` field), as the PRD already requires for events.

## 3. New requirement — runaway protection for small models

Add to PRD §7.4 (anti-busy-work). Small local models fail differently than frontier models:

- **Per-task hard caps:** max agent-loop iterations (suggest 15), max total tokens, max wall-clock time. Exceeding any cap = task blocked with state preserved, escalate to manager.
- **Repetition detector:** if the model emits near-identical output N times in a row, kill the loop. Cheap check (hash last 3 responses), catches the most common 9B failure mode.
- **Self-assessment distrust:** the PRD already says completion requires evidence, not claims (§9.1). For a 9B model this is load-bearing — deterministic gates (tests pass, lint passes, diff applies) are the *only* completion signal. Never let the model's "done" flag advance state.

## 4. Role-based model routing (extends PRD §13)

One model for everything is wrong even locally. Route by role through the model gateway (LiteLLM, as PRD suggests):

- **Default workforce:** qwen3.5:9b — implementation tasks, summaries, test writing.
- **Coder-tuned variant** (e.g. qwen coder family, fits same VRAM): engineering employees. Worth benchmarking both in the capability gate.
- **Consultants:** Claude/OpenAI via LiteLLM with the PRD §10 budget controls. Practical trigger: any task blocked twice by the runaway caps in §3 auto-generates a consultant *proposal* (not an auto-call).
- Keep model aliases per *role*, not per employee, so swapping models later is one config change (PRD §23.3 preserved).

## 5. Tool gateway — standardize on MCP

PRD §14.1 lists a "tool gateway and isolated execution workers" without a protocol. Recommend **MCP (Model Context Protocol)** for tool exposure:

- Tools (git, shell, Playwright, file ops) become MCP servers; any agent runtime (Hermes Agent, custom loop, future frameworks) consumes them uniformly.
- Permission enforcement lives in the gateway between agent and MCP server — deterministic, outside the LLM, exactly as PRD §8 requires.
- Avoids coupling the platform to Hermes Agent's tool format (PRD §3: "do not hard-code to one agent framework").

## 6. MVP scope trim (amends PRD §20)

The PRD's MVP is ~6 months of work. Prove the risky core first with a smaller slice:

**Slice 1 (prove the engine):** one company, three employees (manager, engineer, QA), Postgres + Redis, structured agent protocol, git worktree isolation, one Playwright test run, evidence bundle, web dashboard read-only view, global pause. **No Discord, no 2D office, no consultants, no schedules.**

**Slice 2:** clarification/approval workflow + Discord channel + consultant path.

**Slice 3:** 2D office + schedules + autonomous work modes.

Rationale: PRD §24 itself says prove the company engine before visualization. Discord and the office are synchronized *views* (PRD §23.5) — they can't be validated until the engine emits real events anyway.

## 7. Observability — concrete picks (fills in PRD §17)

- **Langfuse (self-hosted)** for LLM traces: every prompt, response, latency, token count per employee/task. Purpose-built for exactly PRD §17's model metrics, runs in Docker next to Postgres.
- Engine events table in Postgres doubles as the audit log for v1 — no separate observability stack until it hurts.
- GPU metrics: `nvidia-smi` scrape into the same Postgres, chart later. Skip Prometheus/Grafana until multi-node pain is real.

## 8. Additional gaps worth one line each

- **Backpressure:** 4 slots means queue depth will grow. Dashboard must show queue depth per company from day one or "idle employees" will be a mystery.
- **Warm-model pinning:** with 4 instances and 1–2 models, pin models resident (Ollama `keep_alive=-1`) — cold starts on a 1080 Ti will dominate latency otherwise. PRD §13.3 allows this.
- **Time zone:** PRD sets `America/Indiana/Indianapolis` — store all timestamps UTC, convert at display. State it explicitly in the event schema ADR.
- **Company templates:** the new-company wizard (PRD §18.3) should stamp from a GitHub template repo (see GITHUB_INTEGRATION.md) — cheap and gives every company identical scaffolding.
- **Kill switch semantics:** define now whether "pause" drains in-flight inference or aborts it. Recommend: drain inference (seconds), abort tool executions (side effects). Ambiguity here bites during the first incident.
