from __future__ import annotations

import unittest
from dataclasses import replace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.models import BriefingNote, OutreachDraft
from tests.test_support import load_test_app_module


class LiveAgentModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.main_module = load_test_app_module()
        cls.client = TestClient(cls.main_module.app)

    def test_generate_outreach_uses_live_mode_when_enabled(self) -> None:
        live_draft = OutreachDraft(
            account_id="ACCT-001",
            company_name="Northstar Leisure Group",
            contact_name="Avery Hughes",
            contact_role="Commercial Director",
            selected_value_props=["Support commercial consistency across 8 sites"],
            business_insight="Live mode draft",
            estimated_impact="Live mode draft",
            message="Hi Avery, Northstar is opening a new venue soon. For an 8-site footprint, the focus is still drive pre-opening bookings and memberships. A lighter workflow could help the team keep outreach and follow-up tight. Worth a quick look?",
            guardrail_flags=[],
            channel="email",
            tone="concise",
        )
        temp_config = replace(self.main_module.config, use_live_agents=True, openai_api_key="sk-test", model_name="gpt-4.1-mini")

        with patch("app.main.config", temp_config), patch("app.workflows.generate_live_outreach", return_value=live_draft) as mock_live:
            response = self.client.post("/generate/outreach", json={"account_id": "ACCT-001"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["message"], live_draft.message)
        self.assertEqual(payload["guardrail_flags"], [])
        mock_live.assert_called_once()

    def test_generate_briefing_falls_back_when_live_generation_fails(self) -> None:
        temp_config = replace(self.main_module.config, use_live_agents=True, openai_api_key="sk-test", model_name="gpt-4.1-mini")

        with patch("app.main.config", temp_config), patch("app.workflows.generate_live_briefing", side_effect=RuntimeError("boom")):
            response = self.client.post("/generate/briefing", json={"account_id": "ACCT-002", "focus": "growth"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("Live briefing generation failed; fell back to deterministic output.", payload["guardrail_flags"])
        self.assertIn("# Meeting Brief: Harbor Experience Co", payload["briefing_markdown"])
        self.assertIn("## 1. Company Overview", payload["briefing_markdown"])


if __name__ == "__main__":
    unittest.main()
