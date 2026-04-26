from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from .agents import build_briefing_markdown, build_outreach_draft
from .models import AccountRecord, BriefingNote, BriefingRequest, OutreachDraft, OutreachRequest, QueueItem, QueueOutreachRequest
from .send_queue import SendQueue


def _select_account(accounts: Iterable[AccountRecord], account_id: str) -> AccountRecord:
    for account in accounts:
        if account.account_id == account_id:
            return account
    raise ValueError(f"Account not found: {account_id}")


def _outreach_from_live_agent(account: AccountRecord, request: OutreachRequest) -> OutreachDraft:
    # Placeholder integration point for a future live-agent implementation.
    # The fallback remains deterministic so the demo stays self-contained.
    return build_outreach_draft(account, request.channel, request.tone)


def _briefing_from_live_agent(account: AccountRecord) -> BriefingNote | None:
    live_prompt = (
        "Write a markdown briefing note using only the provided account data. "
        "Do not invent facts. Keep the note practical and readable. "
        f"Account JSON: {account.model_dump()}."
    )
    return _run_live_agent(
        BriefingNote,
        "You generate concise markdown briefing notes with strict source fidelity and no unsupported claims.",
        live_prompt,
    )


def generate_outreach(
    accounts: Iterable[AccountRecord],
    request: OutreachRequest,
    use_live_agents: bool = False,
) -> OutreachDraft:
    account = _select_account(accounts, request.account_id)
    if use_live_agents:
        return _outreach_from_live_agent(account, request)
    return build_outreach_draft(account, request.channel, request.tone)


def generate_briefing(
    accounts: Iterable[AccountRecord],
    request: BriefingRequest,
    use_live_agents: bool = False,
) -> BriefingNote:
    account = _select_account(accounts, request.account_id)
    if use_live_agents:
        live_result = _briefing_from_live_agent(account)
        if isinstance(live_result, BriefingNote):
            return live_result
    return build_briefing_markdown(account)


def queue_outreach(
    accounts: Iterable[AccountRecord],
    request: QueueOutreachRequest,
    queue: SendQueue,
    use_live_agents: bool = False,
) -> QueueItem:
    draft = generate_outreach(
        accounts,
        OutreachRequest(account_id=request.account_id, channel=request.channel, tone=request.tone),
        use_live_agents=use_live_agents,
    )
    created_at = datetime.now(timezone.utc)
    item = QueueItem(
        account={
            "account_id": draft.account_id,
            "company_name": draft.company_name,
        },
        persona=draft.contact_role or "commercial lead",
        channel=draft.channel,
        message=draft.message,
        created_at=created_at,
        follow_up_day_3=(created_at + timedelta(days=3)).isoformat(),
        follow_up_day_7=(created_at + timedelta(days=7)).isoformat(),
    )
    return queue.enqueue(item)
