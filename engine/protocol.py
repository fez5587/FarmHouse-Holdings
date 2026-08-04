"""Structured extraction from free-form agent output.

Kanban runs return free text; the protocol requires AgentMessage. Rather than
trusting the worker to format correctly mid-run, the engine converts each raw
report with one schema-enforced pool call (qwen3.5:9b scored 100% validity
under `format` enforcement — benchmarks/RESULTS.md).
"""
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
                    "role": {"type": "string", "enum": ["engineer", "qa", "manager"]},
                    "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "description", "role", "acceptance_criteria"],
            },
        },
        "clarification_needed": {"type": "string"},
    },
    "required": ["tasks"],
}


async def _chat_structured(system: str, user: str, fmt: dict) -> dict:
    async with httpx.AsyncClient(timeout=180) as client:
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
        return json.loads(r.json()["message"]["content"])


async def extract_agent_message(work_item_id: str, raw_report: str) -> AgentMessage:
    data = await _chat_structured(
        EXTRACT_SYSTEM,
        f"Work item ID: {work_item_id}\n\nRaw report:\n{raw_report[:6000]}",
        AGENT_MESSAGE_FORMAT,
    )
    data["work_item_id"] = work_item_id  # never trust the model with the ID
    return AgentMessage.model_validate(data)


async def decompose_objective(brief: str, company_name: str) -> dict:
    """Manager-style decomposition into 2-5 small tasks. Returns validated dict."""
    system = (
        f"You are the engineering manager at {company_name}. Decompose the "
        "objective into 2-5 small, independently completable tasks, each with "
        "concrete acceptance criteria. Assign each to the right role. If the "
        "objective is materially ambiguous, fill clarification_needed with the "
        "question and give your best-guess decomposition anyway."
    )
    return await _chat_structured(system, brief, DECOMPOSE_FORMAT)
