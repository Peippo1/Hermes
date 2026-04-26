from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AccountRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    account_id: str = Field(description="Unique account identifier")
    company_name: str = Field(description="Normalised company name")
    category: str | None = None
    sub_category: str | None = None
    description: str | None = None
    hq_location: str | None = None
    number_of_sites: int | None = None
    estimated_annual_visits: int | None = None
    estimated_average_ticket_price: float | None = None
    estimated_transaction_volume: int | None = None
    estimated_annual_revenue: float | None = None
    region: str | None = None
    contact_name: str | None = None
    contact_role: str | None = None
    website: str | None = None
    signal: str | None = None
    objective: str | None = None
    notes: str | None = None
    source: str | None = None


class OutreachRequest(BaseModel):
    account_id: str
    channel: Literal["email", "linkedin"] = "email"
    tone: str = "clear, warm, concise"
    goal: str = "book a discovery conversation"


class BriefingRequest(BaseModel):
    account_id: str


class QueueOutreachRequest(BaseModel):
    account_id: str
    channel: Literal["email", "linkedin"] = "email"
    tone: str = "clear, warm, concise"
    goal: str = "book a discovery conversation"


class OutreachDraft(BaseModel):
    account_id: str
    company_name: str
    persona: str
    role_reasoning: str
    selected_value_props: list[str] = Field(default_factory=list)
    business_insight: str
    estimated_impact: str
    message: str
    risk_flags: list[str] = Field(default_factory=list)
    channel: str = "email"
    tone: str = "clear, warm, concise"


class BriefingNote(BaseModel):
    account_id: str
    company_name: str
    markdown: str
    source_data: dict[str, Any] = Field(default_factory=dict)


class QueueItem(BaseModel):
    account: dict[str, Any]
    persona: str
    channel: str
    message: str
    status: str = "pending_review"
    created_at: datetime
    follow_up_day_3: str
    follow_up_day_7: str


class AccountsResponse(BaseModel):
    accounts: list[AccountRecord]


class QueueResponse(BaseModel):
    items: list[QueueItem]


class ExportArtifacts(BaseModel):
    outreach_csv_path: str
    outreach_json_path: str
    briefing_note_1_path: str
    briefing_note_2_path: str
    send_queue_path: str

