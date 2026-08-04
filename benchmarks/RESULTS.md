# Capability Gate Results — Step 1 of PRE_IMPLEMENTATION_CHECKLIST

**Date:** 2026-08-03
**Model:** qwen3.5:9b (9.7B, Q4_K_M, 6.6 GB)
**Pool front:** http://192.168.1.5:4000 (HAProxy)
**Verdict: GO.** All five capability gates pass. Platform build proceeds.

---

## Capability gates (run on Windows worker direct, model identical pool-wide)

| Suite | Cases | Score | Gate | Result |
|---|---|---|---|---|
| JSON schema validity (Ollama `format` enforcement) | 20 | **100%** | ≥95% | PASS |
| Correct protocol message type | 20 | **85%** | ≥80% | PASS |
| Tool selection + correct args (7-tool catalog) | 24 | **100%** | ≥80% | PASS |
| Code generation (executed against asserts) | 6 | **100%** | ≥50% | PASS |
| Instruction retention over 10 turns (incl. adversarial) | 10 | **100%** | ≥80% | PASS |

Raw data: `results/capability_qwen3.5_9b.json`. Suite runner: `bench_capability.py` (rerun per candidate model with `--model`).

### Known failure mode (design input for engine)

All 3 protocol-type misses confused escalation types: emitted `task.blocked` where `clarification.requested` or `approval.requested` was correct.
**Engine rule:** `task.blocked` = triage state. Manager (or deterministic check) reclassifies blocked reports before routing. Never route raw `blocked` straight to user.

## Pool topology (discovered)

- Front: HAProxy at `192.168.1.5:4000`, round-robin.
- Workers heterogeneous, identified by generation rate: ~80 tok/s (Windows box, Ollama 0.32.5), ~50 tok/s (×2, TrueNAS containers, 0.24.0), ~37 tok/s (likely the 1080 Ti, 0.24.0).
- Each worker serializes requests (`OLLAMA_NUM_PARALLEL=1` behavior confirmed on direct test: n requests = n× wall time).

## Infra numbers

| Metric | Pool front (:4000) | Windows worker direct |
|---|---|---|
| Warm single-stream | 38–51 tok/s (worker luck) | 77 tok/s |
| Aggregate at 4 concurrent | 137 tok/s (1.92× single) | 75 tok/s (1.06× — serial) |
| Aggregate at 8 concurrent | 177 tok/s | 76 tok/s |
| Cold load | 0.25 s | 0.74 s |
| 16k-token prompt eval | 9.1 s | 3.5 s |

Raw data: `results/infra_pool_front.json`, `results/infra_windows_worker_direct.json`.

## Scheduler consequences (feed into engine design)

1. **Plan for ~3 effective concurrent streams**, not 4 — heterogeneity + round-robin cost. Aggregate budget ≈ 140–180 tok/s at saturation.
2. **Round-robin is blind.** n=2 test landed both streams on slow workers (zero speedup). FarmHouse scheduler should eventually do least-busy dispatch straight to workers (or HAProxy leastconn) rather than trust the front. Not MVP-blocking.
3. **Interactive vs background lanes matter** (PRD §13.3): a user-facing request behind a 37 tok/s worker with queue = bad latency. Reserve fast worker for interactive lane when possible.
4. Cold starts trivial (<1 s) — models effectively always warm. `keep_alive` pinning nice-to-have, not critical.
5. 16k contexts fine pool-wide. Context budget per employee task: 16k safe ceiling for v1.

## Open item

`bench_capability.py --model <coder-variant>` not yet run — no coder-family model pulled on the pool. Optional: general model scored 100% on code suite; revisit only if real tasks expose weakness.
