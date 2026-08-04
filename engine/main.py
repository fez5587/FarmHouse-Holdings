"""FarmHouse engine API — Slice 1 core.

Run: uvicorn engine.main:app --reload --port 8100
"""
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from engine import db
from engine.config import settings
from engine.dispatcher import Dispatcher
from engine.hermes_client import HermesClient, HermesError
from engine.protocol import decompose_objective
from engine.souls import ROLE_CHARTERS, build_soul

PAUSE_KEY = "farmhouse:paused"

hermes = HermesClient()
redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
dispatcher = Dispatcher(hermes, is_paused=lambda: is_paused())


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.open_pool()
    dispatcher.start()
    yield
    await dispatcher.stop()
    await db.close_pool()
    await hermes.aclose()
    await redis_client.aclose()


app = FastAPI(title="FarmHouse Holdings Engine", version="0.1.0", lifespan=lifespan)

# ---------------------------------------------------------------- request models


class EmployeeSpec(BaseModel):
    name: str
    title: str
    role: str  # manager | engineer | qa

    def validate_role(self) -> None:
        if self.role not in ROLE_CHARTERS:
            raise HTTPException(422, f"unknown role {self.role!r}; valid: {sorted(ROLE_CHARTERS)}")


class CompanyCreate(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,40}$")
    name: str
    brief: str
    employees: list[EmployeeSpec] = Field(min_length=1)


# ---------------------------------------------------------------- helpers


def profile_name(company_slug: str, employee_name: str) -> str:
    return f"fh-{company_slug}-{employee_name.lower().replace(' ', '-')}"


async def is_paused() -> bool:
    return await redis_client.get(PAUSE_KEY) == "1"


# ---------------------------------------------------------------- endpoints


@app.get("/health")
async def health() -> dict:
    row = await db.fetch_one("SELECT count(*) AS companies FROM company")
    return {"status": "ok", "companies": row["companies"], "paused": await is_paused()}


@app.post("/companies", status_code=201)
async def create_company(body: CompanyCreate) -> dict:
    for spec in body.employees:
        spec.validate_role()
    if await db.fetch_one("SELECT id FROM company WHERE slug = %s", body.slug):
        raise HTTPException(409, f"company {body.slug!r} already exists")

    async with db.pool.connection() as conn:
        async with conn.transaction():
            cur = await conn.execute(
                "INSERT INTO company (slug, name, description, lifecycle_state) "
                "VALUES (%s, %s, %s, 'active') RETURNING id",
                (body.slug, body.name, body.brief),
            )
            company_id = (await cur.fetchone())["id"]
            await db.append_event(conn, actor="user:philip", event_type="company.created",
                                  company_id=company_id, source="api",
                                  payload={"slug": body.slug, "name": body.name})

            employees = []
            for spec in body.employees:
                cur = await conn.execute(
                    "INSERT INTO employee (company_id, name, title, role, hermes_profile) "
                    "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                    (company_id, spec.name, spec.title, spec.role,
                     profile_name(body.slug, spec.name)),
                )
                emp_id = (await cur.fetchone())["id"]
                await db.append_event(conn, actor="system", event_type="employee.hired",
                                      company_id=company_id,
                                      payload={"employee_id": str(emp_id), "name": spec.name,
                                               "title": spec.title, "role": spec.role})
                employees.append({"id": emp_id, "spec": spec})

    # Hermes profiles outside the tx: DB is source of truth; profile creation is
    # retryable. Failure leaves employees hired with a repairable profile gap.
    profile_errors = []
    for emp in employees:
        spec = emp["spec"]
        try:
            await hermes.create_profile(
                profile_name(body.slug, spec.name),
                soul=build_soul(spec.role, name=spec.name, title=spec.title, company_name=body.name),
                model="qwen3.5:9b",
                description=f"{body.name}: {spec.title}",
            )
        except HermesError as e:
            profile_errors.append({"employee": spec.name, "error": str(e)[:200]})

    return {
        "company_id": str(company_id),
        "slug": body.slug,
        "employees": [{"id": str(e["id"]), "name": e["spec"].name} for e in employees],
        "profile_errors": profile_errors,
    }


@app.get("/companies")
async def list_companies() -> list[dict]:
    rows = await db.fetch_all(
        "SELECT c.*, count(e.id) AS employee_count FROM company c "
        "LEFT JOIN employee e ON e.company_id = c.id GROUP BY c.id ORDER BY c.created_at"
    )
    return [db.as_json(r) for r in rows]


@app.get("/companies/{slug}")
async def get_company(slug: str) -> dict:
    company = await db.fetch_one("SELECT * FROM company WHERE slug = %s", slug)
    if not company:
        raise HTTPException(404, "no such company")
    employees = await db.fetch_all(
        "SELECT id, name, title, department, status, authority_level, hermes_profile "
        "FROM employee WHERE company_id = %s ORDER BY created_at", company["id"]
    )
    return db.as_json({**company, "employees": employees})


@app.get("/companies/{slug}/events")
async def company_events(slug: str, limit: int = 50) -> list[dict]:
    company = await db.fetch_one("SELECT id FROM company WHERE slug = %s", slug)
    if not company:
        raise HTTPException(404, "no such company")
    rows = await db.fetch_all(
        "SELECT * FROM event WHERE company_id = %s ORDER BY created_at DESC LIMIT %s",
        company["id"], limit,
    )
    return [db.as_json(r) for r in rows]


@app.delete("/companies/{slug}", status_code=204)
async def archive_company(slug: str) -> None:
    """Archive (lifecycle change + Hermes profile removal). Rows are kept."""
    company = await db.fetch_one("SELECT * FROM company WHERE slug = %s", slug)
    if not company:
        raise HTTPException(404, "no such company")
    employees = await db.fetch_all(
        "SELECT hermes_profile FROM employee WHERE company_id = %s", company["id"]
    )
    async with db.pool.connection() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE company SET lifecycle_state = 'archived' WHERE id = %s", (company["id"],)
            )
            await db.append_event(conn, actor="user:philip", event_type="company.archived",
                                  company_id=company["id"], source="api")
    for row in employees:
        if row["hermes_profile"]:
            try:
                await hermes.delete_profile(row["hermes_profile"])
            except HermesError:
                pass  # profile may already be gone; DB stays authoritative


# ---------------------------------------------------------------- objectives and work items


class ObjectiveCreate(BaseModel):
    title: str
    brief: str


@app.post("/companies/{slug}/objectives", status_code=201)
async def create_objective(slug: str, body: ObjectiveCreate) -> dict:
    """Submit an objective; the manager decomposes it into ready work items."""
    company = await db.fetch_one(
        "SELECT * FROM company WHERE slug = %s AND lifecycle_state = 'active'", slug)
    if not company:
        raise HTTPException(404, "no active company with that slug")
    staff = await db.fetch_all(
        "SELECT id, name, role FROM employee WHERE company_id = %s", company["id"])
    by_role: dict[str, list] = {}
    for e in staff:
        by_role.setdefault(e["role"], []).append(e)
    manager = (by_role.get("manager") or [None])[0]
    if manager is None:
        raise HTTPException(422, "company has no manager to decompose the objective")

    plan = await decompose_objective(body.brief, company["name"])

    async with db.pool.connection() as conn:
        async with conn.transaction():
            cur = await conn.execute(
                "INSERT INTO work_item (company_id, type, title, description, status, owner_id) "
                "VALUES (%s, 'objective', %s, %s, 'in_progress', %s) RETURNING id",
                (company["id"], body.title, body.brief, manager["id"]),
            )
            objective_id = (await cur.fetchone())["id"]
            await db.append_event(conn, actor="user:philip", event_type="work_item.created",
                                  company_id=company["id"], work_item_id=objective_id,
                                  source="api", payload={"type": "objective", "title": body.title})

            children = []
            rr_index: dict[str, int] = {}
            for t in plan["tasks"]:
                pool_for_role = by_role.get(t["role"]) or by_role.get("engineer") or staff
                idx = rr_index.get(t["role"], 0)
                owner = pool_for_role[idx % len(pool_for_role)]
                rr_index[t["role"]] = idx + 1
                cur = await conn.execute(
                    "INSERT INTO work_item (company_id, parent_id, type, title, description, "
                    "status, owner_id, acceptance_criteria) "
                    "VALUES (%s, %s, 'task', %s, %s, 'ready', %s, %s) RETURNING id",
                    (company["id"], objective_id, t["title"], t["description"],
                     owner["id"], db.Json(t["acceptance_criteria"])),
                )
                child_id = (await cur.fetchone())["id"]
                await db.append_event(
                    conn, actor=f"employee:{manager['id']}", event_type="work_item.created",
                    company_id=company["id"], work_item_id=child_id,
                    payload={"type": "task", "title": t["title"], "role": t["role"],
                             "owner": owner["name"], "parent": str(objective_id)},
                )
                children.append({"id": str(child_id), "title": t["title"],
                                 "role": t["role"], "owner": owner["name"]})

            if plan.get("clarification_needed"):
                await db.append_event(
                    conn, actor=f"employee:{manager['id']}",
                    event_type="clarification.requested",
                    company_id=company["id"], work_item_id=objective_id,
                    payload={"question": plan["clarification_needed"]},
                )

    return {"objective_id": str(objective_id), "tasks": children,
            "clarification_needed": plan.get("clarification_needed") or None}


@app.get("/companies/{slug}/work-items")
async def list_work_items(slug: str) -> list[dict]:
    company = await db.fetch_one("SELECT id FROM company WHERE slug = %s", slug)
    if not company:
        raise HTTPException(404, "no such company")
    rows = await db.fetch_all(
        "SELECT wi.*, e.name AS owner_name FROM work_item wi "
        "LEFT JOIN employee e ON e.id = wi.owner_id "
        "WHERE wi.company_id = %s ORDER BY wi.created_at", company["id"])
    return [db.as_json(r) for r in rows]


# ---------------------------------------------------------------- global pause (kill switch v1)


@app.post("/pause")
async def pause() -> dict:
    await redis_client.set(PAUSE_KEY, "1")
    async with db.pool.connection() as conn:
        await db.append_event(conn, actor="user:philip", event_type="company.paused",
                              source="api", payload={"scope": "global"})
    return {"paused": True}


@app.post("/resume")
async def resume() -> dict:
    await redis_client.delete(PAUSE_KEY)
    async with db.pool.connection() as conn:
        await db.append_event(conn, actor="user:philip", event_type="company.resumed",
                              source="api", payload={"scope": "global"})
    return {"paused": False}
