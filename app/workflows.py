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


def _briefing_from_live_agent(account: AccountRecord, request: BriefingRequest) -> BriefingNote:
    # Placeholder integration point for a future live-agent implementation.
    # The fallback remains deterministic so the demo stays self-contained.
    return build_briefing_markdown(account, request.meeting_persona, request.focus)


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
        return _briefing_from_live_agent(account, request)
    return build_briefing_markdown(account, request.meeting_persona, request.focus)


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
        queue_id="",
        account_id=draft.account_id,
        company_name=draft.company_name,
        contact_name=draft.contact_name,
        contact_role=draft.contact_role,
        channel=draft.channel,
        message=draft.message,
        selected_value_props=draft.selected_value_props,
        created_at=created_at,
        follow_up_day_3=(created_at + timedelta(days=3)).isoformat(),
        follow_up_day_7=(created_at + timedelta(days=7)).isoformat(),
        guardrail_flags=draft.guardrail_flags,
    )
    return queue.enqueue(item)
