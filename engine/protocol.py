"""Structured extraction from free-form agent output.

Kanban runs return free text; the protocol requires AgentMessage. Rather than
trusting the worker to format correctly mid-run, the engine converts each raw
report with one schema-enforced pool call (qwen3.5:9b scored 100% validity
under `format` enforcement — benchmarks/RESULTS.md).
"""
import asyncio
import json
from typing import Any

import httpx

from engine.config import settings
from engine.schemas.events import AGENT_MESSAGE_FORMAT, AgentMessage

MODEL = "qwen3.5:9b"

EXTRACT_SYSTEM = (
    "You convert an AI employee's raw work report into exactly one structured "
    "protocol message. Choose the message_type that matches what actually "
    "happened:\n"
    "- task.completed: work finished, evidence given\n"
    "- task.progressed: partial progress, more to do\n"
    "- task.blocked: cannot continue for technical reasons\n"
    "- clarification.requested: needs a decision/answer from a human; include "
    "the options given\n"
    "- approval.requested: needs authority the employee lacks\n"
    "- incident.declared: something broke that affects others\n"
    "A QA/review/audit task that finished its checks is task.completed even "
    "when it found defects in the thing under test — findings are its "
    "deliverable, not a blocker.\n"
    "Copy concrete facts (files, commits, test counts) into summary/detail. "
    "Do not invent facts not present in the report."
)

DECOMPOSE_FORMAT: dict[str, Any] = {
    "type": "object",
    "properties": {
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "role": {"type": "string", "enum": ["engineer", "qa", "manager", "consultant"]},
                    "kind": {"type": "string", "enum": ["build", "research", "review"]},
                    "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "description", "role", "kind", "acceptance_criteria"],
            },
        },
        "clarification_needed": {"type": "string"},
    },
    "required": ["tasks"],
}


async def _chat_structured(system: str, user: str, fmt: dict) -> dict:
    async with httpx.AsyncClient(timeout=180) as client:
        for attempt in (1, 2, 3):  # pool returns empty content under load; retry with backoff
            r = await client.post(
                f"{settings.ollama_pool_url}/api/chat",
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "stream": False,
                    "think": False,
                    "format": fmt,
                },
            )
            r.raise_for_status()
            try:
                return json.loads(r.json()["message"]["content"])
            except json.JSONDecodeError:
                if attempt == 3:
                    raise
                await asyncio.sleep(3 * attempt)
        raise RuntimeError("unreachable")


async def extract_agent_message(work_item_id: str, raw_report: str) -> AgentMessage:
    data = await _chat_structured(
        EXTRACT_SYSTEM,
        f"Work item ID: {work_item_id}\n\nRaw report:\n{raw_report[:6000]}",
        AGENT_MESSAGE_FORMAT,
    )
    data["work_item_id"] = work_item_id  # never trust the model with the ID
    return AgentMessage.model_validate(data)


CEO_UPDATE_FORMAT: dict[str, Any] = {
    "type": "object",
    "properties": {"update": {"type": "string"}},
    "required": ["update"],
}


async def ceo_update(company_name: str, objective_title: str, task_lines: list[str]) -> str:
    """CEO-voiced 2-4 sentence shareholder update for a completed objective."""
    system = (
        f"You are the CEO of {company_name} writing a short shareholder update "
        "(2-4 sentences). Report the milestone plainly: what shipped and what "
        "comes next. No hype. Do not invent facts not in the task list."
    )
    user = (f"Milestone reached: {objective_title}\nCompleted tasks:\n"
            + "\n".join(f"- {t}" for t in task_lines))
    data = await _chat_structured(system, user, CEO_UPDATE_FORMAT)
    return data["update"]


async def manager_status(company_name: str, event_lines: list[str]) -> str:
    """Manager-voiced interim status update for the shareholder feed."""
    system = (
        f"You are the engineering manager at {company_name} writing a brief "
        "status update to the company's shareholder (2-4 sentences). From the "
        "recent activity log: what is moving, any risk or blocker worth "
        "flagging, and the immediate next step or strategy. Plain, concrete, "
        "no hype, no invented facts.")
    data = await _chat_structured(
        system, "Recent activity:\n" + "\n".join(f"- {ln}" for ln in event_lines),
        CEO_UPDATE_FORMAT)
    return data["update"]


async def decompose_objective(brief: str, company_name: str) -> dict:
    """Manager-style decomposition into 2-5 small tasks. Returns validated dict."""
    system = (
        f"You are the engineering manager at {company_name}. Decompose the "
        "objective into 2-5 small, independently completable tasks, each with "
        "concrete acceptance criteria. Assign each to the right role; assign "
        "consultant ONLY when a task truly needs frontier-model expertise the "
        "core team lacks (deep architecture, hard debugging) — consultants "
        "cost real money per task. Set kind: "
        "build (create/modify artifacts), research (investigate/gather "
        "information), review (verify/QA existing work). If the objective is "
        "materially ambiguous, fill clarification_needed with the question and "
        "give your best-guess decomposition anyway."
    )
    return await _chat_structured(system, brief, DECOMPOSE_FORMAT)
