"""Event schema v1 — the versioned contract between agents, engine, and interfaces.

Two layers:
  * AgentMessage — what an employee (Hermes run) reports back. Small, flat,
    enforced at inference time via Ollama/Hermes structured output
    (qwen3.5:9b scored 100% validity on this shape; see benchmarks/RESULTS.md).
  * EventEnvelope — what the engine appends to the immutable event log after
    policy evaluation. Superset of agent messages: engine/system events too.

Rule from benchmarks: `task.blocked` from an agent is a TRIAGE state. The
engine (manager step) reclassifies to clarification.requested /
approval.requested before anything reaches the user.
"""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

SCHEMA_VERSION = 1

# ---------------------------------------------------------------- agent -> engine

AgentMessageType = Literal[
    "task.accepted",
    "task.progressed",
    "task.blocked",
    "task.completed",
    "clarification.requested",
    "approval.requested",
    "artifact.created",
    "test.started",
    "test.completed",
    "review.completed",
    "consultant.requested",
    "incident.declared",
]


class AgentMessage(BaseModel):
    """Kept flat on purpose — 9B models degrade on nested schemas (PRD_ADDENDUM §2)."""

    message_type: AgentMessageType
    work_item_id: str
    summary: str = Field(max_length=500)
    detail: str = ""
    # clarification/approval: 2-3 options with a recommendation (PRD §7.6)
    options: list[str] = []
    recommended_option: str = ""
    # artifact.created / test.completed
    artifact_uri: str = ""
    tests_passed: int | None = None
    tests_failed: int | None = None


# JSON Schema handed to Hermes/Ollama `format` for enforcement at inference time.
AGENT_MESSAGE_FORMAT: dict = AgentMessage.model_json_schema()

# ---------------------------------------------------------------- engine event log

EngineEventType = Literal[
    # lifecycle
    "company.created", "company.paused", "company.resumed", "company.archived",
    "employee.hired", "employee.updated",
    "work_item.created", "work_item.updated", "work_item.assigned",
    # dispatch loop
    "dispatch.sent", "dispatch.failed", "run.capped",       # run.capped = runaway guard fired
    # decisions
    "clarification.answered", "approval.decided", "policy.denied",
    # accounting
    "cost.recorded",
]

EventType = AgentMessageType | EngineEventType

Source = Literal["engine", "web", "api", "discord", "hermes", "scheduler", "cli"]


class PolicyDecision(BaseModel):
    allowed: bool
    rule_id: UUID | None = None
    level: int
    reason: str = ""


class Provenance(BaseModel):
    model: str = ""
    worker: str = ""
    tool: str = ""
    hermes_run_id: str = ""


class EventEnvelope(BaseModel):
    """Mirrors db/schema.sql `event` table. Append-only; never mutated."""

    event_id: UUID
    company_id: UUID | None = None
    actor: str                       # 'employee:<uuid>' | 'user:philip' | 'system'
    event_type: EventType
    schema_version: int = SCHEMA_VERSION
    work_item_id: UUID | None = None
    parent_event_id: UUID | None = None
    correlation_id: UUID | None = None
    source: Source = "engine"
    payload: dict = {}
    policy_decision: PolicyDecision | None = None
    provenance: Provenance | None = None
    created_at: datetime
