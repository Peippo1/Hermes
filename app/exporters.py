from __future__ import annotations

import json
import csv
from pathlib import Path
from typing import Iterable

from .models import BriefingNote, OutreachDraft, QueueItem


def export_outreach_csv(items: Iterable[OutreachDraft], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = [item.model_dump() for item in items]
    if rows:
        with target.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    else:
        target.write_text("", encoding="utf-8")
    return target


def export_outreach_json(items: Iterable[OutreachDraft], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps([item.model_dump() for item in items], indent=2, default=str), encoding="utf-8")
    return target


def export_briefing_markdown(note: BriefingNote, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(note.briefing_markdown.rstrip() + "\n", encoding="utf-8")
    return target


def export_queue_json(items: Iterable[QueueItem], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps([item.model_dump(mode="json") for item in items], indent=2, default=str), encoding="utf-8")
    return target


def export_report_json(report: dict[str, object], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return target


def export_report_markdown(report: dict[str, object], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    summary = report.get("summary_counts", {})
    outreach_examples = report.get("generated_outreach_examples", [])
    queued_items = report.get("queued_outreach_items", [])
    guardrail_flags = report.get("guardrail_flags", [])
    timestamp = report.get("generated_at", "Unknown")

    lines: list[str] = [
        "# Hermes Report",
        "",
        f"Generated at: {timestamp}",
        "",
        "## Summary Counts",
        f"- Outreach examples: {summary.get('outreach_examples', 0)}",
        f"- Queued outreach items: {summary.get('queued_outreach_items', 0)}",
        f"- Guardrail flags: {summary.get('guardrail_flags', 0)}",
        "",
        "## Generated Outreach Examples",
    ]

    for item in outreach_examples:
        lines.extend(
            [
                f"- {item.get('company_name', 'Unknown company')}: {item.get('message', '')}",
            ]
        )

    lines.extend(["", "## Queued Outreach Items"])
    for item in queued_items:
        lines.append(f"- {item.get('company_name', 'Unknown company')} ({item.get('status', 'unknown')})")

    lines.extend(["", "## Guardrail Flags"])
    if guardrail_flags:
        for flag in guardrail_flags:
            lines.append(f"- {flag}")
    else:
        lines.append("- None")

    lines.append("")
    target.write_text("\n".join(lines), encoding="utf-8")
    return target
