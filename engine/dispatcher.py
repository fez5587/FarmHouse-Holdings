"""Dispatch loop — the engine's heartbeat.

Every tick: send ready work items to Hermes kanban (bounded in-flight),
poll running ones, convert finished runs to protocol events, enforce
wall-clock budgets.

Slice 1 state mapping (ponytail: no separate review stage yet — completed
goes straight to done; anything unclear goes to blocked for manager triage):
    kanban running          -> in_progress (budget-checked)
    kanban blocked          -> blocked
    kanban review/done      -> extract AgentMessage ->
        task.completed      -> done
        anything else       -> blocked (reason = message summary)
"""
import asyncio
import logging
from datetime import datetime, timezone

from engine import db
from engine.hermes_client import HermesClient, HermesError
from engine.protocol import ceo_update, extract_agent_message

log = logging.getLogger("farmhouse.dispatcher")

TICK_SECONDS = 10
MAX_IN_FLIGHT = 3  # effective pool concurrency (benchmarks/RESULTS.md)

TASK_BODY_TEMPLATE = """{description}

## Acceptance criteria
{criteria}

## Reporting
End your work with a clear report: what you did, what you produced, test
evidence, and anything unresolved. If you need a human decision, say exactly
what decision and give 2-3 options with a recommendation.
"""


def _task_body(item: dict) -> str:
    criteria = "\n".join(f"- {c}" for c in item.get("acceptance_criteria") or []) or "- (none given)"
    return TASK_BODY_TEMPLATE.format(description=item["description"], criteria=criteria)


class Dispatcher:
    def __init__(self, hermes: HermesClient, is_paused) -> None:
        self.hermes = hermes
        self.is_paused = is_paused
        self._stop = asyncio.Event()
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await self._task

    async def _run(self) -> None:
        log.info("dispatcher started")
        while not self._stop.is_set():
            try:
                if not await self.is_paused():
                    await self.tick()
            except Exception:
                log.exception("tick failed")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=TICK_SECONDS)
            except asyncio.TimeoutError:
                pass
        log.info("dispatcher stopped")

    # ------------------------------------------------------------ one tick

    async def tick(self) -> None:
        await self._poll_in_flight()
        await self._dispatch_ready()
        await self._roll_up_objectives()

    async def _roll_up_objectives(self) -> None:
        rows = await db.fetch_all(
            """
            SELECT o.id, o.company_id, o.title, o.owner_id, c.name AS company_name
            FROM work_item o JOIN company c ON c.id = o.company_id
            WHERE o.type = 'objective' AND o.status = 'in_progress'
              AND EXISTS (SELECT 1 FROM work_item c WHERE c.parent_id = o.id)
              AND NOT EXISTS (SELECT 1 FROM work_item c
                              WHERE c.parent_id = o.id AND c.status NOT IN ('done','cancelled'))
            """
        )
        for row in rows:
            children = await db.fetch_all(
                "SELECT title, status FROM work_item WHERE parent_id=%s ORDER BY created_at",
                row["id"])
            task_lines = [f"{c['title']} ({c['status']})" for c in children]
            try:
                update = await ceo_update(row["company_name"], row["title"], task_lines)
            except Exception:
                log.exception("ceo_update failed; falling back to plain summary")
                update = (f"Milestone reached: {row['title']} — "
                          f"all {len(children)} tasks closed.")
            async with db.pool.connection() as conn:
                async with conn.transaction():
                    await conn.execute(
                        "UPDATE work_item SET status='done', updated_at=now() WHERE id=%s",
                        (row["id"],))
                    await db.append_event(conn, actor="system", event_type="work_item.updated",
                                          company_id=row["company_id"], work_item_id=row["id"],
                                          payload={"status": "done", "note": "all child tasks done"})
                    await db.append_event(
                        conn, actor=f"employee:{row['owner_id']}",
                        event_type="milestone.update",
                        company_id=row["company_id"], work_item_id=row["id"],
                        payload={"objective_title": row["title"], "summary": update})
            log.info("objective %s rolled up to done", row["id"])

    async def _dispatch_ready(self) -> None:
        in_flight = (await db.fetch_one(
            "SELECT count(*) AS n FROM work_item WHERE status = 'in_progress'"))["n"]
        slots = MAX_IN_FLIGHT - in_flight
        if slots <= 0:
            return
        ready = await db.fetch_all(
            """
            SELECT wi.*, e.hermes_profile, e.id AS employee_id, c.slug AS company_slug,
                   c.config AS company_config
            FROM work_item wi
            JOIN employee e ON e.id = wi.owner_id
            JOIN company c ON c.id = wi.company_id
            WHERE wi.status = 'ready' AND wi.type IN ('task','subtask','defect')
              AND c.lifecycle_state = 'active' AND e.hermes_profile IS NOT NULL
            ORDER BY wi.created_at LIMIT %s
            """, slots,
        )
        for item in ready:
            await self._dispatch_one(item)

    async def _sibling_context(self, item: dict) -> str:
        """Completed-sibling reports appended to the task body: kanban runs are
        isolated, so without this each task is blind to its siblings' output."""
        if not item.get("parent_id"):
            return ""
        rows = await db.fetch_all(
            """
            SELECT e.payload FROM event e
            JOIN work_item w ON w.id = e.work_item_id
            WHERE w.parent_id = %s AND w.id <> %s AND w.status = 'done'
              AND e.event_type = 'task.completed'
            ORDER BY e.created_at
            """, item["parent_id"], item["id"])
        lines = []
        for r in rows:
            p = r["payload"] or {}
            s = p.get("summary") or p.get("detail")
            if s:
                lines.append(f"- {str(s)[:400]}")
        if not lines:
            return ""
        return ("\n\n## What teammates already completed on this objective\n"
                + "\n".join(lines)
                + "\nDo not assume their intermediate files exist; only the "
                "shared workspace directory persists between runs.")

    async def _dispatch_one(self, item: dict) -> None:
        budget = item["budget"]
        try:
            task = await self.hermes.create_task(
                item["title"],
                body=_task_body(item) + await self._sibling_context(item),
                assignee=item["hermes_profile"],
                tenant=item["company_slug"],
                idempotency_key=str(item["id"]),
                max_runtime_seconds=int(budget.get("max_wall_seconds", 1800)),
                goal_max_turns=int(budget.get("max_iterations", 15)),
                workspace_path=(item.get("company_config") or {}).get("workspace_path"),
            )
            await self.hermes.dispatch_now()
        except HermesError as e:
            # block instead of retrying every tick: dispatch 4xx is config, not transient
            log.warning("dispatch failed for %s: %s", item["id"], e)
            async with db.pool.connection() as conn:
                async with conn.transaction():
                    await conn.execute(
                        "UPDATE work_item SET status='blocked', updated_at=now() WHERE id=%s",
                        (item["id"],))
                    await db.append_event(conn, actor="system", event_type="dispatch.failed",
                                          company_id=item["company_id"], work_item_id=item["id"],
                                          payload={"error": str(e)[:300]})
            return
        async with db.pool.connection() as conn:
            async with conn.transaction():
                await conn.execute(
                    "UPDATE work_item SET status='in_progress', hermes_task_id=%s, "
                    "dispatched_at=now(), updated_at=now() WHERE id=%s",
                    (str(task["id"]), item["id"]),
                )
                await conn.execute(
                    "UPDATE employee SET status='working' WHERE id=%s", (item["employee_id"],))
                await db.append_event(
                    conn, actor="system", event_type="dispatch.sent",
                    company_id=item["company_id"], work_item_id=item["id"],
                    payload={"hermes_task_id": str(task["id"]),
                             "assignee": item["hermes_profile"]},
                )
        log.info("dispatched %s -> %s", item["title"][:40], task["id"])

    # ------------------------------------------------------------ polling

    async def _poll_in_flight(self) -> None:
        # blocked items are polled too: Hermes retries transient blocks itself,
        # so a blocked work item whose kanban task is active again must resume
        items = await db.fetch_all(
            "SELECT wi.*, e.id AS employee_id FROM work_item wi "
            "JOIN employee e ON e.id = wi.owner_id "
            "WHERE wi.status IN ('in_progress','blocked') AND wi.hermes_task_id IS NOT NULL"
        )
        for item in items:
            try:
                kt = await self.hermes.get_task(item["hermes_task_id"])
            except HermesError as e:
                log.warning("poll failed for %s: %s", item["hermes_task_id"], e)
                continue
            status = kt.get("status")
            if item["status"] == "blocked":
                # resume only on ACTIVE kanban states; a done/review kanban task
                # under a blocked item was already classified — re-finishing it
                # every tick would spam events and duplicate cost entries
                if status in ("running", "ready", "todo", "scheduled"):
                    await self._resume(item)
                continue
            if status in ("review", "done"):
                await self._finish(item, kt)
            elif status == "blocked":
                await self._block(item, kt.get("block_reason") or "hermes reported blocked",
                                  event_type="task.blocked")
            elif await self._over_budget(item):
                await self._cap(item, kt)
            # todo/scheduled/ready/running: still waiting

    async def _resume(self, item: dict) -> None:
        async with db.pool.connection() as conn:
            async with conn.transaction():
                await conn.execute(
                    "UPDATE work_item SET status='in_progress', updated_at=now() WHERE id=%s",
                    (item["id"],))
                await conn.execute(
                    "UPDATE employee SET status='working' WHERE id=%s", (item["employee_id"],))
                await db.append_event(conn, actor="system", event_type="task.resumed",
                                      company_id=item["company_id"], work_item_id=item["id"],
                                      payload={"note": "hermes task active again"})
        log.info("resumed %s", item["id"])

    async def _over_budget(self, item: dict) -> bool:
        if not item["dispatched_at"]:
            return False
        max_wall = int(item["budget"].get("max_wall_seconds", 1800))
        elapsed = (datetime.now(timezone.utc) - item["dispatched_at"]).total_seconds()
        return elapsed > max_wall

    async def _cap(self, item: dict, kt: dict) -> None:
        run_id = kt.get("current_run_id")
        if run_id:
            try:
                await self.hermes.terminate_run(str(run_id))
            except HermesError:
                pass
        try:
            await self.hermes.update_task(item["hermes_task_id"], status="blocked",
                                          block_reason="farmhouse: wall-clock budget exceeded")
        except HermesError:
            pass
        await self._block(item, "wall-clock budget exceeded", event_type="run.capped")

    async def _block(self, item: dict, reason: str, *, event_type: str,
                     payload: dict | None = None) -> None:
        async with db.pool.connection() as conn:
            async with conn.transaction():
                await conn.execute(
                    "UPDATE work_item SET status='blocked', updated_at=now() WHERE id=%s",
                    (item["id"],))
                await conn.execute(
                    "UPDATE employee SET status='blocked' WHERE id=%s", (item["employee_id"],))
                await db.append_event(conn, actor=f"employee:{item['employee_id']}",
                                      event_type=event_type, source="hermes",
                                      company_id=item["company_id"], work_item_id=item["id"],
                                      payload={**(payload or {}), "reason": reason})
        log.info("blocked %s: %s", item["id"], reason)

    async def _finish(self, item: dict, kt: dict) -> None:
        raw = kt.get("result") or kt.get("summary") or "(no report)"
        try:
            msg = await extract_agent_message(str(item["id"]), raw)
        except Exception as e:
            await self._block(item, f"protocol extraction failed: {e}", event_type="task.blocked")
            return

        wall = None
        if item["dispatched_at"]:
            wall = (datetime.now(timezone.utc) - item["dispatched_at"]).total_seconds()

        if msg.message_type == "task.completed":
            new_status = "done"
        else:
            # ponytail: blocked-for-triage covers clarification/approval/progressed;
            # manager triage flow upgrades this in the next increment
            new_status = "blocked"

        async with db.pool.connection() as conn:
            async with conn.transaction():
                await conn.execute(
                    "UPDATE work_item SET status=%s, updated_at=now() WHERE id=%s",
                    (new_status, item["id"]))
                await conn.execute(
                    "UPDATE employee SET status=%s WHERE id=%s",
                    ("idle" if new_status == "done" else "blocked", item["employee_id"]))
                await db.append_event(
                    conn, actor=f"employee:{item['employee_id']}",
                    event_type=msg.message_type, source="hermes",
                    company_id=item["company_id"], work_item_id=item["id"],
                    payload=msg.model_dump(exclude_defaults=True),
                    provenance={"hermes_run_id": str(kt.get("current_run_id") or ""),
                                "hermes_task_id": item["hermes_task_id"]},
                )
                if wall is not None:
                    await conn.execute(
                        "INSERT INTO cost_entry (company_id, employee_id, work_item_id, kind, "
                        "wall_seconds) VALUES (%s,%s,%s,'local_inference',%s)",
                        (item["company_id"], item["employee_id"], item["id"], round(wall, 1)))
                    await db.append_event(conn, actor="system", event_type="cost.recorded",
                                          company_id=item["company_id"], work_item_id=item["id"],
                                          payload={"wall_seconds": round(wall, 1)})
        log.info("finished %s -> %s (%s)", item["id"], new_status, msg.message_type)
