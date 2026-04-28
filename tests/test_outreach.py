from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.agents import build_outreach_draft
from app.models import AccountRecord
from tests.test_support import load_test_app_module


class OutreachEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.main_module = load_test_app_module()
        cls.client = TestClient(cls.main_module.app)

    def assert_no_internal_wording(self, message: str) -> None:
        lowered = message.lower()
        forbidden_phrases = [
            "account record",
            "source-backed tokens",
            "guardrails",
            "internal data",
        ]
        for phrase in forbidden_phrases:
            self.assertNotIn(phrase, lowered)

    def test_generate_outreach_default(self) -> None:
        response = self.client.post("/generate/outreach", json={"account_id": "ACCT-001"})
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        message = payload["message"]
        self.assertEqual(payload["account_id"], "ACCT-001")
        self.assertEqual(payload["company_name"], "Northstar Leisure Group")
        self.assertIn("contact_name", payload)
        self.assertIn("contact_role", payload)
        self.assertIn("selected_value_props", payload)
        self.assertIn("business_insight", payload)
        self.assertIn("estimated_impact", payload)
        self.assertIn("message", payload)
        self.assertIn("guardrail_flags", payload)
        self.assertLessEqual(len(message.split()), 100)
        self.assert_no_internal_wording(message)
        self.assertNotIn("priority is usually", message.lower())
        self.assertNotIn("we can help turn", message.lower())
        self.assertEqual(payload["guardrail_flags"], [])
        self.assertIn("drive pre-opening bookings and memberships", message)
        self.assertNotIn("increase repeat visits and off-peak demand", message)
        self.assertNotIn("grow weekday group bookings", message)

    def test_generate_outreach_with_channel_and_tone(self) -> None:
        response = self.client.post(
            "/generate/outreach",
            json={"account_id": "ACCT-002", "channel": "linkedin", "tone": "warm"},
        )
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        message = payload["message"]
        self.assertEqual(payload["account_id"], "ACCT-002")
        self.assertEqual(payload["company_name"], "Harbor Experience Co")
        self.assertLessEqual(len(message.split()), 100)
        self.assert_no_internal_wording(message)
        self.assertNotIn("priority is usually", message.lower())
        self.assertIn("increase repeat visits and off-peak demand", message)
        self.assertNotIn("drive pre-opening bookings and memberships", message)
        self.assertNotIn("grow weekday group bookings", message)
        self.assertEqual(payload["guardrail_flags"], [])

    def test_generate_outreach_uses_each_account_objective(self) -> None:
        objectives = {
            "ACCT-001": "drive pre-opening bookings and memberships",
            "ACCT-002": "increase repeat visits and off-peak demand",
            "ACCT-003": "grow weekday group bookings",
        }

        for account_id, expected_objective in objectives.items():
            with self.subTest(account_id=account_id):
                response = self.client.post("/generate/outreach", json={"account_id": account_id})
                self.assertEqual(response.status_code, 200)

                message = response.json()["message"]
                self.assertLessEqual(len(message.split()), 100)
                self.assertIn(expected_objective, message)
                for other_account_id, other_objective in objectives.items():
                    if other_account_id == account_id:
                        continue
                    self.assertNotIn(other_objective, message)

    def test_generate_outreach_missing_account(self) -> None:
        response = self.client.post("/generate/outreach", json={"account_id": "MISSING"})
        self.assertEqual(response.status_code, 404)

    def test_generate_outreach_uses_richer_metrics(self) -> None:
        account = AccountRecord(
            account_id="NQ64",
            company_name="NQ64",
            category="Competitive Socialising",
            sub_category="Arcade Bar",
            description="Retro arcade bar with classic games and craft drinks",
            hq_location="Manchester",
            number_of_sites=10,
            estimated_annual_visits=1500000,
            estimated_average_ticket_price=8,
            estimated_transaction_volume=12000000,
            estimated_annual_revenue=420000,
            region="UK",
            contact_name="James Palmer",
            contact_role="Head of Partnerships",
        )

        draft = build_outreach_draft(account, channel="email", tone="concise")

        self.assertIn("Head of Partnerships", draft.message)
        self.assertIn("10-site footprint", draft.message)
        self.assertIn("1.5m annual visits", draft.message)
        self.assertIn("$12m", draft.message)
        self.assertNotIn("moving through a practical growth phase", draft.message)
        self.assertNotIn("A cleaner workflow can help", draft.message)


if __name__ == "__main__":
    unittest.main()
