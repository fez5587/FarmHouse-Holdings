# Slice 1 Acceptance Demo — verbatim script

This is the acceptance test for Slice 1 (PRD_ADDENDUM §6). When every step below works end-to-end, Slice 1 ships. Nothing outside this script is in scope.

## Cast

- Company: **GasWatch Inc.** (first real subsidiary; brief: track local gas prices, tiny web app)
- Employees: `Mara` (Manager), `Dev` (Engineer), `Quinn` (QA) — three Hermes profiles, qwen3.5:9b

## Script

1. `POST /companies` with the GasWatch brief → company row, event `company.created`, three employees hired (`employee.hired` ×3), Hermes profiles created via adapter.
2. Engine asks Mara to decompose the brief → Mara returns plan; engine creates ~3 work items (`work_item.created`), one flagged as needing clarification.
3. Clarification flows: Mara emits `clarification.requested` with 2–3 options + recommendation → surfaces in dashboard → user answers → `clarification.answered` → dependent task unblocks. Non-blocked tasks proceeded meanwhile.
4. Dev picks up the feature task: engine dispatches to Hermes (`dispatch.sent`), worktree created on an isolated branch, code committed. Every agent report lands as validated `AgentMessage` events.
5. Quinn runs pytest + one Playwright browser flow against the running app; screenshots + trace captured (`test.started` / `test.completed`, `artifact.created`).
6. Seeded defect found by Quinn → defect work item → Dev fixes → Quinn re-verifies (defect loop closed).
7. Evidence bundle assembled (commits, test output, screenshots, trace) → `artifact.created(kind=evidence_bundle)` → downloadable from dashboard.
8. Dashboard (read-only) showed live truthful states the whole time: employee status, work item board, event feed, cost tally (`cost.recorded` per run).
9. Runaway guard demonstrated: one task configured with `max_iterations: 2` trips `run.capped` and blocks cleanly instead of looping.
10. Global pause: `POST /pause` mid-run → no new dispatches, in-flight inference drains, tool executions abort, state consistent, resume works.

## Hard exit criteria

- Zero free-form parsing: every agent→engine message validated against `AgentMessage`.
- Event log replay tells the whole story; no state exists that lacks a causal event.
- `task.blocked` from any agent was triaged by Mara before surfacing to user.
- Kill Hermes mid-demo → engine marks run failed, work item re-dispatchable, no corruption.
