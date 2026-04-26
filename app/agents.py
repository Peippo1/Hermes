from __future__ import annotations

import asyncio
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .models import AccountRecord, BriefingNote, OutreachMessage, PersonalizationPoint


@dataclass(frozen=True)
class AgentMode:
    live: bool = False
    enabled: bool = False


def agent_mode(api_key_present: bool, use_live_agents: bool) -> AgentMode:
    return AgentMode(live=api_key_present and use_live_agents, enabled=api_key_present)


def _seed(account: AccountRecord, purpose: str) -> int:
    digest = sha256(f"{account.account_id}:{purpose}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _pick(sequence: list[str], seed: int) -> str:
    return sequence[seed % len(sequence)]


def build_outreach_message(account: AccountRecord, tone: str, goal: str, channel: str) -> OutreachMessage:
    seed = _seed(account, "outreach")
    opener_templates = [
        "I noticed that the record mentions {detail}, and that looks relevant to {goal}.",
        "The source data suggests {detail}, which makes a short conversation about {goal} worth considering.",
        "Based on the available account data, {detail} stands out as a useful signal for {goal}.",
    ]
    subject_templates = [
        "Idea for {account_name}",
        "A practical note for {account_name}",
        "Thoughts on {account_name} growth",
        "A quick idea for {city}",
    ]
    ctas = [
        "Would it be useful to compare notes on this next week?",
        "Open to a short conversation about the idea?",
        "If this is relevant, I can share a tighter version tailored to your team.",
    ]
    detail = account.signal or account.objective or account.venue_type or "your current priorities"
    city = account.city or "your market"
    subject = _pick(subject_templates, seed).format(account_name=account.account_name, city=city)
    opener = _pick(opener_templates, seed).format(detail=detail, goal=goal)
    cta = _pick(ctas, seed)
    body = (
        f"Hi {account.contact_name or 'there'},\n\n"
        f"{opener} "
        f"For an account like {account.account_name}, I would keep the note focused on {goal} and anchor it in the source data we actually have. "
        f"That keeps the draft useful without stretching beyond the record.\n\n"
        f"{cta}\n\n"
        f"Best,\nHermes"
    )
    personalization_points = [
        PersonalizationPoint(label="Signal", detail=account.signal or "No direct signal provided in the source file."),
        PersonalizationPoint(label="Objective", detail=account.objective or "No objective captured in the source file."),
        PersonalizationPoint(label="Location", detail=", ".join([part for part in [account.city, account.region] if part]) or "Location not provided."),
    ]
    guardrails = [
        "Do not invent revenue figures, partners, or campaign results.",
        "Keep the tone practical, concise, and respectful.",
        "Flag missing source fields instead of guessing.",
        "This workflow only prepares a draft for a mock queue; it never sends a real message.",
    ]
    return OutreachMessage(
        account_id=account.account_id,
        account_name=account.account_name,
        channel=channel,
        tone=tone,
        subject=subject,
        preview=body[:220].replace("\n", " "),
        body=body,
        call_to_action=cta,
        personalization_points=personalization_points,
        guardrails=guardrails,
        source_data=account.model_dump(),
    )


def build_briefing_note(account: AccountRecord) -> BriefingNote:
    summary = (
        f"{account.account_name} is a {account.segment or 'unspecified'} account in "
        f"{account.city or 'an unspecified market'} with a near-term commercial opportunity."
    )
    opportunities = [
        f"Use {account.signal or 'the current account signal'} as the opening context.",
        f"Position the conversation around {account.objective or 'a measurable commercial outcome'}.",
        "Keep the first meeting focused on practical next steps and decision criteria.",
    ]
    risks = [
        "Do not overstate familiarity with the account.",
        "Avoid claims about site performance, audience size, or pipeline unless present in the file.",
        "Keep the briefing grounded in observed source fields only.",
    ]
    questions = [
        "What is the current commercial priority for the next 90 days?",
        "Which audience or visit segment matters most right now?",
        "What would make a follow-up conversation worthwhile?",
    ]
    guardrails = [
        "Use tentative language when source data is thin.",
        "Call out gaps explicitly rather than filling them in.",
        "No real outreach execution is performed from this note.",
    ]
    snapshot = [
        f"Segment: {account.segment or 'not supplied'}",
        f"Venue type: {account.venue_type or 'not supplied'}",
        f"Location: {', '.join([part for part in [account.city, account.region, account.country] if part]) or 'not supplied'}",
        f"Signal: {account.signal or 'not supplied'}",
        f"Objective: {account.objective or 'not supplied'}",
    ]
    return BriefingNote(
        account_id=account.account_id,
        account_name=account.account_name,
        summary=summary,
        account_snapshot=snapshot,
        opportunities=opportunities,
        risks=risks,
        questions=questions,
        suggested_next_step="Prepare a short conversation plan that reflects the account's stated goal and avoids unsupported claims.",
        guardrails=guardrails,
        source_data=account.model_dump(),
    )


def try_live_generation(*_: Any, **__: Any) -> Any:
    return None


def _run_live_agent(output_type: type[Any], instructions: str, input_text: str) -> Any | None:
    try:
        from agents import Agent, Runner  # type: ignore
    except Exception:
        return None

    async def _runner() -> Any:
        agent = Agent(
            name="Hermes drafting agent",
            instructions=instructions,
            output_type=output_type,
        )
        result = await Runner.run(agent, input_text)
        return result.final_output

    try:
        return asyncio.run(_runner())
    except RuntimeError:
        return None
