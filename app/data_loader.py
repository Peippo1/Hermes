from __future__ import annotations

import csv
import io
import logging
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.error import URLError
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from urllib.request import urlopen
from xml.etree import ElementTree as ET

from pydantic import ValidationError

from .models import AccountRecord


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_PATH = BASE_DIR / "data" / "sample_accounts.csv"
DEFAULT_DATA_PATH_LABEL = "data/sample_accounts.csv"
LOGGER = logging.getLogger(__name__)

DataSourceName = Literal["google_sheet", "local_file", "sample_fallback"]


class AccountDataError(RuntimeError):
    """Base error for account data loading failures."""


class AccountDataNotFoundError(AccountDataError):
    """Raised when the configured account data file is missing."""


class AccountDataMalformedError(AccountDataError):
    """Raised when the account data file cannot be parsed."""


@dataclass(frozen=True)
class AccountLoadResult:
    accounts: list[AccountRecord]
    data_source: DataSourceName
    data_source_detail: str
    data_load_warning: str | None = None


ALIASES: dict[str, list[str]] = {
    "account_id": ["account_id", "id", "company_id", "record_id", "account name", "account"],
    "company_name": ["company_name", "company", "account_name", "account name", "name"],
    "category": ["category", "segment", "industry"],
    "sub_category": ["sub_category", "sub-category", "subsegment", "venue_type", "vertical"],
    "description": ["description", "notes", "summary", "signal"],
    "hq_location": ["hq_location", "hq location", "headquarters", "city", "location"],
    "number_of_sites": ["number_of_sites", "sites", "site count"],
    "estimated_annual_visits": ["estimated_annual_visits", "est. annual visits", "annual_visits", "annual visits", "visits"],
    "estimated_average_ticket_price": [
        "estimated_average_ticket_price",
        "est. avg ticket price ($)",
        "estimated avg ticket price ($)",
        "average_ticket_price",
        "average ticket price",
        "ticket_price",
        "ticket price",
    ],
    "estimated_transaction_volume": [
        "estimated_transaction_volume",
        "est. total transaction volume ($)",
        "estimated total transaction volume ($)",
        "transaction_volume",
        "transaction volume",
        "transactions",
    ],
    "estimated_annual_revenue": [
        "estimated_annual_revenue",
        "est. easol annual revenue ($)",
        "estimated easol annual revenue ($)",
        "annual_revenue",
        "annual revenue",
        "revenue",
    ],
    "region": ["region", "market", "territory"],
    "contact_name": ["contact_name", "contact name", "contact"],
    "contact_role": ["contact_role", "contact title", "contact title/role", "contact role", "role", "title"],
    "website": ["website", "url", "site"],
    "signal": ["signal", "source_signal"],
    "objective": ["objective", "goal"],
    "notes": ["notes", "commentary"],
    "source": ["source"],
}

CONTACT_CATEGORY_PRIORITY = {
    "commercial": 0,
    "ceo_managing_director": 1,
    "operations": 2,
    "finance": 3,
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


EXPECTED_HEADER_NAMES = {
    _normalize_column_name(name)
    for canonical, aliases in ALIASES.items()
    for name in [canonical, *aliases]
}


def _canonicalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {_normalize_column_name(key): value for key, value in row.items() if _normalize_column_name(key)}


def _coerce_int(value: Any) -> int | None:
    if value in ("", None):
        return None
    try:
        text = str(value).strip()
        if not text:
            return None
        text = re.sub(r"[^0-9.\-]", "", text)
        if not text or text in {".", "-", "-."}:
            return None
        return int(float(text))
    except (TypeError, ValueError):
        return None


def _coerce_float(value: Any) -> float | None:
    if value in ("", None):
        return None
    try:
        text = str(value).strip()
        if not text:
            return None
        text = re.sub(r"[^0-9.\-]", "", text)
        if not text or text in {".", "-", "-."}:
            return None
        return float(text)
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

    record["company_name"] = record["company_name"] or normalized_row.get("company_name")
    record["account_id"] = record["account_id"] or normalized_row.get("account_id") or normalized_row.get("id") or record["company_name"]
    record["company_name"] = record["company_name"] or record["account_id"]
    record["_contact_category"] = _pick_value(normalized_row, [_normalize_column_name("contact_category")])
    record["number_of_sites"] = _coerce_int(record["number_of_sites"])
    record["estimated_annual_visits"] = _coerce_int(record["estimated_annual_visits"])
    record["estimated_average_ticket_price"] = _coerce_float(record["estimated_average_ticket_price"])
    record["estimated_transaction_volume"] = _coerce_int(record["estimated_transaction_volume"])
    record["estimated_annual_revenue"] = _coerce_float(record["estimated_annual_revenue"])
    return record


def _contact_category_rank(value: Any) -> int:
    normalized = _normalize_column_name(value)
    if normalized in CONTACT_CATEGORY_PRIORITY:
        return CONTACT_CATEGORY_PRIORITY[normalized]
    if normalized.startswith("ceo") and "managing_director" in normalized:
        return CONTACT_CATEGORY_PRIORITY[_normalize_column_name("CEO / Managing Director")]
    return len(CONTACT_CATEGORY_PRIORITY)


def _row_completeness(row: dict[str, Any]) -> int:
    return sum(1 for key in ALIASES if row.get(key) not in ("", None))


def _first_non_empty_row_value(rows: list[dict[str, Any]], field: str) -> Any:
    for row in rows:
        value = row.get(field)
        if value not in ("", None):
            return value
    return None


def _group_account_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped_rows: list[tuple[str, list[dict[str, Any]]]] = []
    index_by_key: dict[str, int] = {}

    for source_index, row in enumerate(rows, start=1):
        group_key = _normalize_column_name(row.get("account_id") or row.get("company_name") or f"ROW-{source_index}")
        if not group_key:
            group_key = f"row_{source_index}"
        if group_key not in index_by_key:
            index_by_key[group_key] = len(grouped_rows)
            grouped_rows.append((group_key, []))
        grouped_rows[index_by_key[group_key]][1].append({**row, "_source_index": source_index})

    merged_rows: list[dict[str, Any]] = []
    for _, grouped in grouped_rows:
        ordered_rows = sorted(
            grouped,
            key=lambda row: (
                _contact_category_rank(row.get("_contact_category")),
                -_row_completeness(row),
                row.get("_source_index", 0),
            ),
        )

        merged: dict[str, Any] = {}
        for field in ALIASES:
            merged[field] = _first_non_empty_row_value(ordered_rows, field)

        merged["account_id"] = merged["account_id"] or merged["company_name"]
        merged["company_name"] = merged["company_name"] or merged["account_id"]
        merged["number_of_sites"] = _coerce_int(merged["number_of_sites"])
        merged["estimated_annual_visits"] = _coerce_int(merged["estimated_annual_visits"])
        merged["estimated_average_ticket_price"] = _coerce_float(merged["estimated_average_ticket_price"])
        merged["estimated_transaction_volume"] = _coerce_int(merged["estimated_transaction_volume"])
        merged["estimated_annual_revenue"] = _coerce_float(merged["estimated_annual_revenue"])
        merged_rows.append(merged)

    return merged_rows


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


def _load_csv_records_from_text(text: str, source_label: str) -> list[dict[str, Any]]:
    text = text.lstrip("\ufeff")
    try:
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or not any((field or "").strip() for field in reader.fieldnames):
            raise AccountDataMalformedError(f"CSV source '{source_label}' is missing a header row.")
        if not _csv_headers_look_valid(reader.fieldnames):
            raise AccountDataMalformedError(
                f"CSV source '{source_label}' does not contain expected account columns."
            )

        records: list[dict[str, Any]] = []
        for row in reader:
            if not any(value not in ("", None) for value in row.values()):
                continue
            records.append(row)
    except AccountDataError:
        raise
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise AccountDataMalformedError(f"CSV source '{source_label}' could not be read: {exc}") from exc

    if not records:
        raise AccountDataMalformedError(f"CSV source '{source_label}' does not contain any data rows.")
    return records


def _csv_headers_look_valid(fieldnames: list[str]) -> bool:
    normalized_headers = {
        _normalize_column_name(fieldname)
        for fieldname in fieldnames
        if _normalize_column_name(fieldname)
    }
    return bool(normalized_headers & EXPECTED_HEADER_NAMES)


def _google_sheet_csv_url(url: str) -> str:
    parsed = urlparse(url)
    if "docs.google.com" not in parsed.netloc or "/spreadsheets/d/" not in parsed.path:
        return url

    if "/export" in parsed.path and parse_qs(parsed.query).get("format") == ["csv"]:
        return url

    path_parts = [part for part in parsed.path.split("/") if part]
    try:
        sheet_index = path_parts.index("d")
        sheet_id = path_parts[sheet_index + 1]
    except (ValueError, IndexError) as exc:
        raise AccountDataMalformedError(f"Google Sheet URL '{url}' is missing a spreadsheet id.") from exc

    query = parse_qs(parsed.query)
    gid = query.get("gid", ["0"])[0]
    normalized = parsed._replace(
        path=f"/spreadsheets/d/{sheet_id}/export",
        query=urlencode({"format": "csv", "gid": gid}),
    )
    return urlunparse(normalized)


def load_accounts_from_csv_url(url: str) -> list[AccountRecord]:
    normalized_url = _google_sheet_csv_url(url)
    try:
        with urlopen(normalized_url, timeout=15) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            text = response.read().decode(charset, errors="replace")
            content_type = response.headers.get_content_type()
    except URLError as exc:
        raise AccountDataNotFoundError(f"Account data URL '{url}' could not be reached: {exc}") from exc
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise AccountDataMalformedError(f"Account data URL '{url}' could not be read: {exc}") from exc

    if content_type == "text/html" or _looks_like_html(text):
        raise AccountDataMalformedError(
            "Google Sheet URL returned HTML instead of CSV. Ensure the sheet is published as CSV and accessible without login."
        )

    records = _load_csv_records_from_text(text, normalized_url)
    normalized_rows = [_row_from_record(row) for row in records]
    return [normalise_row(row, idx) for idx, row in enumerate(_group_account_rows(normalized_rows), start=1)]


def _looks_like_html(text: str) -> bool:
    snippet = text.lstrip().lower()[:200]
    return snippet.startswith("<!doctype html") or snippet.startswith("<html") or "<html" in snippet


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
    record.pop("_contact_category", None)
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

    normalized_rows = [_row_from_record(row) for row in records]
    return [normalise_row(row, idx) for idx, row in enumerate(_group_account_rows(normalized_rows), start=1)]


def load_accounts_with_metadata(
    *,
    data_path: str | Path | None,
    google_sheet_csv_url: str | None,
) -> AccountLoadResult:
    if google_sheet_csv_url:
        LOGGER.info("Loading account data from Google Sheet CSV URL.")
        try:
            accounts = load_accounts_from_csv_url(google_sheet_csv_url)
            return AccountLoadResult(
                accounts=accounts,
                data_source="google_sheet",
                data_source_detail="Google Sheet CSV URL",
            )
        except AccountDataError as exc:
            warning = (
                "Google Sheet CSV URL failed to load; falling back to bundled sample data. "
                f"Reason: {exc}"
            )
            LOGGER.warning("%s", warning)
            if not DEFAULT_DATA_PATH.is_file():
                raise AccountDataNotFoundError(f"Bundled sample data file '{DEFAULT_DATA_PATH}' does not exist.")
            return AccountLoadResult(
                accounts=load_accounts_from_path(DEFAULT_DATA_PATH),
                data_source="sample_fallback",
                data_source_detail=DEFAULT_DATA_PATH_LABEL,
                data_load_warning=warning,
            )

    if data_path is not None:
        source = Path(data_path)
        if source.is_file():
            LOGGER.info("Loading account data from local file: %s", source)
            return AccountLoadResult(
                accounts=load_accounts_from_path(source),
                data_source="local_file",
                data_source_detail=str(source),
            )
        warning = f"HERMES_DATA_PATH was set but '{source}' is not a valid file; using bundled sample data."
        LOGGER.warning("%s", warning)
    else:
        warning = None

    if not DEFAULT_DATA_PATH.is_file():
        raise AccountDataNotFoundError(f"Bundled sample data file '{DEFAULT_DATA_PATH}' does not exist.")

    LOGGER.info("Loading account data from bundled sample file: %s", DEFAULT_DATA_PATH_LABEL)
    return AccountLoadResult(
        accounts=load_accounts_from_path(DEFAULT_DATA_PATH),
        data_source="sample_fallback",
        data_source_detail=DEFAULT_DATA_PATH_LABEL,
        data_load_warning=warning,
    )


def accounts_to_dataframe(accounts: list[AccountRecord]) -> list[dict[str, Any]]:
    return [account.model_dump() for account in accounts]
