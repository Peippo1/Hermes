from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from .models import AccountRecord


def _sample_rows() -> list[dict[str, str]]:
    return [
        {
            "account_id": "A-001",
            "account_name": "Account 001",
            "segment": "family entertainment",
            "venue_type": "multi-site indoor entertainment",
            "city": "Manchester",
            "region": "UK North",
            "country": "UK",
            "website": "https://example.invalid/001",
            "contact_name": "Contact 001",
            "contact_role": "Commercial Director",
            "signal": "new venue opening within the next quarter",
            "objective": "drive pre-opening bookings and memberships",
            "notes": "Values repeat visits and group revenue.",
            "source": "sample",
        },
        {
            "account_id": "A-002",
            "account_name": "Account 002",
            "segment": "immersive attraction",
            "venue_type": "single-site attraction",
            "city": "London",
            "region": "Greater London",
            "country": "UK",
            "website": "https://example.invalid/002",
            "contact_name": "Contact 002",
            "contact_role": "Head of Growth",
            "signal": "loyalty and retention campaign is active",
            "objective": "increase repeat visits and off-peak demand",
            "notes": "Prefers concise messages with a clear commercial angle.",
            "source": "sample",
        },
        {
            "account_id": "A-003",
            "account_name": "Account 003",
            "segment": "social gaming",
            "venue_type": "group entertainment venue",
            "city": "Birmingham",
            "region": "Midlands",
            "country": "UK",
            "website": "https://example.invalid/003",
            "contact_name": "Contact 003",
            "contact_role": "Revenue Lead",
            "signal": "corporate events team was recently expanded",
            "objective": "grow weekday group bookings",
            "notes": "Interested in practical ideas that can be launched quickly.",
            "source": "sample",
        },
        {
            "account_id": "A-004",
            "account_name": "Account 004",
            "segment": "active play",
            "venue_type": "regional leisure chain",
            "city": "Leeds",
            "region": "Yorkshire",
            "country": "UK",
            "website": "https://example.invalid/004",
            "contact_name": "Contact 004",
            "contact_role": "Operations Director",
            "signal": "site expansion planning is underway",
            "objective": "fill off-peak sessions and improve yield",
            "notes": "Sensitive to tone that feels too sales-heavy.",
            "source": "sample",
        },
        {
            "account_id": "A-005",
            "account_name": "Account 005",
            "segment": "live experience",
            "venue_type": "multi-activity venue",
            "city": "Bristol",
            "region": "South West",
            "country": "UK",
            "website": "https://example.invalid/005",
            "contact_name": "Contact 005",
            "contact_role": "Partnership Manager",
            "signal": "seasonal campaign planning is the current priority",
            "objective": "improve partner-led demand",
            "notes": "Uses event timing and local relevance in outreach.",
            "source": "sample",
        },
    ]


def load_accounts_from_path(path: str | Path | None = None) -> list[AccountRecord]:
    if path is None:
        return [AccountRecord.model_validate(row) for row in _sample_rows()]

    source = Path(path)
    if not source.exists():
        return [AccountRecord.model_validate(row) for row in _sample_rows()]

    if source.suffix.lower() in {".xlsx", ".xls"}:
        frame = pd.read_excel(source)
    else:
        frame = pd.read_csv(source)

    frame = frame.fillna("")
    records = frame.to_dict(orient="records")
    if not records:
        return [AccountRecord.model_validate(row) for row in _sample_rows()]

    normalised: list[AccountRecord] = []
    for idx, row in enumerate(records, start=1):
        data = dict(row)
        data.setdefault("account_id", data.get("id") or f"ROW-{idx:03d}")
        data.setdefault("account_name", data.get("name") or data["account_id"])
        normalised.append(AccountRecord.model_validate(data))
    return normalised


def accounts_to_dataframe(accounts: Iterable[AccountRecord]) -> pd.DataFrame:
    rows = [account.model_dump() for account in accounts]
    return pd.DataFrame(rows)

