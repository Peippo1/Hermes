from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.agents import build_briefing_markdown
from app.models import AccountRecord
from tests.test_support import load_test_app_module


class BriefingEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.main_module = load_test_app_module()
        cls.client = TestClient(cls.main_module.app)

    def test_generate_briefing_default(self) -> None:
        response = self.client.post(
            "/generate/briefing",
            json={"account_id": "ACCT-001", "meeting_persona": "Commercial Director", "focus": "commercial"},
        )
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["account_id"], "ACCT-001")
        self.assertEqual(payload["company_name"], "Northstar Leisure Group")
        self.assertEqual(payload["contact_name"], "Avery Hughes")
        self.assertEqual(payload["contact_role"], "Commercial Director")
        self.assertIn("briefing_markdown", payload)
        self.assertIn("opportunity_summary", payload)
        self.assertIn("quantified_value_case", payload)
        self.assertIn("talking_points", payload)
        self.assertIn("likely_objections", payload)
        self.assertIn("recommended_next_step", payload)
        self.assertIn("guardrail_flags", payload)
        self.assertEqual(payload["guardrail_flags"], [])
        self.assertGreaterEqual(len(payload["talking_points"]), 4)
        self.assertGreaterEqual(len(payload["likely_objections"]), 3)

        markdown = payload["briefing_markdown"]
        required_sections = [
            "# Meeting Brief: Northstar Leisure Group",
            "## 1. Company Overview",
            "## 2. Individual / Persona Profile",
            "## 3. Opportunity Analysis",
            "## 4. Quantified Value Case",
            "## 5. Suggested Talking Points",
            "## 6. Likely Objections",
            "## 7. Competitive / Systems Context",
            "## 8. Recommended Next Step",
        ]
        for section in required_sections:
            self.assertIn(section, markdown)

    def test_generate_briefing_missing_account(self) -> None:
        response = self.client.post("/generate/briefing", json={"account_id": "MISSING"})
        self.assertEqual(response.status_code, 404)

    def test_generate_briefing_no_fake_competitors(self) -> None:
        response = self.client.post("/generate/briefing", json={"account_id": "ACCT-002", "focus": "operations"})
        self.assertEqual(response.status_code, 200)

        markdown = response.json()["briefing_markdown"]
        forbidden_names = [
            "Salesforce",
            "HubSpot",
            "Zendesk",
            "Oracle",
            "Microsoft",
            "SAP",
            "Adobe",
        ]
        for name in forbidden_names:
            self.assertNotIn(name, markdown)

    def test_generate_briefing_uses_richer_metrics(self) -> None:
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

        note = build_briefing_markdown(account, focus="commercial")

        self.assertIn("For a Head of Partnerships", note.briefing_markdown)
        self.assertIn("10 sites", note.briefing_markdown)
        self.assertIn("1.5m annual visits", note.briefing_markdown)
        self.assertIn("$12m", note.briefing_markdown)
        self.assertIn("Objection: We already have a process for this.", note.briefing_markdown)
        self.assertIn("Response: Acknowledge the current process", note.briefing_markdown)
        self.assertIn("Use the first call to choose one journey to inspect", note.recommended_next_step)
        self.assertIn("25% conversion uplift value proposition", note.quantified_value_case)
        self.assertNotIn("For a Competitive Socialising lead", note.briefing_markdown)


if __name__ == "__main__":
    unittest.main()
