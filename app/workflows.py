from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from .agents import build_briefing_markdown, build_outreach_draft
from .live_agents import generate_live_briefing, generate_live_outreach
from .models import AccountRecord, BriefingNote, BriefingRequest, OutreachDraft, OutreachRequest, QueueItem, QueueOutreachRequest
from .send_queue import SendQueue


def _select_account(accounts: Iterable[AccountRecord], account_id: str) -> AccountRecord:
    for account in accounts:
        if account.account_id == account_id:
            return account
    raise ValueError(f"Account not found: {account_id}")


def _fallback_flag(scope: str) -> str:
    return f"Live {scope} generation failed; fell back to deterministic output."


def _append_fallback_flag(model: OutreachDraft | BriefingNote, scope: str) -> OutreachDraft | BriefingNote:
    flags = list(model.guardrail_flags)
    fallback_flag = _fallback_flag(scope)
    if fallback_flag not in flags:
        flags.append(fallback_flag)
    return model.model_copy(update={"guardrail_flags": flags})


def _outreach_from_live_agent(
    account: AccountRecord,
    request: OutreachRequest,
    *,
    api_key: str | None,
    model_name: str,
) -> OutreachDraft:
    if not api_key:
        return build_outreach_draft(account, request.channel, request.tone)
    try:
        return generate_live_outreach(account, request, api_key=api_key, model_name=model_name)
    except Exception:
        return _append_fallback_flag(build_outreach_draft(account, request.channel, request.tone), "outreach")


def _briefing_from_live_agent(
    account: AccountRecord,
    request: BriefingRequest,
    *,
    api_key: str | None,
    model_name: str,
) -> BriefingNote:
    if not api_key:
        return build_briefing_markdown(account, request.meeting_persona, request.focus)
    try:
        return generate_live_briefing(account, request, api_key=api_key, model_name=model_name)
    except Exception:
        return _append_fallback_flag(build_briefing_markdown(account, request.meeting_persona, request.focus), "briefing")


def generate_outreach(
    accounts: Iterable[AccountRecord],
    request: OutreachRequest,
    use_live_agents: bool = False,
    openai_api_key: str | None = None,
    model_name: str = "gpt-4.1-mini",
) -> OutreachDraft:
    account = _select_account(accounts, request.account_id)
    if use_live_agents:
        return _outreach_from_live_agent(account, request, api_key=openai_api_key, model_name=model_name)
    return build_outreach_draft(account, request.channel, request.tone)


def generate_briefing(
    accounts: Iterable[AccountRecord],
    request: BriefingRequest,
    use_live_agents: bool = False,
    openai_api_key: str | None = None,
    model_name: str = "gpt-4.1-mini",
) -> BriefingNote:
    account = _select_account(accounts, request.account_id)
    if use_live_agents:
        return _briefing_from_live_agent(account, request, api_key=openai_api_key, model_name=model_name)
    return build_briefing_markdown(account, request.meeting_persona, request.focus)


def queue_outreach(
    accounts: Iterable[AccountRecord],
    request: QueueOutreachRequest,
    queue: SendQueue,
    use_live_agents: bool = False,
    openai_api_key: str | None = None,
    model_name: str = "gpt-4.1-mini",
) -> QueueItem:
    draft = generate_outreach(
        accounts,
        OutreachRequest(account_id=request.account_id, channel=request.channel, tone=request.tone),
        use_live_agents=use_live_agents,
        openai_api_key=openai_api_key,
        model_name=model_name,
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
