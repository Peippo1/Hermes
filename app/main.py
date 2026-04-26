from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI

from .agents import agent_mode
from .config import get_config
from .data_loader import load_accounts_from_path
from .exporters import export_json, export_markdown_briefings, export_markdown_outreach, export_outreach_csv
from .models import AccountsResponse, BriefingRequest, GenerationResponse, OutreachRequest, QueueOutreachRequest
from .send_queue import SendQueue
from .workflows import generate_briefings, generate_outreach, queue_outreach


config = get_config()
app = FastAPI(title=config.app_name, version="0.1.0")


class RuntimeState:
    def __init__(self) -> None:
        self.accounts = load_accounts_from_path(config.data_path)
        self.queue = SendQueue()


app.state.runtime = RuntimeState()


@app.get("/health")
def health() -> dict[str, object]:
    mode = agent_mode(bool(config.agent_api_key), config.use_live_agents)
    return {
        "status": "ok",
        "app": config.app_name,
        "loaded_accounts": len(app.state.runtime.accounts),
        "queue_items": len(app.state.runtime.queue.items),
        "live_agents_enabled": mode.live,
        "agent_key_present": mode.enabled,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/accounts", response_model=AccountsResponse)
def get_accounts() -> AccountsResponse:
    return AccountsResponse(accounts=app.state.runtime.accounts)


@app.post("/generate/outreach", response_model=GenerationResponse)
def generate_outreach_endpoint(request: OutreachRequest) -> GenerationResponse:
    items = generate_outreach(app.state.runtime.accounts, request, use_live_agents=config.use_live_agents)
    return GenerationResponse(items=items)


@app.post("/generate/briefing", response_model=GenerationResponse)
def generate_briefing_endpoint(request: BriefingRequest) -> GenerationResponse:
    items = generate_briefings(app.state.runtime.accounts, request, use_live_agents=config.use_live_agents)
    return GenerationResponse(items=items)


@app.post("/queue/outreach")
def queue_outreach_endpoint(request: QueueOutreachRequest) -> dict[str, object]:
    items = queue_outreach(app.state.runtime.accounts, request, app.state.runtime.queue, use_live_agents=config.use_live_agents)
    return {"queued": items, "queue_size": len(app.state.runtime.queue.items)}


@app.get("/queue")
def list_queue() -> dict[str, object]:
    return {"items": app.state.runtime.queue.list_items()}


@app.post("/export/examples")
def export_examples() -> dict[str, object]:
    selected_accounts = app.state.runtime.accounts[:5]
    outreach = generate_outreach(
        selected_accounts,
        OutreachRequest(account_ids=[account.account_id for account in selected_accounts]),
        use_live_agents=False,
    )
    briefings = generate_briefings(
        selected_accounts,
        BriefingRequest(account_ids=[account.account_id for account in selected_accounts]),
        use_live_agents=False,
    )
    generated_dir = Path(config.generated_dir)
    csv_path = export_outreach_csv(outreach, generated_dir / "outreach_examples.csv")
    json_path = export_json(
        {"outreach": [item.model_dump() for item in outreach], "briefings": [item.model_dump() for item in briefings]},
        generated_dir / "example_bundle.json",
    )
    outreach_md_path = export_markdown_outreach(outreach, generated_dir / "outreach_examples.md")
    briefing_md_path = export_markdown_briefings(briefings, generated_dir / "briefing_examples.md")
    return {
        "outreach": [item.model_dump() for item in outreach],
        "briefings": [item.model_dump() for item in briefings],
        "artifacts": {
            "csv_path": str(csv_path),
            "json_path": str(json_path),
            "outreach_markdown_path": str(outreach_md_path),
            "briefing_markdown_path": str(briefing_md_path),
            "generated_count": len(outreach) + len(briefings),
        },
    }
