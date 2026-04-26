from __future__ import annotations

import asyncio
from dataclasses import dataclass
from hashlib import sha256
import re
from typing import Any

from .models import AccountRecord, BriefingNote, OutreachDraft


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


def _persona_for_queue(account: AccountRecord) -> str:
    if account.contact_role:
        return account.contact_role
    if account.category:
        return f"{account.category} lead"
    return "commercial lead"


def _value_props(account: AccountRecord) -> list[str]:
    props: list[str] = []
    if account.number_of_sites:
        site_label = "site" if account.number_of_sites == 1 else "sites"
        props.append(f"Support commercial consistency across {account.number_of_sites} {site_label}")
    if account.objective:
        props.append(f"Align the first conversation to the stated objective: {account.objective}")
    if account.signal:
        props.append(f"Use the current signal as a practical opening: {account.signal}")
    if not props and account.description:
        props.append(f"Reflect the operating model described in the account record: {account.description}")
    if not props:
        props.append("Open a practical commercial conversation grounded in the account record")
    return props[:3]


def _message_focus(account: AccountRecord) -> str:
    if account.objective:
        return account.objective
    if account.signal and account.number_of_sites:
        return "booking conversion and repeat visits"
    if account.signal:
        return "the current commercial opportunity"
    if account.number_of_sites:
        return "commercial consistency across the footprint"
    return "a practical commercial next step"


def _business_insight(account: AccountRecord) -> str:
    location = account.hq_location or account.region or "the account's market"
    if account.number_of_sites and account.objective:
        site_phrase = "a single-site footprint" if account.number_of_sites == 1 else f"an {account.number_of_sites}-site footprint"
        return (
            f"{account.company_name} has {site_phrase} in {location}, "
            f"so the first message should stay focused on {account.objective} and avoid broad feature claims."
        )
    if account.signal:
        return (
            f"{account.company_name} has a clear current signal in {location}, so the outreach should stay tied to that trigger."
        )
    return f"The account has enough commercial context to justify a short, practical first-touch message in {location}."


def _estimated_impact(account: AccountRecord) -> str:
    visits = account.estimated_annual_visits
    revenue = account.estimated_annual_revenue
    if visits and revenue:
        uplift_visits = max(1, round(visits * 0.05))
        uplift_revenue = max(1, round(revenue * 0.05))
        return (
            f"A modest 5% uplift from the current base would be roughly {uplift_visits:,} additional annual visits "
            f"or about {uplift_revenue:,.0f} in annual revenue, depending on the lever."
        )
    if revenue:
        uplift_revenue = max(1, round(revenue * 0.05))
        return f"A modest 5% uplift could mean about {uplift_revenue:,.0f} in annual revenue."
    if visits:
        uplift_visits = max(1, round(visits * 0.05))
        return f"A modest 5% uplift could mean about {uplift_visits:,} additional annual visits."
    return "A small uplift in conversion or repeat visits would likely justify a follow-up commercial conversation."


def _tone_opening(tone: str) -> str:
    return {
        "concise": "Saw a few signals that made this worth a note.",
        "warm": "Noticed a few signals that felt relevant.",
        "direct": "Reaching out because this looks like a practical fit.",
    }[tone]


def _channel_suffix(channel: str) -> str:
    return {
        "email": "If this is useful, I can send a short follow-up with the idea in plain terms.",
        "linkedin": "If useful, I can share a short version here.",
    }[channel]


def _compose_message(account: AccountRecord, channel: str, tone: str) -> str:
    greeting = account.contact_name or "there"
    opening = _tone_opening(tone)
    focus = _message_focus(account)
    if account.signal and "opening" in account.signal.lower():
        signal_line = f"{account.company_name} is opening a new venue soon."
    elif account.signal:
        signal_line = f"{account.company_name} has a clear current signal: {account.signal}."
    else:
        signal_line = f"{account.company_name} is moving through a practical growth phase."

    if account.number_of_sites == 1:
        site_line = "For a single-site business, "
    elif account.number_of_sites:
        site_line = f"For an {account.number_of_sites}-site footprint, "
    else:
        site_line = "For teams like yours, "
    suffix = _channel_suffix(channel)
    closing = "Best,\nHermes" if channel == "email" else "Hermes"
    message = (
        f"Hi {greeting}, {opening} {signal_line} "
        f"{site_line}the priority is usually {focus}. "
        f"We can help turn that into a concise outreach note and a low-pressure next step. "
        f"{suffix} {closing}"
    )
    words = message.split()
    if len(words) > 140:
        message = " ".join(words[:140])
    return message


def _named_claim_tokens(account: AccountRecord) -> set[str]:
    tokens: set[str] = {
        "Hi",
        "I",
        "I'm",
        "If",
        "Saw",
        "Noticed",
        "We",
        "Worth",
        "The",
        "A",
        "As",
        "Best",
        "Hermes",
        "This",
        "For",
        "With",
        "On",
    }
    source_fields = [
        account.company_name,
        account.contact_name,
        account.contact_role,
        account.hq_location,
        account.region,
    ]
    for field in source_fields:
        if not field:
            continue
        for token in re.findall(r"[A-Za-z0-9&'-]+", field):
            if token:
                tokens.add(token)
    return tokens


def _guardrail_flags(account: AccountRecord, message: str, tone: str) -> list[str]:
    flags: list[str] = []
    if len(message.split()) > 140:
        flags.append("Message exceeds the 140-word limit.")
    if tone not in {"concise", "warm", "direct"}:
        flags.append("Tone falls outside the supported set.")
    if not account.contact_name:
        flags.append("No named contact provided, so the greeting stays generic.")
    if not account.signal and not account.objective and not account.description:
        flags.append("Source data is thin, so the message avoids unsupported claims.")
    supported_tokens = _named_claim_tokens(account)
    message_tokens = set(re.findall(r"\b[A-Z][A-Za-z0-9&'-]*\b", message))
    unexpected_tokens = sorted(
        token for token in message_tokens if token not in supported_tokens and token not in {"UK"}
    )
    if unexpected_tokens:
        flags.append(f"Unsupported named claims detected: {', '.join(unexpected_tokens)}.")
    return flags


def build_outreach_draft(account: AccountRecord, channel: str, tone: str) -> OutreachDraft:
    selected_value_props = _value_props(account)
    business_insight = _business_insight(account)
    estimated_impact = _estimated_impact(account)
    message = _compose_message(account, channel, tone)
    return OutreachDraft(
        account_id=account.account_id,
        company_name=account.company_name,
        contact_name=account.contact_name,
        contact_role=account.contact_role,
        selected_value_props=selected_value_props,
        business_insight=business_insight,
        estimated_impact=estimated_impact,
        message=message,
        guardrail_flags=_guardrail_flags(account, message, tone),
        channel=channel,
        tone=tone,
    )


def _focus_label(focus: str) -> str:
    return {
        "commercial": "Commercial",
        "operations": "Operations",
        "growth": "Growth",
        "customer_support": "Customer support",
    }[focus]


def _briefing_persona(account: AccountRecord, meeting_persona: str | None) -> str:
    if meeting_persona:
        return meeting_persona
    if account.contact_role:
        return account.contact_role
    if account.category:
        return f"{account.category} lead"
    return "commercial lead"


def _company_overview_lines(account: AccountRecord) -> list[str]:
    category = account.category or "commercial"
    sub_category = account.sub_category or "unspecified sub-category"
    location = account.hq_location or account.region or "an unspecified location"
    site_count = str(account.number_of_sites) if account.number_of_sites is not None else "not provided"
    visits = f"{account.estimated_annual_visits:,}" if account.estimated_annual_visits is not None else "not provided"
    ticket = f"{account.estimated_average_ticket_price:,.2f}" if account.estimated_average_ticket_price is not None else "not provided"
    revenue = f"{account.estimated_annual_revenue:,.0f}" if account.estimated_annual_revenue is not None else "not provided"
    lines = [
        f"{account.company_name} sits in the {category} space, with a sub-category of {sub_category}.",
        f"The account is based in {location} and is represented here with {site_count} site(s).",
        f"Estimated annual visits: {visits}. Average ticket price: {ticket}. Estimated annual revenue: {revenue}.",
    ]
    if account.description:
        description = account.description.rstrip(".")
        lines.append(f"Description from the source data: {description}.")
    return lines


def _opportunity_areas(account: AccountRecord, focus: str) -> list[str]:
    areas: list[str] = []
    if focus in {"commercial", "growth"}:
        areas.extend([
            "conversion improvement",
            "average transaction value / upsell",
        ])
    elif focus == "operations":
        areas.extend([
            "cost and complexity reduction",
            "reporting consistency",
        ])
    elif focus == "customer_support":
        areas.extend([
            "AI customer support",
            "cost and complexity reduction",
        ])

    if account.signal:
        areas.append("AI sales agent for group/corporate enquiries")
    if account.objective and "support" in account.objective.lower():
        areas.append("AI customer support")
    if account.objective and any(term in account.objective.lower() for term in {"book", "booking", "conversion", "grow", "revenue"}):
        areas.append("conversion improvement")

    deduped: list[str] = []
    for area in areas:
        if area not in deduped:
            deduped.append(area)
    return deduped[:3]


def _opportunity_summary(account: AccountRecord, meeting_persona: str | None, focus: str) -> str:
    persona = _briefing_persona(account, meeting_persona)
    areas = _opportunity_areas(account, focus)
    signal = account.signal or "the current account profile"
    objective = account.objective or "a practical commercial next step"
    area_text = ", ".join(areas) if areas else "conversion improvement and operational simplification"
    return (
        f"For {persona}, the strongest angle is to connect {signal} to {objective}. "
        f"That usually points to a small set of value areas: {area_text}. "
        f"The conversation should stay practical and focus on what would make the first step useful rather than on broad platform claims."
    )


def _quantified_value_case(account: AccountRecord) -> str:
    parts: list[str] = []
    if account.estimated_annual_visits is not None and account.estimated_annual_revenue is not None:
        upside_visits = max(1, round(account.estimated_annual_visits * 0.05))
        upside_revenue = max(1, round(account.estimated_annual_revenue * 0.05))
        parts.append(
            f"5% visit/revenue upside scenario: roughly {upside_visits:,} additional annual visits or about {upside_revenue:,.0f} in annual revenue. "
            "These are directional estimates based only on the account data."
        )
    elif account.estimated_annual_visits is not None:
        upside_visits = max(1, round(account.estimated_annual_visits * 0.05))
        parts.append(
            f"5% visit upside scenario: roughly {upside_visits:,} additional annual visits. This is a directional estimate based only on the account data."
        )
    elif account.estimated_annual_revenue is not None:
        upside_revenue = max(1, round(account.estimated_annual_revenue * 0.05))
        parts.append(
            f"5% revenue upside scenario: about {upside_revenue:,.0f} in annual revenue. This is a directional estimate based only on the account data."
        )
    else:
        parts.append("5% visit/revenue upside scenario: not enough data to calculate a directional estimate from the account record.")

    if account.estimated_transaction_volume is not None and account.estimated_average_ticket_price is not None:
        uplift_per_transaction = account.estimated_average_ticket_price * 0.08
        annual_uplift = account.estimated_transaction_volume * uplift_per_transaction
        parts.append(
            f"8% transaction value uplift scenario: about {uplift_per_transaction:,.2f} more per transaction, which would be roughly {annual_uplift:,.0f} annually if applied across the estimated transaction volume. "
            "This is a directional estimate based only on the account data."
        )
    elif account.estimated_average_ticket_price is not None:
        uplift_per_transaction = account.estimated_average_ticket_price * 0.08
        parts.append(
            f"8% transaction value uplift scenario: about {uplift_per_transaction:,.2f} more per transaction. "
            "The annual effect cannot be calculated cleanly because transaction volume is missing."
        )
    else:
        parts.append("8% transaction value uplift scenario: not enough pricing data to calculate a directional estimate.")

    return " ".join(parts)


def _suggested_questions(account: AccountRecord, focus: str) -> list[str]:
    questions = [
        f"What is the current priority behind {account.objective or 'the next commercial step'}?",
        "Where does the team see the most friction today: conversion, upsell, support, or reporting?",
        "Which part of the current process still depends on manual follow-up or spreadsheet work?",
        "What would make a first step feel useful enough to test without adding complexity?",
    ]
    if focus == "customer_support":
        questions[1] = "Where do customers need the most help today: booking, pre-visit questions, or post-visit support?"
    elif focus == "operations":
        questions[1] = "Where do manual steps or reporting handoffs create the most friction?"
    elif focus == "growth":
        questions[1] = "Which part of the commercial funnel needs the most help: discovery, conversion, or repeat visits?"
    return questions


def _likely_objections() -> list[tuple[str, str]]:
    return [
        (
            "We already have a process for this.",
            "That is usually the right starting point. The useful question is whether the current process leaves room for a lighter, faster first step.",
        ),
        (
            "Timing is not ideal.",
            "Fair point. A short review can still clarify whether there is a low-effort way to test the idea later.",
        ),
        (
            "We need to avoid adding complexity.",
            "Agreed. The conversation should stay focused on one practical use case and the smallest useful next step.",
        ),
    ]


def _systems_context() -> str:
    return (
        "Most teams in this space operate across separate ticketing, booking, CRM, support, spreadsheet, and reporting tools. "
        "The briefing should assume the opportunity is about making those systems work together more cleanly, not about replacing everything at once."
    )


def _recommended_next_step(account: AccountRecord, focus: str) -> str:
    objective = account.objective or "the current commercial priority"
    focus_value = _focus_label(focus).lower()
    return (
        f"Propose a short follow-up focused on {objective.lower()} and ask for one specific workflow or customer journey to review first. "
        f"Keep the next step narrow enough to assess {focus_value} value without adding process overhead."
    )


def _briefing_markdown(account: AccountRecord, meeting_persona: str | None, focus: str) -> str:
    overview = _company_overview_lines(account)
    persona = _briefing_persona(account, meeting_persona)
    if account.contact_name and account.contact_role:
        persona_block = f"Primary contact: {account.contact_name} ({account.contact_role})."
    elif account.contact_name:
        persona_block = f"Primary contact: {account.contact_name}."
    elif account.contact_role:
        persona_block = f"Likely persona: {account.contact_role}."
    else:
        persona_block = f"Likely persona: {persona}."

    markdown = "\n".join(
        [
            f"# Meeting Brief: {account.company_name}",
            "",
            "## 1. Company Overview",
            *[f"- {line}" for line in overview],
            "",
            "## 2. Individual / Persona Profile",
            persona_block,
            "",
            "## 3. Opportunity Analysis",
            _opportunity_summary(account, meeting_persona, focus),
            "",
            "## 4. Quantified Value Case",
            _quantified_value_case(account),
            "",
            "## 5. Suggested Talking Points",
            *[f"- {question}" for question in _suggested_questions(account, focus)],
            "",
            "## 6. Likely Objections",
            *[
                f"- Objection: {objection} Suggested response: {response}"
                for objection, response in _likely_objections()
            ],
            "",
            "## 7. Competitive / Systems Context",
            _systems_context(),
            "",
            "## 8. Recommended Next Step",
            _recommended_next_step(account, focus),
            "",
        ]
    )
    return markdown


def _briefing_guardrail_flags(account: AccountRecord, markdown: str) -> list[str]:
    flags: list[str] = []
    if len(markdown.split()) > 1000:
        flags.append("Briefing note is longer than the requested maximum.")
    if not account.contact_name:
        flags.append("No contact name was supplied, so the note is framed for the likely persona.")
    if not account.contact_role:
        flags.append("No contact role was supplied, so the note avoids assuming a named job title.")
    if not account.estimated_annual_visits and not account.estimated_annual_revenue and not account.estimated_transaction_volume:
        flags.append("Key scale data is missing, so the quantified value case is limited.")
    return flags


def build_briefing_markdown(account: AccountRecord, meeting_persona: str | None = None, focus: str = "commercial") -> BriefingNote:
    briefing_markdown = _briefing_markdown(account, meeting_persona, focus)
    opportunity_summary = _opportunity_summary(account, meeting_persona, focus)
    quantified_value_case = _quantified_value_case(account)
    talking_points = _suggested_questions(account, focus)
    likely_objections = [objection for objection, _ in _likely_objections()]
    recommended_next_step = _recommended_next_step(account, focus)
    return BriefingNote(
        account_id=account.account_id,
        company_name=account.company_name,
        contact_name=account.contact_name,
        contact_role=account.contact_role,
        briefing_markdown=briefing_markdown,
        opportunity_summary=opportunity_summary,
        quantified_value_case=quantified_value_case,
        talking_points=talking_points,
        likely_objections=likely_objections,
        recommended_next_step=recommended_next_step,
        guardrail_flags=_briefing_guardrail_flags(account, briefing_markdown),
    )


def _run_live_agent(output_type: type[Any], instructions: str, input_text: str) -> Any | None:
    try:
        from agents import Agent, Runner  # type: ignore
    except Exception:
        return None

    async def _runner() -> Any:
        agent = Agent(name="Hermes drafting agent", instructions=instructions, output_type=output_type)
        result = await Runner.run(agent, input_text)
        return result.final_output

    try:
        return asyncio.run(_runner())
    except RuntimeError:
        return None
