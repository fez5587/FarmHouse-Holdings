# Pre-Implementation Checklist

Ordered steps before writing platform code. Each step has an exit criterion. Do not skip step 1 — everything downstream depends on it.

---

## Step 1: Capability gate — benchmark qwen3.5:9b (1–2 days)

The entire employee model assumes the local model can do the work. Verify before building.

**Infrastructure benchmarks** (script against the HAProxy/pool endpoint):
- [ ] Warm tokens/sec per instance, and with all 4 instances loaded concurrently
- [ ] Cold-start time (model load) vs warm request — PRD §3 requires distinguishing these
- [ ] Max usable context before VRAM pressure/OOM on the 1080 Ti (test 8k, 16k, 32k)
- [ ] Behavior when a 5th request arrives: queue latency through the pool redirect
- [ ] Host RAM headroom on each instance under load

**Capability benchmarks** (20–30 fixed test cases each, scored pass/fail):
- [ ] **JSON schema compliance:** emit valid `task.progressed`, `clarification.requested`, etc. messages with Ollama `format` enforcement — target ≥95% valid
- [ ] **Tool call selection:** given 5–8 tool descriptions, pick the right tool with right args — target ≥80%
- [ ] **Code generation:** small full-stack tasks (add endpoint, write test, fix seeded bug) — measure % producing an applying, passing diff
- [ ] **Instruction retention:** does it still follow the system prompt after 10 loop iterations
- [ ] Same suite against a qwen coder-family variant that fits 11 GB — pick per-role winners

**Exit criterion:** written scores in `benchmarks/RESULTS.md`. If JSON compliance <90% or code tasks <50%, stop and rethink model choice before proceeding.

## Step 2: Decide agent runtime (half day)

- [ ] Evaluate whether existing Hermes Agent setup can: enforce max iterations, emit the structured protocol, call MCP tools, and hand control back to an external engine per step
- [ ] If not cleanly: write a minimal custom loop (~200 lines: prompt → structured response → engine records event → next step). The engine owns state either way (PRD §3)
- [ ] Record decision as ADR-001

## Step 3: Pick the stack (half day, write it down)

Recommendation (fits ecosystem, one language, boring choices):

- [ ] **Python 3.12 + FastAPI** — engine API, agent loop, tool workers (Playwright, git libs all first-class)
- [ ] **PostgreSQL** — durable state + event log + audit (PRD §14)
- [ ] **Redis** — task queue + pub/sub for live dashboard updates
- [ ] **LiteLLM** — model gateway (local pool + consultant providers, budgets, accounting)
- [ ] **Docker** — sandboxed tool execution
- [ ] **React + Vite** — dashboard; defer 2D engine choice (PixiJS vs Phaser) until Slice 3
- [ ] **Langfuse** — LLM tracing
- [ ] Record as ADR-002 with rejected alternatives

## Step 4: GitHub setup (half day)

- [ ] Execute `GITHUB_INTEGRATION.md` steps 1–4 (org structure, platform repo, company template repo, GitHub App)

## Step 5: Core schemas before code (1–2 days)

- [ ] Event schema v1: the ~12 message types from PRD §13.4, with envelope (event ID, company, actor, correlation, timestamp, schema_version, policy decision)
- [ ] Draft DDL for the load-bearing subset of PRD §14.3 entities: Company, Employee, WorkItem, Event, Approval, Artifact, ToolExecution, CostEntry — defer the rest until needed
- [ ] Authority levels 0–5 as a policy table: (role, tool, environment) → max level; enforcement point in the tool gateway
- [ ] Record as ADR-003

## Step 6: Define the Slice 1 demo script (1 hour)

Write the exact demo before building it (amended MVP from PRD_ADDENDUM.md §6):

- [ ] One company created from a brief; manager decomposes into ~3 tasks
- [ ] Engineer employee implements a small feature in an isolated git worktree, on the pool
- [ ] QA employee runs an automated + Playwright check, files one seeded defect
- [ ] Engineer fixes, QA re-verifies, evidence bundle lands in artifact storage
- [ ] Dashboard shows live states; global pause stops cleanly mid-task
- [ ] Every state transition visible as events in Postgres

**Exit criterion:** this script becomes the Slice 1 acceptance test, verbatim.

## Step 7: Risk register (1 hour)

Top risks to track (revisit after Step 1 results):

1. **qwen3.5:9b too weak for autonomous coding** — mitigation: capability gate first; smaller task shapes; consultant escalation path
2. **4-slot throughput too low for multi-company** — mitigation: measure in Step 1; strict background preemption; single company until it hurts
3. **Runaway loops burn compute silently** — mitigation: hard caps + repetition detection before any autonomous mode ships
4. **Scope explosion** (PRD is a platform, a game, and an org sim) — mitigation: slice discipline; nothing outside current slice
5. **State corruption on worker death mid-task** — mitigation: idempotent task steps, event-sourced state, resume-from-last-event tested in Slice 1

---

## Explicit open questions for Philip

1. Consultant budget: which external providers approved, monthly cap in dollars?
2. Discord server — already created? Bot application registered?
3. First real company/project to run through the system once Slice 1 works?
4. Where does artifact/object storage live — TrueNAS share, MinIO, or plain disk?
5. Is the Hermes Agent setup something to preserve, or replaceable if Step 2 finds friction?
