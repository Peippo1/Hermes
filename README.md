# Hermes

Hermes is a FastAPI prototype for sales enablement in experience commerce and location-based entertainment.

It supports:

- loading target accounts from a CSV or spreadsheet export
- generating personalised outreach drafts
- generating pre-meeting briefing notes
- queueing outreach drafts in a mock outbound send queue
- exporting outputs as CSV, JSON, and Markdown

## Principles

- Orchestration stays deterministic in Python.
- Agent-backed generation is reserved for judgement-heavy drafting.
- Structured outputs are modelled with Pydantic.
- Guardrails prevent fabricated claims and real sending.

## Project Layout

- `app/main.py`
- `app/config.py`
- `app/models.py`
- `app/data_loader.py`
- `app/agents.py`
- `app/workflows.py`
- `app/send_queue.py`
- `app/exporters.py`
- `prompts/`
- `outputs/`
- `README.md`
- `PRD.md`
- `ARCHITECTURE.md`

## Run

```bash
python -m uvicorn app.main:app --reload
```

By default, the app loads sample accounts from `outputs/sample_accounts.csv`. You can point it at a different CSV or spreadsheet export with `HERMES_DATA_PATH`.

## Optional live agent path

The code includes a single toggle for live agent-backed generation. If the key is available and live mode is enabled, the app can route generation through an SDK adapter; otherwise it uses deterministic mock generation.

Set these environment variables in a local `.env` file:

```bash
HERMES_USE_LIVE_AGENTS=true
AGENT_API_KEY=your_key_here
```

If no key is available, the prototype stays fully functional with mock generation.

## API

- `GET /health`
- `GET /accounts`
- `POST /generate/outreach`
- `POST /generate/briefing`
- `POST /queue/outreach`
- `GET /queue`
- `POST /export/examples`

## Sample flow

1. Load accounts from the sample export.
2. Generate outreach or briefing notes for selected account IDs.
3. Queue outreach drafts in the mock send layer.
4. Export generated examples for review.

## Notes

- The send queue is in-memory only.
- No real delivery integrations are implemented.
- The sample outputs in `outputs/` are generated from fictional account rows for safe testing.

