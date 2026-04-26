from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable
from uuid import uuid4

from .agents import _run_live_agent, build_briefing_note, build_outreach_message
from .models import AccountRecord, BriefingNote, BriefingRequest, OutreachMessage, OutreachRequest, QueueItem, QueueOutreachRequest
from .send_queue import SendQueue


def _select_accounts(accounts: Iterable[AccountRecord], account_ids: list[str]) -> list[AccountRecord]:
    account_map = {account.account_id: account for account in accounts}
    if not account_ids:
        return list(account_map.values())
    return [account_map[account_id] for account_id in account_ids if account_id in account_map]


def generate_outreach(
    accounts: Iterable[AccountRecord],
    request: OutreachRequest,
    use_live_agents: bool = False,
) -> list[OutreachMessage]:
    selected = _select_accounts(accounts, request.account_ids)
    results: list[OutreachMessage] = []
    for account in selected:
        live_result = None
        if use_live_agents:
            live_prompt = (
                "Write a personalized outreach draft using only the provided account data. "
                "Do not invent facts. Keep the tone clear, warm, and concise. "
                f"Target account JSON: {account.model_dump()}. "
                f"Request: {request.model_dump()}."
            )
            live_result = _run_live_agent(
                OutreachMessage,
                "You generate structured outreach drafts with strict source fidelity and no real sending.",
                live_prompt,
            )
        if isinstance(live_result, OutreachMessage):
            results.append(live_result)
            continue
        results.append(build_outreach_message(account, request.tone, request.goal, request.channel))
    return results


def generate_briefings(
    accounts: Iterable[AccountRecord],
    request: BriefingRequest,
    use_live_agents: bool = False,
) -> list[BriefingNote]:
    selected = _select_accounts(accounts, request.account_ids)
    results: list[BriefingNote] = []
    for account in selected:
        live_result = None
        if use_live_agents:
            live_prompt = (
                "Write a pre-meeting briefing note using only the provided account data. "
                "Do not invent facts. Keep the note practical and concise. "
                f"Target account JSON: {account.model_dump()}. "
                f"Request: {request.model_dump()}."
            )
            live_result = _run_live_agent(
                BriefingNote,
                "You generate structured briefing notes with strict source fidelity and no unsupported claims.",
                live_prompt,
            )
        if isinstance(live_result, BriefingNote):
            results.append(live_result)
            continue
        results.append(build_briefing_note(account))
    return results


def queue_outreach(
    accounts: Iterable[AccountRecord],
    request: QueueOutreachRequest,
    queue: SendQueue,
    use_live_agents: bool = False,
) -> list[QueueItem]:
    generated = generate_outreach(accounts, request, use_live_agents=use_live_agents)
    queued_items: list[QueueItem] = []
    created_at = datetime.now(timezone.utc)
    for message in generated:
        queued_items.append(
            queue.enqueue(
                QueueItem(
                    queue_id=str(uuid4()),
                    created_at=created_at,
                    schedule_for=request.schedule_for,
                    account_id=message.account_id,
                    account_name=message.account_name,
                    channel=message.channel,
                    subject=message.subject,
                    body=message.body,
                )
            )
        )
    return queued_items
