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


def _format_quantity(value: int | float) -> str:
    amount = float(value)
    if abs(amount) >= 1_000_000:
        text = f"{amount / 1_000_000:.2f}".rstrip("0").rstrip(".")
        return f"{text}m"
    if abs(amount) >= 1_000:
        text = f"{amount / 1_000:.1f}".rstrip("0").rstrip(".")
        return f"{text}k"
    if amount.is_integer():
        return f"{int(amount)}"
    return f"{amount:.1f}".rstrip("0").rstrip(".")


def _format_currency(value: float | int) -> str:
    amount = float(value)
    if abs(amount) >= 1_000_000:
        text = f"${amount / 1_000_000:.2f}".rstrip("0").rstrip(".")
        return f"{text}m"
    if abs(amount) >= 1_000:
        text = f"${amount / 1_000:.1f}".rstrip("0").rstrip(".")
        return f"{text}k"
    if amount.is_integer():
        return f"${int(amount)}"
    return f"${amount:.2f}"


def _site_phrase(account: AccountRecord) -> str:
    if account.number_of_sites == 1:
        return "a single-site footprint"
    if account.number_of_sites is None:
        return "a footprint"
    return f"a {account.number_of_sites}-site footprint"


def _footprint_label(account: AccountRecord) -> str:
    if account.number_of_sites == 1:
        return "single-site footprint"
    if account.number_of_sites is None:
        return "commercial footprint"
    return f"{account.number_of_sites}-site footprint"


def _format_average_ticket(account: AccountRecord) -> str:
    if account.estimated_average_ticket_price is None:
        return "an unspecified average ticket"
    return f"{_format_currency(account.estimated_average_ticket_price)} average ticket"


def _outreach_levers(account: AccountRecord) -> str:
    role = (account.contact_role or "").lower()
    category = (account.category or "").lower()
    sub_category = (account.sub_category or "").lower()
    if "partnership" in role:
        return "booking conversion, repeat visits and private-hire enquiries"
    if any(term in role for term in {"sales", "commercial", "revenue", "growth"}):
        return "booking conversion, repeat visits and upsell"
    if "operations" in role:
        return "booking flow, handoffs and service consistency"
    if "finance" in role:
        return "yield, margin and revenue quality"
    if "competitive socialising" in category or any(term in sub_category for term in {"arcade", "mini golf", "darts", "bowling", "escape", "kart", "golf"}):
        return "booking conversion, repeat visits and private-hire enquiries"
    if account.objective:
        return account.objective
    return "booking conversion and repeat visits"


def _value_props(account: AccountRecord) -> list[str]:
    props: list[str] = []
    if account.number_of_sites:
        props.append(f"{account.number_of_sites}-site footprint creates a clear case for better conversion")
    if account.estimated_annual_visits:
        props.append(f"About {_format_quantity(account.estimated_annual_visits)} annual visits means small gains matter")
    if account.estimated_transaction_volume:
        props.append(f"Estimated transaction volume of {_format_currency(account.estimated_transaction_volume)} gives the account enough scale to test")
    if account.objective:
        props.append(f"First conversation should align to the stated objective: {account.objective}")
    if account.signal:
        props.append(f"Current signal to reference: {account.signal}")
    if not props and account.description:
        props.append(f"Operating model from the source data: {account.description}")
    if not props:
        props.append("Open a practical commercial conversation grounded in the source data")
    return props[:3]


def _business_insight(account: AccountRecord) -> str:
    location = account.hq_location or account.region or "the account's market"
    site_phrase = _site_phrase(account)
    levers = _outreach_levers(account)
    if account.estimated_annual_visits and account.estimated_transaction_volume:
        return (
            f"{account.company_name} has {site_phrase} in {location}, with about {_format_quantity(account.estimated_annual_visits)} annual visits "
            f"and roughly {_format_currency(account.estimated_transaction_volume)} in transaction volume, so {levers} are worth a closer look."
        )
    if account.estimated_annual_visits:
        return (
            f"{account.company_name} has {site_phrase} in {location} and about {_format_quantity(account.estimated_annual_visits)} annual visits, "
            f"so {levers} are worth a closer look."
        )
    if account.signal:
        return f"{account.company_name} has {site_phrase} in {location} and a clear current signal, so the outreach should stay tied to that trigger."
    return f"{account.company_name} has enough commercial context in {location} to justify a short, practical first-touch message."


def _estimated_impact(account: AccountRecord) -> str:
    visits = account.estimated_annual_visits
    transaction_volume = account.estimated_transaction_volume
    revenue = account.estimated_annual_revenue
    if visits and transaction_volume:
        uplift_visits = max(1, round(visits * 0.05))
        uplift_volume = max(1, round(transaction_volume * 0.05))
        return (
            f"A 25% uplift in conversion on a narrow journey would be a strong upside case. "
            f"Conservatively, a 5% lift from { _format_quantity(visits) } annual visits is about {uplift_visits:,} additional visits, "
            f"and a 5% lift on {_format_currency(transaction_volume)} in transaction volume is about {_format_currency(uplift_volume)}."
        )
    if visits:
        uplift_visits = max(1, round(visits * 0.05))
        return (
            "A 25% uplift in conversion on a narrow journey would be a strong upside case. "
            f"Conservatively, a 5% lift from {_format_quantity(visits)} annual visits is about {uplift_visits:,} additional visits."
        )
    if transaction_volume:
        uplift_volume = max(1, round(transaction_volume * 0.05))
        return (
            "A 25% uplift in conversion on a narrow journey would be a strong upside case. "
            f"Conservatively, a 5% lift on {_format_currency(transaction_volume)} in transaction volume is about {_format_currency(uplift_volume)}."
        )
    if revenue:
        uplift_revenue = max(1, round(revenue * 0.05))
        return (
            "A 25% uplift in conversion on a narrow journey would be a strong upside case. "
            f"Conservatively, a 5% lift on {_format_currency(revenue)} in annual revenue is about {_format_currency(uplift_revenue)}."
        )
    return "A 25% uplift in conversion on a narrow journey would be a strong upside case, but the source data is too thin for a conservative estimate."


def _tone_opening(tone: str) -> str:
    return {
        "concise": "Worth a quick look.",
        "warm": "Worth a closer look.",
        "direct": "Worth a direct look.",
    }[tone]


def _channel_suffix(channel: str) -> str:
    return {
        "email": "If this is useful, I can send a short follow-up with the idea in plain terms.",
        "linkedin": "If useful, I can share a short version here.",
    }[channel]


def _opening_sentence(account: AccountRecord, tone: str) -> str:
    if account.objective:
        return {
            "concise": f"{account.company_name} has a current focus on {account.objective} that looks commercially relevant.",
            "warm": f"{account.company_name} has a current focus on {account.objective} that looks commercially relevant for the next conversation.",
            "direct": f"{account.company_name} has a current focus on {account.objective} that looks commercially relevant for the next step.",
        }[tone]

    levers = _outreach_levers(account)
    if account.estimated_annual_visits and account.estimated_transaction_volume:
        return {
            "concise": f"{account.company_name} has a {_footprint_label(account)} and group-friendly format that make {levers} the obvious levers.",
            "warm": f"{account.company_name} has a {_footprint_label(account)} and group-friendly format that make {levers} the obvious levers to focus on.",
            "direct": f"{account.company_name} has a {_footprint_label(account)} and group-friendly format that make {levers} the obvious levers to tighten.",
        }[tone]
    if account.estimated_annual_visits:
        return {
            "concise": f"{account.company_name} has a {_footprint_label(account)} and visit volume that make {levers} the obvious levers.",
            "warm": f"{account.company_name} has a {_footprint_label(account)} and visit volume that make {levers} the obvious levers to focus on.",
            "direct": f"{account.company_name} has a {_footprint_label(account)} and visit volume that make {levers} the obvious levers to tighten.",
        }[tone]
    return {
        "concise": f"{account.company_name} has a commercial profile that makes {levers} the obvious levers.",
        "warm": f"{account.company_name} has a commercial profile that makes {levers} the obvious levers to focus on.",
        "direct": f"{account.company_name} has a commercial profile that makes {levers} the obvious levers to tighten.",
    }[tone]


def _compose_message(account: AccountRecord, channel: str, tone: str) -> str:
    greeting = account.contact_name.split()[0] if account.contact_name else "there"
    opening = _opening_sentence(account, tone)
    metrics: list[str] = []
    if account.estimated_annual_visits is not None:
        metrics.append(f"roughly {_format_quantity(account.estimated_annual_visits)} annual visits")
    if account.estimated_average_ticket_price is not None:
        metrics.append(f"a {_format_currency(account.estimated_average_ticket_price)} average ticket")
    if account.estimated_transaction_volume is not None:
        metrics.append(f"about {_format_currency(account.estimated_transaction_volume)} in transaction volume")
    if account.estimated_annual_revenue is not None:
        metrics.append(f"about {_format_currency(account.estimated_annual_revenue)} in annual revenue")
    metric_text = ", ".join(metrics[:3])
    role_prefix = f"As {account.contact_role}, " if account.contact_role else ""
    metric_clause = f" With {metric_text}, even small improvements in conversion or upsell could be meaningful." if metric_text else " Even small improvements in conversion or upsell could be meaningful."
    message = f"Hi {greeting}, {role_prefix}{opening}{metric_clause} Worth a quick look at where the booking and group-sales journey could be tightened?"
    words = message.split()
    if len(words) > 100:
        message = " ".join(words[:100])
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
    site_count = (
        f"{account.number_of_sites} site" if account.number_of_sites == 1 else f"{account.number_of_sites} sites"
    ) if account.number_of_sites is not None else "not provided"
    visits = _format_quantity(account.estimated_annual_visits) if account.estimated_annual_visits is not None else "not provided"
    ticket = _format_currency(account.estimated_average_ticket_price) if account.estimated_average_ticket_price is not None else "not provided"
    revenue = _format_currency(account.estimated_annual_revenue) if account.estimated_annual_revenue is not None else "not provided"
    lines = [
        f"{account.company_name} sits in the {category} space, with a sub-category of {sub_category}.",
        f"The account is based in {location} and is represented here with {site_count}.",
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
            "repeat visits and upsell",
        ])
    elif focus == "operations":
        areas.extend([
            "booking flow and handoff clarity",
            "reporting consistency",
        ])
    elif focus == "customer_support":
        areas.extend([
            "booking support and response speed",
            "customer support load reduction",
        ])

    if account.contact_role and "partnership" in account.contact_role.lower():
        areas.append("group-sales follow-up")
    if account.estimated_transaction_volume is not None:
        areas.append("transaction value uplift")
    if account.estimated_annual_visits is not None:
        areas.append("conversion improvement")
    if account.objective and "support" in account.objective.lower():
        areas.append("customer support load reduction")
    if account.objective and any(term in account.objective.lower() for term in {"book", "booking", "conversion", "grow", "revenue", "membership"}):
        areas.append("conversion improvement")

    deduped: list[str] = []
    for area in areas:
        if area not in deduped:
            deduped.append(area)
    return deduped[:3]


def _opportunity_summary(account: AccountRecord, meeting_persona: str | None, focus: str) -> str:
    persona = _briefing_persona(account, meeting_persona)
    levers = _outreach_levers(account)
    site_phrase = _site_phrase(account)
    if account.objective:
        return (
            f"For a {persona}, the cleanest angle is to keep the conversation on {account.objective} across {site_phrase}. "
            f"The data points to {levers}, so the first meeting should stay close to one real workflow or enquiry path."
        )
    return (
        f"For a {persona}, the cleanest angle is to improve {levers} across {site_phrase}. "
        f"The data points to one practical workflow or enquiry path that can be reviewed without broad platform claims."
    )


def _opportunity_analysis(account: AccountRecord, meeting_persona: str | None, focus: str) -> str:
    persona = _briefing_persona(account, meeting_persona)
    areas = _opportunity_areas(account, focus)
    area_text = ", ".join(areas) if areas else "conversion improvement and operational simplification"
    levers = _outreach_levers(account)
    if account.estimated_annual_visits and account.estimated_transaction_volume:
        return (
            f"For a {persona}, the practical angle is to tighten {levers} without adding more process overhead. "
            f"With { _format_quantity(account.estimated_annual_visits) } annual visits and roughly {_format_currency(account.estimated_transaction_volume)} in transaction volume, "
            f"the opportunity is most likely to show up in {area_text}."
        )
    if account.estimated_annual_visits:
        return (
            f"For a {persona}, the practical angle is to tighten {levers} without adding more process overhead. "
            f"With { _format_quantity(account.estimated_annual_visits) } annual visits, the opportunity is most likely to show up in {area_text}."
        )
    return (
        f"For a {persona}, the practical angle is to tighten {levers} without adding more process overhead. "
        f"The opportunity is most likely to show up in {area_text}."
    )


def _quantified_value_case(account: AccountRecord) -> str:
    parts: list[str] = []
    if account.estimated_annual_visits is not None and account.estimated_annual_revenue is not None:
        upside_visits = max(1, round(account.estimated_annual_visits * 0.05))
        upside_revenue = max(1, round(account.estimated_annual_revenue * 0.05))
        parts.append(
            f"25% conversion uplift value proposition: a meaningful improvement on one high-intent journey would be the upside case. "
            f"Conservatively, a 5% visit uplift would be roughly {upside_visits:,} additional annual visits, and a 5% revenue uplift would be about {_format_currency(upside_revenue)} in annual revenue. "
            "These are directional estimates based only on the account data."
        )
    elif account.estimated_annual_visits is not None:
        upside_visits = max(1, round(account.estimated_annual_visits * 0.05))
        parts.append(
            f"25% conversion uplift value proposition: a meaningful improvement on one high-intent journey would be the upside case. "
            f"Conservatively, a 5% visit uplift would be roughly {upside_visits:,} additional annual visits. This is a directional estimate based only on the account data."
        )
    elif account.estimated_annual_revenue is not None:
        upside_revenue = max(1, round(account.estimated_annual_revenue * 0.05))
        parts.append(
            f"25% conversion uplift value proposition: a meaningful improvement on one high-intent journey would be the upside case. "
            f"Conservatively, a 5% revenue uplift would be about {_format_currency(upside_revenue)} in annual revenue. This is a directional estimate based only on the account data."
        )
    else:
        parts.append("25% conversion uplift value proposition: not enough data to calculate a directional estimate from the account record.")

    if account.estimated_transaction_volume is not None:
        upside_transaction_volume = max(1, round(account.estimated_transaction_volume * 0.05))
        parts.append(
            f"Transaction volume context: a 5% uplift on {_format_currency(account.estimated_transaction_volume)} would be about {_format_currency(upside_transaction_volume)} annually. "
            "This remains a directional estimate based only on the account data."
        )
    if account.estimated_average_ticket_price is not None:
        parts.append(
            f"Average ticket context: {_format_currency(account.estimated_average_ticket_price)} per sale gives enough headroom to test upsell or conversion improvements without changing the core offer."
        )

    return " ".join(parts)


def _suggested_questions(account: AccountRecord, focus: str) -> list[str]:
    questions = [
        f"What is driving the focus on {account.objective or 'the next commercial step'}?",
        "Where are high-intent enquiries dropping out today?",
        "Which step still relies on manual follow-up or chasing?",
        "If conversion improved by 25% on one journey, what would the team expect to see first?",
    ]
    if focus == "customer_support":
        questions[1] = "Where do customers need the most help today: booking, pre-visit questions, or post-visit support?"
        questions[2] = "Which support step still needs the most manual follow-up?"
    elif focus == "operations":
        questions[1] = "Where do manual handoffs or reporting gaps create the most friction?"
        questions[2] = "Which handoff still feels slow or error-prone?"
    elif focus == "growth":
        questions[1] = "Which part of the commercial funnel needs the most help: discovery, conversion, or repeat visits?"
        questions[2] = "What would a better conversion path need to prove before anyone scaled it?"
    return questions


def _likely_objections() -> list[tuple[str, str]]:
    return [
        (
            "We already have a process for this.",
            "That is a sensible starting point. The useful question is whether the current process leaves room for a lighter, faster first step.",
        ),
        (
            "Timing is not ideal.",
            "Fair point. A short review can still show whether there is a low-effort way to test the idea later.",
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
        persona_block = f"For a {account.contact_role}, the primary contact is {account.contact_name}."
    elif account.contact_name:
        persona_block = f"Primary contact: {account.contact_name}."
    elif account.contact_role:
        persona_block = f"For a {account.contact_role}."
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
            _opportunity_analysis(account, meeting_persona, focus),
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
