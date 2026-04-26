from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.data_loader import AccountDataNotFoundError
from app.models import OutreachDraft
from app.send_queue import SendQueue
from tests.test_support import load_test_app_module


class QueueAndExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.main_module = load_test_app_module()
        cls.client = TestClient(cls.main_module.app)

    def setUp(self) -> None:
        self.main_module.app.state.runtime.queue = SendQueue()

    def test_queue_outreach_creates_pending_review_item(self) -> None:
        response = self.client.post("/queue/outreach", json={"account_id": "ACCT-001"})
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        item = payload["item"]
        self.assertEqual(item["status"], "pending_review")
        self.assertIn("queue_id", item)
        self.assertEqual(item["account_id"], "ACCT-001")
        self.assertEqual(item["company_name"], "Northstar Leisure Group")
        self.assertIn("selected_value_props", item)
        self.assertIn("guardrail_flags", item)
        self.assertEqual(payload["queue_size"], 1)

        queue_response = self.client.get("/queue")
        self.assertEqual(queue_response.status_code, 200)
        queue_payload = queue_response.json()
        self.assertEqual(queue_payload["queue_size"], len(queue_payload["items"]))
        self.assertEqual(queue_payload["items"][0]["status"], "pending_review")

    def test_health_and_data_source_report_sample_fallback(self) -> None:
        health_response = self.client.get("/health")
        self.assertEqual(health_response.status_code, 200)
        health_payload = health_response.json()
        self.assertEqual(health_payload["data_source"], "local_file")
        self.assertEqual(health_payload["data_source_detail"], str(self.main_module.config.data_path))
        self.assertIsNone(health_payload["data_load_warning"])
        self.assertEqual(health_payload["loaded_accounts"], 3)

        data_source_response = self.client.get("/data-source")
        self.assertEqual(data_source_response.status_code, 200)
        data_source_payload = data_source_response.json()
        self.assertEqual(data_source_payload["data_source"], "local_file")
        self.assertEqual(data_source_payload["loaded_accounts"], 3)

    def test_empty_data_path_falls_back_to_sample_file(self) -> None:
        temp_config = replace(self.main_module.config, data_path=Path(""))
        runtime = self.main_module.RuntimeState.__new__(self.main_module.RuntimeState)
        with patch("app.main.config", temp_config):
            runtime.__init__()
        self.assertGreater(len(runtime.accounts), 0)
        self.assertEqual(runtime.accounts[0].account_id, "ACCT-001")
        self.assertEqual(runtime.data_source, "sample_fallback")
        self.assertEqual(runtime.data_source_detail, "data/sample_accounts.csv")

    def test_google_sheet_csv_url_falls_back_to_sample_file_when_unreachable(self) -> None:
        temp_config = replace(
            self.main_module.config,
            data_path=Path(""),
            google_sheet_csv_url="https://docs.google.com/spreadsheets/d/example/export?format=csv&gid=0",
        )
        runtime = self.main_module.RuntimeState.__new__(self.main_module.RuntimeState)
        with patch("app.main.config", temp_config), patch(
            "app.data_loader.load_accounts_from_csv_url",
            side_effect=AccountDataNotFoundError("Google Sheet unavailable"),
        ) as mock_load:
            runtime.__init__()
        self.assertEqual(mock_load.call_count, 1)
        self.assertGreater(len(runtime.accounts), 0)
        self.assertEqual(runtime.accounts[0].account_id, "ACCT-001")
        self.assertEqual(runtime.data_source, "sample_fallback")
        self.assertEqual(runtime.data_source_detail, "data/sample_accounts.csv")

    def test_queue_outreach_does_not_send_externally(self) -> None:
        draft = OutreachDraft(
            account_id="ACCT-002",
            company_name="Harbor Experience Co",
            contact_name="Mina Patel",
            contact_role="Head of Growth",
            selected_value_props=["Support commercial consistency across 1 site"],
            business_insight="Test",
            estimated_impact="Test",
            message="Hi Mina, this is a local-only queue test.",
            guardrail_flags=[],
            channel="email",
            tone="concise",
        )
        with patch("app.workflows.generate_outreach") as mock_generate:
            mock_generate.return_value = draft
            response = self.client.post("/queue/outreach", json={"account_id": "ACCT-002"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(mock_generate.call_count, 1)
            self.assertEqual(response.json()["item"]["status"], "pending_review")
            self.assertEqual(len(self.main_module.app.state.runtime.queue.items), 1)

    def test_export_examples_creates_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_config = replace(self.main_module.config, generated_dir=Path(tmpdir))
            with patch("app.main.config", temp_config):
                response = self.client.post("/export/examples")
                self.assertEqual(response.status_code, 200)

                payload = response.json()
                self.assertEqual(len(payload["outreach"]), 3)
                self.assertEqual(len(payload["briefings"]), 2)

                artifacts = payload["artifacts"]
                expected_paths = [
                    Path(artifacts["outreach_csv_path"]),
                    Path(artifacts["outreach_json_path"]),
                    Path(artifacts["briefing_note_1_path"]),
                    Path(artifacts["briefing_note_2_path"]),
                    Path(artifacts["send_queue_path"]),
                ]
                for path in expected_paths:
                    self.assertTrue(path.exists(), msg=str(path))

                self.assertEqual(Path(artifacts["outreach_csv_path"]).name, "outreach_examples.csv")
                self.assertEqual(Path(artifacts["outreach_json_path"]).name, "outreach_examples.json")
                self.assertEqual(Path(artifacts["briefing_note_1_path"]).name, "briefing_note_1.md")
                self.assertEqual(Path(artifacts["briefing_note_2_path"]).name, "briefing_note_2.md")
                self.assertEqual(Path(artifacts["send_queue_path"]).name, "send_queue.json")

                send_queue = json.loads(Path(artifacts["send_queue_path"]).read_text(encoding="utf-8"))
                self.assertEqual(len(send_queue), 3)
                self.assertIn("queue_id", send_queue[0])

    def test_export_report_creates_expected_files(self) -> None:
        self.client.post("/queue/outreach", json={"account_id": "ACCT-001"})

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_config = replace(self.main_module.config, generated_dir=Path(tmpdir))
            with patch("app.main.config", temp_config):
                response = self.client.post("/export/report")
                self.assertEqual(response.status_code, 200)

                payload = response.json()
                report = payload["report"]
                self.assertEqual(report["summary_counts"]["outreach_examples"], 3)
                self.assertEqual(report["summary_counts"]["queued_outreach_items"], 1)

                artifacts = payload["artifacts"]
                report_md = Path(artifacts["report_md_path"])
                report_json = Path(artifacts["report_json_path"])
                self.assertTrue(report_md.exists())
                self.assertTrue(report_json.exists())
                self.assertEqual(report_md.name, "outreach_report.md")
                self.assertEqual(report_json.name, "outreach_report.json")

                saved = json.loads(report_json.read_text(encoding="utf-8"))
                self.assertEqual(len(saved["generated_outreach_examples"]), 3)
                self.assertEqual(len(saved["queued_outreach_items"]), 1)
                self.assertIn("generated_at", saved)


if __name__ == "__main__":
    unittest.main()
