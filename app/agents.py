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
        "concise": "I'm sharing one practical idea based on the account record.",
        "warm": "I noticed a few details in the account record that may be relevant.",
        "direct": "A short, practical note based on the account record:",
    }[tone]


def _channel_suffix(channel: str) -> str:
    return {
        "email": "If this is useful, I can send a short follow-up with the idea in plain terms.",
        "linkedin": "If useful, I can share a short version here.",
    }[channel]


def _compose_message(account: AccountRecord, channel: str, tone: str) -> str:
    greeting = account.contact_name or "there"
    opening = _tone_opening(tone)
    value_prop = _value_props(account)[0]
    business_line = _business_insight(account)
    suffix = _channel_suffix(channel)
    closing = "Best,\nHermes"
    if channel == "linkedin":
        closing = "Hermes"
    message = (
        f"Hi {greeting}, {opening} {business_line} "
        f"The most relevant angle looks like {value_prop.lower()}. "
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


def build_briefing_markdown(account: AccountRecord) -> BriefingNote:
    company_overview = (
        f"{account.company_name} is a {account.category or 'commercial'} account "
        f"with headquarters in {account.hq_location or 'an unspecified location'} and a regional footprint of "
        f"{account.number_of_sites if account.number_of_sites is not None else 'unknown'} sites."
    )
    persona_profile = (
        f"Primary persona: {account.contact_role or 'commercial lead'}\n\n"
        f"Reasoning: {account.contact_name or 'no named contact was supplied'}, so the brief should be written for the role rather than an assumed person."
    )
    value_case = (
        f"The strongest value case is around {account.objective or 'commercial conversion'}, using "
        f"{account.signal or 'the current account signal'} as the opening hook."
    )
    quantified_impact = _estimated_impact(account)
    talking_points = [
        "Lead with the commercial problem rather than a product pitch.",
        "Tie the conversation to current footprint, visit volume, or conversion efficiency where available.",
        "Keep the first meeting focused on practical next steps and proof criteria.",
    ]
    likely_objections = [
        "The timing is not right.",
        "We already have a process for this.",
        "We need evidence before changing anything.",
    ]
    competitive_context = (
        "The brief should assume the team may compare existing tools, internal processes, and alternative platforms; "
        "avoid overstating differentiation without evidence."
    )
    recommended_next_step = "Open with one relevant signal, confirm the current priority, and ask for the smallest useful next meeting step."
    markdown = "\n".join(
        [
            "# Briefing note",
            "",
            "## Company overview",
            company_overview,
            "",
            "## Individual/persona profile",
            persona_profile,
            "",
            "## Value case",
            value_case,
            "",
            "## Quantified impact",
            quantified_impact,
            "",
            "## Talking points",
            *[f"- {point}" for point in talking_points],
            "",
            "## Likely objections",
            *[f"- {point}" for point in likely_objections],
            "",
            "## Competitive context",
            competitive_context,
            "",
            "## Recommended next step",
            recommended_next_step,
            "",
        ]
    )
    return BriefingNote(account_id=account.account_id, company_name=account.company_name, markdown=markdown, source_data=account.model_dump())


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
