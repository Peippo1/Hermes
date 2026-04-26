from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import BriefingNote, OutreachMessage


def export_outreach_csv(items: Iterable[OutreachMessage], path: str | Path) -> Path:
    import pandas as pd

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame([item.model_dump() for item in items])
    frame.to_csv(target, index=False)
    return target


def export_json(payload: object, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return target


def export_markdown_outreach(items: Iterable[OutreachMessage], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = ["# Hermes outreach examples", ""]
    for item in items:
        lines.extend(
            [
                f"## {item.account_name}",
                f"- Subject: {item.subject}",
                f"- Channel: {item.channel}",
                f"- Tone: {item.tone}",
                "",
                item.body,
                "",
            ]
        )
    target.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return target


def export_markdown_briefings(items: Iterable[BriefingNote], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = ["# Hermes briefing examples", ""]
    for item in items:
        lines.extend(
            [
                f"## {item.account_name}",
                f"- Summary: {item.summary}",
                "- Snapshot:",
            ]
        )
        lines.extend([f"  - {value}" for value in item.account_snapshot])
        lines.extend(["- Opportunities:"] + [f"  - {value}" for value in item.opportunities])
        lines.extend(["- Risks:"] + [f"  - {value}" for value in item.risks])
        lines.extend(["- Questions:"] + [f"  - {value}" for value in item.questions] + [""])
    target.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return target
