from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AccountRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    account_id: str = Field(description="Unique account identifier")
    account_name: str = Field(description="Display name for the account")
    segment: str | None = None
    venue_type: str | None = None
    city: str | None = None
    region: str | None = None
    country: str | None = None
    website: str | None = None
    contact_name: str | None = None
    contact_role: str | None = None
    signal: str | None = None
    objective: str | None = None
    notes: str | None = None
    source: str | None = None


class OutreachRequest(BaseModel):
    account_ids: list[str] = Field(default_factory=list)
    tone: str = "clear, warm, concise"
    goal: str = "book a discovery conversation"
    channel: Literal["email", "linkedin"] = "email"
    include_subject: bool = True


class BriefingRequest(BaseModel):
    account_ids: list[str] = Field(default_factory=list)
    focus: str = "pre-meeting briefing"


class QueueOutreachRequest(OutreachRequest):
    schedule_for: datetime | None = None


class PersonalizationPoint(BaseModel):
    label: str
    detail: str


class OutreachMessage(BaseModel):
    account_id: str
    account_name: str
    channel: str = "email"
    tone: str
    subject: str
    preview: str
    body: str
    call_to_action: str
    personalization_points: list[PersonalizationPoint] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)
    source_data: dict[str, Any] = Field(default_factory=dict)


class BriefingNote(BaseModel):
    account_id: str
    account_name: str
    summary: str
    account_snapshot: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    suggested_next_step: str
    guardrails: list[str] = Field(default_factory=list)
    source_data: dict[str, Any] = Field(default_factory=dict)


class QueueItem(BaseModel):
    queue_id: str
    created_at: datetime
    schedule_for: datetime | None = None
    account_id: str
    account_name: str
    channel: str = "email"
    subject: str
    body: str
    status: str = "queued"
    source: str = "mock_send_queue"


class ExportArtifacts(BaseModel):
    csv_path: str
    json_path: str
    markdown_path: str
    generated_count: int


class AccountsResponse(BaseModel):
    accounts: list[AccountRecord]


class GenerationResponse(BaseModel):
    items: list[OutreachMessage | BriefingNote]
