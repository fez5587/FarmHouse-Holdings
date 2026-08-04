"""Adapter for Hermes Agent 0.19.0 (ADR-001).

The ONLY module allowed to talk to Hermes. Engine business logic imports this,
never httpx-to-Hermes directly, so a Hermes upgrade is contained here.

Two Hermes surfaces:
  * Dashboard API (:30433) — cookie session auth (login endpoint), profiles,
    kanban orchestration, runs. This is the integration surface.
  * api_server (:30432) — OpenAI-compatible bearer-auth chat; one completion =
    one full agent run. Used later for one-shot manager reasoning if needed.

Event flow back to the engine is POLLING (kanban task status + runs): Hermes
webhooks are inbound triggers, not outbound delivery.
"""
from typing import Any

import httpx

from engine.config import settings


class HermesError(RuntimeError):
    pass


class HermesClient:
    """Async client with lazy cookie login and one retry on session expiry."""

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(base_url=settings.hermes_dashboard_url, timeout=30)
        self._logged_in = False

    async def aclose(self) -> None:
        await self._http.aclose()

    # ------------------------------------------------------------ auth

    async def _login(self) -> None:
        r = await self._http.post(
            "/auth/password-login",
            json={
                "provider": "basic",
                "username": settings.hermes_username,
                "password": settings.hermes_password,
            },
        )
        if r.status_code != 200 or not r.json().get("ok"):
            raise HermesError(f"Hermes login failed: {r.status_code} {r.text[:200]}")
        self._logged_in = True

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        if not self._logged_in:
            await self._login()
        r = await self._http.request(method, path, **kwargs)
        if r.status_code == 401:  # session expired mid-flight
            await self._login()
            r = await self._http.request(method, path, **kwargs)
        if r.status_code >= 400:
            raise HermesError(f"{method} {path} -> {r.status_code}: {r.text[:300]}")
        return r

    async def _json(self, method: str, path: str, **kwargs) -> Any:
        r = await self._request(method, path, **kwargs)
        return r.json() if r.content else None

    # ------------------------------------------------------------ health

    async def status(self) -> dict:
        return await self._json("GET", "/api/status")

    # ------------------------------------------------------------ profiles (= employees)

    async def list_profiles(self) -> list[dict]:
        data = await self._json("GET", "/api/profiles")
        return data if isinstance(data, list) else data.get("profiles", [])

    async def create_profile(self, name: str, *, soul: str, model: str,
                             description: str = "") -> None:
        """Create employee persona: profile + soul (system prompt) + model binding.

        no_skills: lean prompt — 73 bundled skills drown a 9B model's tool
        discipline; employees get capabilities via explicit toolsets instead.
        """
        await self._json("POST", "/api/profiles", json={
            "name": name,
            "no_skills": True,
            "description": description,
        })
        await self._json("PUT", f"/api/profiles/{name}/soul", json={"content": soul})
        # no-clone profiles have a bare config with no custom endpoint defined;
        # declare the pool endpoint directly, same shape as the default profile
        await self._json("PUT", "/api/config", json={
            "profile": name,
            "config": {"model": {
                "default": model,
                "provider": "custom",
                "base_url": f"{settings.ollama_pool_url}/v1",
            }},
        })

    async def get_soul(self, name: str) -> str:
        data = await self._json("GET", f"/api/profiles/{name}/soul")
        return data.get("content", "") if isinstance(data, dict) else str(data)

    async def delete_profile(self, name: str) -> None:
        await self._json("DELETE", f"/api/profiles/{name}")

    # ------------------------------------------------------------ files

    async def mkdir(self, path: str) -> None:
        await self._json("POST", "/api/files/mkdir", json={"path": path})

    # ------------------------------------------------------------ kanban (= work dispatch)

    async def create_task(self, title: str, *, body: str, assignee: str, tenant: str,
                          idempotency_key: str, max_runtime_seconds: int = 1800,
                          goal_max_turns: int = 15, priority: int = 3,
                          workspace_path: str | None = None) -> dict:
        """One engine work-item dispatch = one kanban task.

        tenant = FarmHouse company slug (board isolation).
        goal_max_turns / max_runtime_seconds carry the work item's runaway budget.
        idempotency_key = engine work_item UUID — safe re-dispatch after crashes.
        """
        payload = {
            "title": title,
            "body": body,
            "assignee": assignee,
            "tenant": tenant,
            "priority": priority,
            "idempotency_key": idempotency_key,
            "max_runtime_seconds": max_runtime_seconds,
            "goal_max_turns": goal_max_turns,
            "triage": False,
        }
        if workspace_path:
            payload["workspace_kind"] = "dir"
            payload["workspace_path"] = workspace_path
        data = await self._json("POST", "/api/plugins/kanban/tasks", json=payload)
        return data.get("task", data)

    async def get_task(self, task_id: str) -> dict:
        data = await self._json("GET", f"/api/plugins/kanban/tasks/{task_id}")
        return data.get("task", data)

    async def update_task(self, task_id: str, **fields) -> dict:
        data = await self._json("PATCH", f"/api/plugins/kanban/tasks/{task_id}", json=fields)
        return data.get("task", data)

    async def delete_task(self, task_id: str) -> None:
        await self._json("DELETE", f"/api/plugins/kanban/tasks/{task_id}")

    async def board(self, tenant: str | None = None) -> dict:
        params = {"tenant": tenant} if tenant else {}
        return await self._json("GET", "/api/plugins/kanban/board", params=params)

    async def dispatch_now(self) -> dict | None:
        """Force a dispatch tick instead of waiting for Hermes' 60s interval."""
        return await self._json("POST", "/api/plugins/kanban/dispatch")

    async def get_run(self, run_id: str) -> dict:
        return await self._json("GET", f"/api/plugins/kanban/runs/{run_id}")

    async def active_workers(self) -> list[dict]:
        data = await self._json("GET", "/api/plugins/kanban/workers/active")
        return data if isinstance(data, list) else data.get("workers", [])

    async def terminate_run(self, run_id: str) -> None:
        await self._json("POST", f"/api/plugins/kanban/runs/{run_id}/terminate")
