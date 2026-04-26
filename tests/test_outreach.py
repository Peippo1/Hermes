from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.main import app


class OutreachEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

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
        self.assertEqual(payload["account_id"], "ACCT-001")
        self.assertEqual(payload["company_name"], "Northstar Leisure Group")
        self.assertIn("contact_name", payload)
        self.assertIn("contact_role", payload)
        self.assertIn("selected_value_props", payload)
        self.assertIn("business_insight", payload)
        self.assertIn("estimated_impact", payload)
        self.assertIn("message", payload)
        self.assertIn("guardrail_flags", payload)
        self.assertLessEqual(len(payload["message"].split()), 100)
        self.assert_no_internal_wording(payload["message"])
        self.assertNotIn("priority is usually", payload["message"].lower())
        self.assertNotIn("we can help turn", payload["message"].lower())
        self.assertEqual(payload["guardrail_flags"], [])
        self.assertIn("Northstar", payload["message"])
        self.assertTrue(
            "bookings" in payload["message"].lower() or "memberships" in payload["message"].lower()
        )

    def test_generate_outreach_with_channel_and_tone(self) -> None:
        response = self.client.post(
            "/generate/outreach",
            json={"account_id": "ACCT-002", "channel": "linkedin", "tone": "warm"},
        )
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["account_id"], "ACCT-002")
        self.assertEqual(payload["company_name"], "Harbor Experience Co")
        self.assertLessEqual(len(payload["message"].split()), 100)
        self.assert_no_internal_wording(payload["message"])
        self.assertNotIn("priority is usually", payload["message"].lower())
        self.assertEqual(payload["guardrail_flags"], [])

    def test_generate_outreach_missing_account(self) -> None:
        response = self.client.post("/generate/outreach", json={"account_id": "MISSING"})
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
