from __future__ import annotations

import json
from typing import Any

from .agents import _briefing_guardrail_flags, _guardrail_flags
from .models import AccountRecord, BriefingNote, BriefingRequest, OutreachDraft, OutreachRequest


FORBIDDEN_COMPETITORS = {
    "Salesforce",
    "HubSpot",
    "Zendesk",
    "Oracle",
    "Microsoft",
    "SAP",
    "Adobe",
}


class LiveGenerationError(RuntimeError):
    pass


def _create_client(api_key: str):
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - depends on optional dependency
        raise LiveGenerationError("OpenAI client is not installed.") from exc
    return OpenAI(api_key=api_key)


def _response_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text
    raise LiveGenerationError("Live response did not include text output.")


def _fallback_json_schema(client: Any, *, model_name: str, system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
    response = client.responses.create(
        model=model_name,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        text={"format": {"type": "json_object"}},
    )
    return json.loads(_response_text(response))


def _live_json_payload(
    *,
    api_key: str,
    model_name: str,
    system_prompt: str,
    user_payload: dict[str, Any],
    text_format: Any,
) -> Any:
    client = _create_client(api_key)
    try:
        response = client.responses.parse(
            model=model_name,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            text_format=text_format,
        )
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise LiveGenerationError("Structured live response could not be parsed.")
        return parsed
    except Exception:
        payload = _fallback_json_schema(
            client,
            model_name=model_name,
            system_prompt=system_prompt,
            user_payload=user_payload,
        )
        if hasattr(text_format, "model_validate"):
            return text_format.model_validate(payload)
        return payload


def _outreach_hard_failures(account: AccountRecord, draft: OutreachDraft) -> list[str]:
    flags: list[str] = []
    if len(draft.message.split()) > 100:
        flags.append("Live outreach exceeded the 100-word limit.")
    if draft.tone not in {"concise", "warm", "direct"}:
        flags.append("Live outreach used an unsupported tone.")
    lowered = draft.message.lower()
    for phrase in ("account record", "source-backed tokens", "guardrails", "internal data", "prototype"):
        if phrase in lowered:
            flags.append(f"Live outreach used internal wording: {phrase}.")
            break
    hard_named_claim_flags = [
        flag for flag in _guardrail_flags(account, draft.message, draft.tone) if "Unsupported named claims detected:" in flag
    ]
    flags.extend(hard_named_claim_flags)
    return flags


def _briefing_hard_failures(account: AccountRecord, note: BriefingNote) -> list[str]:
    flags: list[str] = []
    markdown = note.briefing_markdown
    if len(markdown.split()) > 1000:
        flags.append("Live briefing exceeded the requested length.")
    if "# Meeting Brief:" not in markdown:
        flags.append("Live briefing missed the required markdown structure.")
    for section in (
        "## 1. Company Overview",
        "## 2. Individual / Persona Profile",
        "## 3. Opportunity Analysis",
        "## 4. Quantified Value Case",
        "## 5. Suggested Talking Points",
        "## 6. Likely Objections",
        "## 7. Competitive / Systems Context",
        "## 8. Recommended Next Step",
    ):
        if section not in markdown:
            flags.append(f"Live briefing missed section: {section}.")
    if "directional" not in note.quantified_value_case.lower():
        flags.append("Live briefing did not label estimates as directional.")
    if any(name in markdown for name in FORBIDDEN_COMPETITORS):
        flags.append("Live briefing introduced named competitors.")
    flags.extend(_briefing_guardrail_flags(account, markdown))
    return flags


def generate_live_outreach(
    account: AccountRecord,
    request: OutreachRequest,
    *,
    api_key: str,
    model_name: str,
) -> OutreachDraft:
    system_prompt = (
        "You write commercially credible cold outreach for the experience commerce and location-based entertainment market. "
        "Return only structured JSON matching the requested schema. "
        "Keep the message under 100 words, make the commercial outcome specific, do not mention internal systems, prototypes, guardrails, or sending mechanics, "
        "and do not invent unsupported facts or named competitors."
    )
    user_payload = {
        "account": account.model_dump(mode="json"),
        "request": request.model_dump(mode="json"),
        "instructions": [
            "Use the account's own objective consistently.",
            "Reference the account signal naturally.",
            "Keep the tone credible and non-salesy.",
            "Return the same response shape as the deterministic generator.",
        ],
    }
    draft = _live_json_payload(
        api_key=api_key,
        model_name=model_name,
        system_prompt=system_prompt,
        user_payload=user_payload,
        text_format=OutreachDraft,
    )
    if not isinstance(draft, OutreachDraft):
        draft = OutreachDraft.model_validate(draft)
    hard_failures = _outreach_hard_failures(account, draft)
    if hard_failures:
        raise LiveGenerationError("; ".join(hard_failures))
    return draft.model_copy(update={"guardrail_flags": _guardrail_flags(account, draft.message, draft.tone)})


def generate_live_briefing(
    account: AccountRecord,
    request: BriefingRequest,
    *,
    api_key: str,
    model_name: str,
) -> BriefingNote:
    system_prompt = (
        "You produce concise sales briefing notes for the experience commerce and location-based entertainment market. "
        "Return only structured JSON matching the requested schema. "
        "The markdown must include the required sections, stay under 1000 words, use the account fields naturally, "
        "label estimates as directional, format objections as short objection/response pairs, keep the next step human and specific, "
        "and avoid named competitors or unsupported public claims."
    )
    user_payload = {
        "account": account.model_dump(mode="json"),
        "request": request.model_dump(mode="json"),
        "instructions": [
            "Write sales briefing material, not template prose.",
            "Use the account's objective, signal, and commercial scale data.",
            "Keep opportunity analysis specific and practical.",
            "Use paragraph breaks in outreach and a compact objection/response markdown structure in briefing notes.",
            "Use only platform categories in the systems context section.",
        ],
    }
    note = _live_json_payload(
        api_key=api_key,
        model_name=model_name,
        system_prompt=system_prompt,
        user_payload=user_payload,
        text_format=BriefingNote,
    )
    if not isinstance(note, BriefingNote):
        note = BriefingNote.model_validate(note)
    hard_failures = _briefing_hard_failures(account, note)
    if hard_failures:
        raise LiveGenerationError("; ".join(hard_failures))
    return note.model_copy(update={"guardrail_flags": _briefing_guardrail_flags(account, note.briefing_markdown)})
