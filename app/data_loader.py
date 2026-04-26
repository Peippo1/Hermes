from __future__ import annotations

import csv
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from pydantic import ValidationError

from .models import AccountRecord


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_PATH = BASE_DIR / "data" / "sample_accounts.csv"


class AccountDataError(RuntimeError):
    """Base error for account data loading failures."""


class AccountDataNotFoundError(AccountDataError):
    """Raised when the configured account data file is missing."""


class AccountDataMalformedError(AccountDataError):
    """Raised when the account data file cannot be parsed."""


ALIASES: dict[str, list[str]] = {
    "account_id": ["account_id", "id", "company_id", "record_id"],
    "company_name": ["company_name", "company", "account_name", "name"],
    "category": ["category", "segment", "industry"],
    "sub_category": ["sub_category", "subsegment", "venue_type", "vertical"],
    "description": ["description", "notes", "summary", "signal"],
    "hq_location": ["hq_location", "headquarters", "city", "location"],
    "number_of_sites": ["number_of_sites", "sites", "site_count"],
    "estimated_annual_visits": ["estimated_annual_visits", "annual_visits", "visits"],
    "estimated_average_ticket_price": ["estimated_average_ticket_price", "average_ticket_price", "ticket_price"],
    "estimated_transaction_volume": ["estimated_transaction_volume", "transaction_volume", "transactions"],
    "estimated_annual_revenue": ["estimated_annual_revenue", "annual_revenue", "revenue"],
    "region": ["region", "market", "territory"],
    "contact_name": ["contact_name", "contact"],
    "contact_role": ["contact_role", "role", "title"],
    "website": ["website", "url", "site"],
    "signal": ["signal", "source_signal"],
    "objective": ["objective", "goal"],
    "notes": ["notes", "commentary"],
    "source": ["source"],
}


def _sample_rows() -> list[dict[str, Any]]:
    return [
        {
            "account_id": "ACCT-001",
            "company_name": "Northstar Leisure Group",
            "category": "family entertainment",
            "sub_category": "multi-site indoor entertainment",
            "description": "Regional operator focused on family bookings and repeat visits.",
            "hq_location": "Manchester, UK",
            "number_of_sites": 8,
            "estimated_annual_visits": 1240000,
            "estimated_average_ticket_price": 24.5,
            "estimated_transaction_volume": 510000,
            "estimated_annual_revenue": 30400000,
            "region": "UK North",
            "contact_name": "Avery Hughes",
            "contact_role": "Commercial Director",
            "website": "https://example.invalid/northstar",
            "signal": "new venue opening within the next quarter",
            "objective": "drive pre-opening bookings and memberships",
            "notes": "Values repeat visits and group revenue.",
            "source": "sample",
        },
        {
            "account_id": "ACCT-002",
            "company_name": "Harbor Experience Co",
            "category": "immersive attraction",
            "sub_category": "single-site attraction",
            "description": "Destination attraction balancing day tickets with loyalty offers.",
            "hq_location": "London, UK",
            "number_of_sites": 1,
            "estimated_annual_visits": 420000,
            "estimated_average_ticket_price": 31.0,
            "estimated_transaction_volume": 183000,
            "estimated_annual_revenue": 13020000,
            "region": "Greater London",
            "contact_name": "Mina Patel",
            "contact_role": "Head of Growth",
            "website": "https://example.invalid/harbor",
            "signal": "retention campaign is active",
            "objective": "increase repeat visits and off-peak demand",
            "notes": "Prefers concise messages with a clear commercial angle.",
            "source": "sample",
        },
        {
            "account_id": "ACCT-003",
            "company_name": "Vertex Social Games",
            "category": "social gaming",
            "sub_category": "group entertainment venue",
            "description": "Expanding corporate events and weekday group bookings.",
            "hq_location": "Birmingham, UK",
            "number_of_sites": 3,
            "estimated_annual_visits": 280000,
            "estimated_average_ticket_price": 27.0,
            "estimated_transaction_volume": 119000,
            "estimated_annual_revenue": 7560000,
            "region": "Midlands",
            "contact_name": "Jordan Price",
            "contact_role": "Revenue Lead",
            "website": "https://example.invalid/vertex",
            "signal": "corporate events team was recently expanded",
            "objective": "grow weekday group bookings",
            "notes": "Interested in practical ideas that can be launched quickly.",
            "source": "sample",
        },
    ]


def _normalize_column_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _canonicalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {_normalize_column_name(key): value for key, value in row.items() if _normalize_column_name(key)}


def _coerce_int(value: Any) -> int | None:
    if value in ("", None):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _coerce_float(value: Any) -> float | None:
    if value in ("", None):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pick_value(row: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in ("", None):
            return value
    return None


def _row_from_record(raw_row: dict[str, Any]) -> dict[str, Any]:
    normalized_row = _canonicalize_row(raw_row)
    record: dict[str, Any] = {}
    for target, aliases in ALIASES.items():
        normalized_aliases = [_normalize_column_name(alias) for alias in [target, *aliases]]
        record[target] = _pick_value(normalized_row, normalized_aliases)

    record["account_id"] = record["account_id"] or normalized_row.get("account_id") or normalized_row.get("id")
    record["company_name"] = record["company_name"] or normalized_row.get("company_name") or record["account_id"]
    record["number_of_sites"] = _coerce_int(record["number_of_sites"])
    record["estimated_annual_visits"] = _coerce_int(record["estimated_annual_visits"])
    record["estimated_average_ticket_price"] = _coerce_float(record["estimated_average_ticket_price"])
    record["estimated_transaction_volume"] = _coerce_int(record["estimated_transaction_volume"])
    record["estimated_annual_revenue"] = _coerce_float(record["estimated_annual_revenue"])
    return {**normalized_row, **record}


def _load_csv_records(source: Path) -> list[dict[str, Any]]:
    try:
        with source.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or not any((field or "").strip() for field in reader.fieldnames):
                raise AccountDataMalformedError(f"CSV file '{source}' is missing a header row.")

            records: list[dict[str, Any]] = []
            for row in reader:
                if not any(value not in ("", None) for value in row.values()):
                    continue
                records.append(row)
    except AccountDataError:
        raise
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise AccountDataMalformedError(f"CSV file '{source}' could not be read: {exc}") from exc

    if not records:
        raise AccountDataMalformedError(f"CSV file '{source}' does not contain any data rows.")
    return records


def _cell_reference_to_index(reference: str) -> int:
    match = re.match(r"([A-Z]+)", reference.upper())
    if not match:
        return 0
    column = match.group(1)
    index = 0
    for char in column:
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index - 1


def _load_xlsx_records(source: Path) -> list[dict[str, Any]]:
    namespace = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

    try:
        with zipfile.ZipFile(source) as archive:
            shared_strings: list[str] = []
            if "xl/sharedStrings.xml" in archive.namelist():
                shared_tree = ET.fromstring(archive.read("xl/sharedStrings.xml"))
                for item in shared_tree.findall(".//a:si", namespace):
                    text_parts = [node.text or "" for node in item.findall(".//a:t", namespace)]
                    shared_strings.append("".join(text_parts))

            try:
                sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
            except KeyError as exc:
                raise AccountDataMalformedError(f"XLSX file '{source}' does not contain sheet1.") from exc

            rows: list[list[str]] = []
            for row in sheet.findall(".//a:sheetData/a:row", namespace):
                values: list[str] = []
                for cell in row.findall("a:c", namespace):
                    cell_reference = cell.attrib.get("r", "A1")
                    cell_index = _cell_reference_to_index(cell_reference)
                    while len(values) <= cell_index:
                        values.append("")

                    cell_type = cell.attrib.get("t")
                    value = ""
                    if cell_type == "s":
                        index_text = cell.findtext("a:v", default="0", namespaces=namespace)
                        if index_text.isdigit():
                            shared_index = int(index_text)
                            if shared_index < len(shared_strings):
                                value = shared_strings[shared_index]
                    elif cell_type == "inlineStr":
                        value = "".join(node.text or "" for node in cell.findall(".//a:t", namespace))
                    else:
                        value = cell.findtext("a:v", default="", namespaces=namespace) or ""

                    values[cell_index] = value
                rows.append(values)
    except AccountDataError:
        raise
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise AccountDataMalformedError(f"XLSX file '{source}' could not be read: {exc}") from exc

    if not rows:
        raise AccountDataMalformedError(f"XLSX file '{source}' does not contain any rows.")

    header = [column.strip() for column in rows[0]]
    if not any(header):
        raise AccountDataMalformedError(f"XLSX file '{source}' is missing a header row.")

    records: list[dict[str, Any]] = []
    for row_values in rows[1:]:
        if not any(value not in ("", None) for value in row_values):
            continue
        record = {
            header[index]: (row_values[index] if index < len(row_values) else "")
            for index in range(len(header))
            if header[index]
        }
        records.append(record)

    if not records:
        raise AccountDataMalformedError(f"XLSX file '{source}' does not contain any data rows.")
    return records


def normalise_row(row: dict[str, Any], fallback_index: int) -> AccountRecord:
    record = _row_from_record(row)
    record["account_id"] = record["account_id"] or f"ROW-{fallback_index:03d}"
    record["company_name"] = record["company_name"] or record["account_id"]
    try:
        return AccountRecord.model_validate(record)
    except ValidationError as exc:
        raise AccountDataMalformedError(f"Row {fallback_index} is invalid: {exc}") from exc


def load_accounts_from_path(path: str | Path | None = None) -> list[AccountRecord]:
    source = Path(path) if path is not None else DEFAULT_DATA_PATH

    if not source.exists():
        raise AccountDataNotFoundError(f"Account data file '{source}' does not exist.")

    suffix = source.suffix.lower()
    if suffix == ".csv":
        records = _load_csv_records(source)
    elif suffix == ".xlsx":
        records = _load_xlsx_records(source)
    else:
        raise AccountDataMalformedError(f"Unsupported account data format '{source.suffix}'. Use CSV or XLSX.")

    return [normalise_row(row, idx) for idx, row in enumerate(records, start=1)]


def accounts_to_dataframe(accounts: list[AccountRecord]) -> list[dict[str, Any]]:
    return [account.model_dump() for account in accounts]
