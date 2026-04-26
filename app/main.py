from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .agents import agent_mode
from .config import get_config
from .data_loader import AccountDataError, load_accounts_from_path
from .exporters import export_briefing_markdown, export_outreach_csv, export_outreach_json, export_queue_json
from .models import AccountRecord, AccountsResponse, BriefingNote, BriefingRequest, OutreachDraft, OutreachRequest, QueueOutreachRequest, QueueResponse
from .send_queue import SendQueue
from .workflows import generate_briefing, generate_outreach, queue_outreach


config = get_config()
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
        self.accounts = load_accounts_from_path(self._resolve_data_path())
        self.queue = SendQueue()

    def get_account(self, account_id: str) -> AccountRecord | None:
        for account in self.accounts:
            if account.account_id == account_id:
                return account
        return None

    def _resolve_data_path(self) -> Path:
        base_dir = Path(__file__).resolve().parent.parent
        sample_path = base_dir / "data" / "sample_accounts.csv"
        fallback_candidates = [sample_path, base_dir / "outputs" / "sample_accounts.csv"]
        candidates = [config.data_path] if config.data_path is not None else []
        candidates.extend(fallback_candidates)
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        candidate_text = ", ".join(str(candidate) for candidate in candidates if candidate is not None)
        raise RuntimeError(f"No valid account data file found. Checked: {candidate_text}")


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
        "queue_items": len(app.state.runtime.queue.items),
        "live_agents_enabled": mode.live,
        "agent_key_present": mode.enabled,
    }


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
