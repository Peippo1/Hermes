from __future__ import annotations

import asyncio
from dataclasses import dataclass
from hashlib import sha256
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


def _persona_for_account(account: AccountRecord) -> str:
    if account.contact_role:
        return account.contact_role
    if account.category:
        return f"{account.category} leader"
    return "commercial lead"


def _role_reasoning(account: AccountRecord) -> str:
    parts = [account.category, account.sub_category, account.objective]
    pieces = [part for part in parts if part]
    if pieces:
        return f"The available record points to {'; '.join(pieces)}."
    return "The record has enough commercial context to justify a practical first-touch message."


def _value_props(account: AccountRecord) -> list[str]:
    props = [
        account.signal or "current commercial activity in the account",
        account.objective or "a clearer path to commercial conversion",
        account.description or "the account's operating model and footprint",
    ]
    return [prop for prop in props if prop]


def _business_insight(account: AccountRecord) -> str:
    location = account.hq_location or account.region or "the account's market"
    if account.estimated_annual_revenue and account.number_of_sites:
        return (
            f"With {account.number_of_sites} sites and an estimated annual revenue of "
            f"{account.estimated_annual_revenue:,.0f}, {account.company_name} appears positioned to benefit from sharper conversion, "
            f"repeat visit, or group booking improvements in {location}."
        )
    return f"The account appears to have a meaningful commercial opportunity in {location}, based on the available record."


def _estimated_impact(account: AccountRecord) -> str:
    visits = account.estimated_annual_visits
    revenue = account.estimated_annual_revenue
    ticket = account.estimated_average_ticket_price
    if visits and revenue and ticket:
        uplift_visits = max(1, round(visits * 0.05))
        uplift_revenue = max(1, round(revenue * 0.05))
        return (
            f"A modest 5% uplift could mean roughly {uplift_visits:,} additional annual visits "
            f"or about {uplift_revenue:,.0f} in annual revenue, depending on the commercial lever."
        )
    if revenue:
        uplift_revenue = max(1, round(revenue * 0.05))
        return f"A modest 5% uplift could mean about {uplift_revenue:,.0f} in annual revenue."
    return "A small uplift in conversion or repeat visits would likely justify a follow-up commercial conversation."


def _risk_flags(account: AccountRecord, message: str) -> list[str]:
    flags: list[str] = [
        "Do not present unsupported claims as facts.",
        "Keep the tone credible and non-salesy.",
        "No real sending is performed from this prototype.",
    ]
    if not account.contact_name:
        flags.append("No named contact provided; keep the greeting generic.")
    if len(message.split()) > 170:
        flags.append("Outreach is longer than a concise cold message should be.")
    if not account.signal and not account.objective and not account.description:
        flags.append("Source data is thin; avoid unsupported claims.")
    if account.contact_name:
        flags.append("Named contact can be used only because it was present in the source file.")
    return flags


def build_outreach_draft(account: AccountRecord, channel: str, tone: str, goal: str) -> OutreachDraft:
    persona = _persona_for_account(account)
    role_reasoning = _role_reasoning(account)
    selected_value_props = _value_props(account)
    business_insight = _business_insight(account)
    estimated_impact = _estimated_impact(account)
    opener = account.contact_name if account.contact_name else "there"
    message = (
        f"Hi {opener},\n\n"
        f"{business_insight} "
        f"I thought it would be useful to share one idea that could support {goal} without adding unnecessary noise. "
        f"Specifically, the record suggests {selected_value_props[0] if selected_value_props else 'a clear commercial opportunity'}.\n\n"
        f"If it is relevant, I can share a short version tailored to the current priorities.\n\n"
        f"Best,\nHermes"
    )
    return OutreachDraft(
        account_id=account.account_id,
        company_name=account.company_name,
        persona=persona,
        role_reasoning=role_reasoning,
        selected_value_props=selected_value_props,
        business_insight=business_insight,
        estimated_impact=estimated_impact,
        message=message,
        risk_flags=_risk_flags(account, message),
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
