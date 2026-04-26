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
