from __future__ import annotations

import textwrap
import unittest
from unittest.mock import patch

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


class DataLoaderTests(unittest.TestCase):
    def test_load_accounts_from_csv_url_normalises_account_and_contact_fields(self) -> None:
        csv_text = textwrap.dedent(
            """\
            Account Name,Category,Sub-Category,Description,HQ Location,Sites,Est. Annual Visits,Region,Est. Avg Ticket Price ($),Est. Total Transaction Volume ($),Est. Easol Annual Revenue ($),Contact Name,Contact Title,Contact Category
            NQ64,Competitive Socialising,Arcade Bar,Retro arcade bar with classic games and craft drinks,Manchester,"10","1,500,000",UK,"8","12,000,000","420,000",James Palmer,Head of Partnerships,Commercial
            NQ64,Competitive Socialising,Arcade Bar,Retro arcade bar with classic games and craft drinks,Manchester,"10","1,500,000",UK,"8","12,000,000","420,000",Aisha Hall,Co-Founder & CEO,CEO / Managing Director
            NQ64,Competitive Socialising,Arcade Bar,Retro arcade bar with classic games and craft drinks,Manchester,"10","1,500,000",UK,"8","12,000,000","420,000",Adam Osei,Operations Director,Operations
            """
        )

        with patch("app.data_loader.urlopen", return_value=_FakeResponse(csv_text)) as mock_urlopen:
            accounts = load_accounts_from_csv_url("https://docs.google.com/spreadsheets/d/example/export?format=csv&gid=0")

        self.assertEqual(mock_urlopen.call_count, 1)
        self.assertEqual(len(accounts), 1)

        account = accounts[0]
        self.assertEqual(account.account_id, "NQ64")
        self.assertEqual(account.company_name, "NQ64")
        self.assertEqual(account.category, "Competitive Socialising")
        self.assertEqual(account.sub_category, "Arcade Bar")
        self.assertEqual(account.description, "Retro arcade bar with classic games and craft drinks")
        self.assertEqual(account.hq_location, "Manchester")
        self.assertEqual(account.number_of_sites, 10)
        self.assertEqual(account.estimated_annual_visits, 1500000)
        self.assertEqual(account.estimated_average_ticket_price, 8.0)
        self.assertEqual(account.estimated_transaction_volume, 12000000)
        self.assertEqual(account.estimated_annual_revenue, 420000.0)
        self.assertEqual(account.region, "UK")
        self.assertEqual(account.contact_name, "James Palmer")
        self.assertEqual(account.contact_role, "Head of Partnerships")


if __name__ == "__main__":
    unittest.main()
