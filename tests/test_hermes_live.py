"""Live integration smoke for HermesClient against the real Hermes instance.

Creates a disposable profile + kanban task, verifies round-trips, cleans up.
Does NOT trigger a dispatch — no agent run, no GPU burn.

Run: .venv python -m pytest tests/test_hermes_live.py -v   (or python tests/test_hermes_live.py)
"""
import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.hermes_client import HermesClient, HermesError  # noqa: E402

TEST_PROFILE = "fh-smoke-test"
TEST_TENANT = "fh-smoke"
SOUL = "You are a FarmHouse smoke-test employee. You only ever say 'ok'."


async def cleanup(h: HermesClient) -> None:
    try:
        await h.delete_profile(TEST_PROFILE)
    except HermesError:
        pass
    board = await h.board(tenant=TEST_TENANT)
    for col in board.get("columns", []):
        for task in col.get("tasks", []):
            try:
                await h.delete_task(str(task["id"]))
            except HermesError:
                pass


async def main() -> None:
    h = HermesClient()
    try:
        # health
        st = await h.status()
        assert st["gateway_running"] is True, st
        print(f"status ok: hermes {st['version']}, gateway {st['gateway_state']}")

        await cleanup(h)  # in case a previous run died

        # profile round-trip
        await h.create_profile(TEST_PROFILE, soul=SOUL, model="qwen3.5:9b",
                               description="disposable smoke-test profile")
        soul = await h.get_soul(TEST_PROFILE)
        assert SOUL in soul, f"soul mismatch: {soul[:100]!r}"
        names = [p.get("name") for p in await h.list_profiles()]
        assert TEST_PROFILE in names, names
        print("profile round-trip ok")

        # kanban round-trip (no dispatch)
        wid = str(uuid.uuid4())
        task = await h.create_task(
            "Smoke: do nothing", body="Smoke-test task. Do not run.",
            assignee=TEST_PROFILE, tenant=TEST_TENANT,
            idempotency_key=wid, max_runtime_seconds=60, goal_max_turns=2,
        )
        task_id = str(task["id"])
        got = await h.get_task(task_id)
        assert got.get("idempotency_key") in (wid, None) or got.get("title") == "Smoke: do nothing", got
        print(f"kanban task created: id={task_id}, status={got.get('status')}")

        # idempotency: same key second time must not duplicate
        dup = await h.create_task(
            "Smoke: do nothing", body="dup", assignee=TEST_PROFILE, tenant=TEST_TENANT,
            idempotency_key=wid, max_runtime_seconds=60, goal_max_turns=2,
        )
        assert str(dup["id"]) == task_id, f"idempotency broken: {dup['id']} != {task_id}"
        print("idempotency ok")

        # status transition via engine-side patch
        await h.update_task(task_id, status="blocked", block_reason="smoke")
        assert (await h.get_task(task_id)).get("status") == "blocked"
        print("task update ok")

        await cleanup(h)
        # profile really gone
        assert TEST_PROFILE not in [p.get("name") for p in await h.list_profiles()]
        print("cleanup ok — ALL SMOKE CHECKS PASS")
    finally:
        await h.aclose()


def test_hermes_live() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
