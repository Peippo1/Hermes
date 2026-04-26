from __future__ import annotations

from datetime import datetime
from typing import Literal

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
    tone: Literal["concise", "warm", "direct"] = "concise"


class BriefingRequest(BaseModel):
    account_id: str
    meeting_persona: str | None = None
    focus: Literal["commercial", "operations", "growth", "customer_support"] = "commercial"


class QueueOutreachRequest(BaseModel):
    account_id: str
    channel: Literal["email", "linkedin"] = "email"
    tone: Literal["concise", "warm", "direct"] = "concise"


class OutreachDraft(BaseModel):
    account_id: str
    company_name: str
    contact_name: str | None = None
    contact_role: str | None = None
    selected_value_props: list[str] = Field(default_factory=list)
    business_insight: str
    estimated_impact: str
    message: str
    guardrail_flags: list[str] = Field(default_factory=list)
    channel: Literal["email", "linkedin"] = "email"
    tone: Literal["concise", "warm", "direct"] = "concise"


class BriefingNote(BaseModel):
    account_id: str
    company_name: str
    contact_name: str | None = None
    contact_role: str | None = None
    briefing_markdown: str
    opportunity_summary: str
    quantified_value_case: str
    talking_points: list[str] = Field(default_factory=list)
    likely_objections: list[str] = Field(default_factory=list)
    recommended_next_step: str
    guardrail_flags: list[str] = Field(default_factory=list)


class QueueItem(BaseModel):
    queue_id: str
    account_id: str
    company_name: str
    contact_name: str | None = None
    contact_role: str | None = None
    channel: str
    message: str
    selected_value_props: list[str] = Field(default_factory=list)
    status: str = "pending_review"
    created_at: datetime
    follow_up_day_3: str
    follow_up_day_7: str
    guardrail_flags: list[str] = Field(default_factory=list)


class AccountsResponse(BaseModel):
    accounts: list[AccountRecord]


class QueueResponse(BaseModel):
    items: list[QueueItem]
    queue_size: int


class DataSourceInfo(BaseModel):
    data_source: Literal["google_sheet", "local_file", "sample_fallback"]
    data_source_detail: str
    data_load_warning: str | None = None
    loaded_accounts: int


class ExportArtifacts(BaseModel):
    outreach_csv_path: str
    outreach_json_path: str
    briefing_note_1_path: str
    briefing_note_2_path: str
    send_queue_path: str
