from __future__ import annotations

import textwrap

from app.agents import build_briefing_markdown, build_outreach_draft
from app.data_loader import load_accounts_from_csv_url


class _FakeHeaders:
    def get_content_charset(self) -> str:
        return "utf-8"

    def get_content_type(self) -> str:
        return "text/csv"


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self._payload = text.encode("utf-8")
        self.headers = _FakeHeaders()

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


def test_load_accounts_from_csv_url_normalises_metrics_and_contact_fields(monkeypatch) -> None:
    csv_text = textwrap.dedent(
        """\
        Account Name,Category,Sub-Category,Description,HQ Location,Sites,Est. Annual Visits,Region,Est. Avg Ticket Price ($),Est. Total Transaction Volume ($),Est. Easol Annual Revenue ($),Contact Name,Contact Title,Contact Category
        NQ64,Competitive Socialising,Arcade Bar,Retro arcade bar with classic games and craft drinks,Manchester,"10","1,500,000",UK,"8","12,000,000","420,000",James Palmer,Head of Partnerships,Commercial
        """
    )

    monkeypatch.setattr("app.data_loader.urlopen", lambda *args, **kwargs: _FakeResponse(csv_text))

    accounts = load_accounts_from_csv_url("https://docs.google.com/spreadsheets/d/example/export?format=csv&gid=0")

    assert len(accounts) == 1
    account = accounts[0]
    assert account.account_id == "NQ64"
    assert account.company_name == "NQ64"
    assert account.number_of_sites == 10
    assert account.estimated_annual_visits == 1500000
    assert account.estimated_average_ticket_price == 8.0
    assert account.estimated_transaction_volume == 12000000
    assert account.contact_name == "James Palmer"
    assert account.contact_role == "Head of Partnerships"


def test_nq64_style_input_maps_expected_fields_and_supports_generation(monkeypatch) -> None:
    csv_text = textwrap.dedent(
        """\
        account name,sites,annual visits,average ticket price,transaction volume,contact name,contact title
        NQ64,10,"1,500,000",8,"12,000,000",James Palmer,Head of Partnerships
        """
    )

    monkeypatch.setattr("app.data_loader.urlopen", lambda *args, **kwargs: _FakeResponse(csv_text))

    account = load_accounts_from_csv_url("https://docs.google.com/spreadsheets/d/example/export?format=csv&gid=0")[0]
    outreach = build_outreach_draft(account, channel="email", tone="concise")
    briefing = build_briefing_markdown(account, focus="commercial")

    assert outreach.account_id == "NQ64"
    assert "10-site footprint" in outreach.message
    assert "1.5m annual visits" in outreach.message
    assert "Head of Partnerships" in outreach.message
    assert briefing.contact_name == "James Palmer"
    assert "10 sites" in briefing.briefing_markdown
    assert "1.5m annual visits" in briefing.briefing_markdown


def test_missing_optional_fields_do_not_crash_generation(monkeypatch) -> None:
    csv_text = textwrap.dedent(
        """\
        Account Name,Contact Name,Contact Title
        Minimal Co,Alex Reed,Commercial Director
        """
    )

    monkeypatch.setattr("app.data_loader.urlopen", lambda *args, **kwargs: _FakeResponse(csv_text))

    account = load_accounts_from_csv_url("https://docs.google.com/spreadsheets/d/example/export?format=csv&gid=0")[0]
    outreach = build_outreach_draft(account, channel="linkedin", tone="warm")
    briefing = build_briefing_markdown(account, focus="commercial")

    assert account.company_name == "Minimal Co"
    assert outreach.message
    assert briefing.briefing_markdown
    assert "Minimal Co" in outreach.message
    assert "Minimal Co" in briefing.briefing_markdown
