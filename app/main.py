from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .agents import agent_mode
from .config import get_config
from .data_loader import AccountDataError, load_accounts_with_metadata
from .exporters import (
    export_briefing_markdown,
    export_outreach_csv,
    export_outreach_json,
    export_queue_json,
    export_report_json,
    export_report_markdown,
)
from .models import AccountRecord, AccountsResponse, BriefingNote, BriefingRequest, DataSourceInfo, OutreachDraft, OutreachRequest, QueueOutreachRequest, QueueResponse
from .send_queue import SendQueue
from .workflows import generate_briefing, generate_outreach, queue_outreach


config = get_config()
LOGGER = logging.getLogger(__name__)
app = FastAPI(title=config.app_name, version="0.2.0")

default_cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
configured_cors_origins = [
    origin.strip()
    for origin in config.cors_origins.split(",")
    if origin.strip()
]
allowed_cors_origins = list(dict.fromkeys(default_cors_origins + configured_cors_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RuntimeState:
    def __init__(self) -> None:
        load_result = self._load_accounts()
        self.accounts = load_result.accounts
        self.data_source = load_result.data_source
        self.data_source_detail = load_result.data_source_detail
        self.data_load_warning = load_result.data_load_warning
        self.queue = SendQueue()

    def get_account(self, account_id: str) -> AccountRecord | None:
        for account in self.accounts:
            if account.account_id == account_id:
                return account
        return None

    def _load_accounts(self):
        return load_accounts_with_metadata(
            data_path=config.data_path,
            google_sheet_csv_url=config.google_sheet_csv_url,
        )


try:
    app.state.runtime = RuntimeState()
except (AccountDataError, RuntimeError) as exc:
    raise RuntimeError(f"Unable to load account data: {exc}") from exc


@app.get("/health")
def health() -> dict[str, object]:
    mode = agent_mode(bool(config.openai_api_key), config.use_live_agents)
    return {
        "status": "ok",
        "app": config.app_name,
        "loaded_accounts": len(app.state.runtime.accounts),
        "data_source": app.state.runtime.data_source,
        "data_source_detail": app.state.runtime.data_source_detail,
        "data_load_warning": app.state.runtime.data_load_warning,
        "queue_items": len(app.state.runtime.queue.items),
        "live_agents_enabled": mode.live,
        "agent_key_present": mode.enabled,
    }


@app.get("/data-source", response_model=DataSourceInfo)
def data_source() -> DataSourceInfo:
    return DataSourceInfo(
        data_source=app.state.runtime.data_source,
        data_source_detail=app.state.runtime.data_source_detail,
        data_load_warning=app.state.runtime.data_load_warning,
        loaded_accounts=len(app.state.runtime.accounts),
    )


@app.get("/accounts", response_model=AccountsResponse)
def get_accounts() -> AccountsResponse:
    return AccountsResponse(accounts=app.state.runtime.accounts)


@app.get("/accounts/{account_id}", response_model=AccountRecord)
def get_account(account_id: str) -> AccountRecord:
    account = app.state.runtime.get_account(account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Account '{account_id}' was not found.")
    return account


@app.post("/generate/outreach", response_model=OutreachDraft)
def generate_outreach_endpoint(request: OutreachRequest) -> OutreachDraft:
    try:
        return generate_outreach(
            app.state.runtime.accounts,
            request,
            use_live_agents=config.use_live_agents,
            openai_api_key=config.openai_api_key,
            model_name=config.model_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.post("/generate/briefing", response_model=BriefingNote)
def generate_briefing_endpoint(request: BriefingRequest) -> BriefingNote:
    try:
        return generate_briefing(
            app.state.runtime.accounts,
            request,
            use_live_agents=config.use_live_agents,
            openai_api_key=config.openai_api_key,
            model_name=config.model_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.post("/queue/outreach")
def queue_outreach_endpoint(request: QueueOutreachRequest) -> dict[str, object]:
    try:
        queued = queue_outreach(
            app.state.runtime.accounts,
            request,
            app.state.runtime.queue,
            use_live_agents=config.use_live_agents,
            openai_api_key=config.openai_api_key,
            model_name=config.model_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"item": queued.model_dump(mode="json"), "queue_size": len(app.state.runtime.queue.items)}


@app.get("/queue", response_model=QueueResponse)
def list_queue() -> QueueResponse:
    items = app.state.runtime.queue.list_items()
    return QueueResponse(items=items, queue_size=len(items))


@app.post("/export/examples")
def export_examples() -> dict[str, object]:
    selected_accounts = app.state.runtime.accounts[:3]
    outreach_items = [
        generate_outreach(
            app.state.runtime.accounts,
            OutreachRequest(account_id=account.account_id),
            use_live_agents=False,
        )
        for account in selected_accounts
    ]
    briefing_items = [
        generate_briefing(
            app.state.runtime.accounts,
            BriefingRequest(account_id=account.account_id),
            use_live_agents=False,
        )
        for account in selected_accounts
    ][:2]
    generated_dir = Path(config.generated_dir)
    outreach_csv_path = export_outreach_csv(outreach_items, generated_dir / "outreach_examples.csv")
    outreach_json_path = export_outreach_json(outreach_items, generated_dir / "outreach_examples.json")
    briefing_note_1_path = export_briefing_markdown(briefing_items[0], generated_dir / "briefing_note_1.md")
    briefing_note_2_path = export_briefing_markdown(briefing_items[1], generated_dir / "briefing_note_2.md")
    sample_queue = SendQueue()
    send_queue_items = [
        queue_outreach(
            app.state.runtime.accounts,
            QueueOutreachRequest(account_id=account.account_id),
            sample_queue,
            use_live_agents=False,
        )
        for account in selected_accounts
    ]
    send_queue_path = export_queue_json(send_queue_items, generated_dir / "send_queue.json")
    return {
        "outreach": [item.model_dump() for item in outreach_items],
        "briefings": [item.model_dump() for item in briefing_items],
        "artifacts": {
            "outreach_csv_path": str(outreach_csv_path),
            "outreach_json_path": str(outreach_json_path),
            "briefing_note_1_path": str(briefing_note_1_path),
            "briefing_note_2_path": str(briefing_note_2_path),
            "send_queue_path": str(send_queue_path),
        },
    }


@app.post("/export/report")
def export_report() -> dict[str, object]:
    selected_accounts = app.state.runtime.accounts[:3]
    outreach_items = [
        generate_outreach(
            app.state.runtime.accounts,
            OutreachRequest(account_id=account.account_id),
            use_live_agents=False,
        )
        for account in selected_accounts
    ]
    queued_items = app.state.runtime.queue.list_items()
    guardrail_flags = [
        *[flag for item in outreach_items for flag in item.guardrail_flags],
        *[flag for item in queued_items for flag in item.guardrail_flags],
    ]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary_counts": {
            "outreach_examples": len(outreach_items),
            "queued_outreach_items": len(queued_items),
            "guardrail_flags": len(guardrail_flags),
        },
        "generated_outreach_examples": [item.model_dump() for item in outreach_items],
        "queued_outreach_items": [item.model_dump(mode="json") for item in queued_items],
        "guardrail_flags": guardrail_flags,
    }
    generated_dir = Path(config.generated_dir)
    report_md_path = export_report_markdown(report, generated_dir / "outreach_report.md")
    report_json_path = export_report_json(report, generated_dir / "outreach_report.json")
    return {
        "report": report,
        "artifacts": {
            "report_md_path": str(report_md_path),
            "report_json_path": str(report_json_path),
        },
    }
