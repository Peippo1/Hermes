# Architecture

## System Overview

Hermes is a FastAPI backend that loads account data, normalises it into typed records, and generates deterministic outreach and briefing content for commercial demo use.

The system is shaped like a production service, but it keeps the operational risk low by:

- running locally by default
- keeping outbound activity in memory only
- using deterministic generation unless live-agent mode is explicitly enabled
- failing fast when the source data is invalid

## Data Flow

1. The app reads a CSV or XLSX file from `data/` or `HERMES_DATA_PATH`.
2. `app.data_loader` normalises columns into `AccountRecord` models.
3. `app.main` exposes the loaded records through account endpoints.
4. `app.workflows` resolves the target account and builds outreach or briefing content.
5. `app.agents` produces the deterministic copy and the live-agent placeholder path.
6. `app.send_queue` stores outbound drafts in memory only.
7. `app.exporters` writes CSV, JSON, and Markdown artifacts for review.

## Endpoint List

- `GET /health`
- `GET /accounts`
- `GET /accounts/{account_id}`
- `POST /generate/outreach`
- `POST /generate/briefing`
- `POST /queue/outreach`
- `GET /queue`
- `POST /export/examples`

## Agent and Workflow Design

The generator split is deliberately small:

- `app.agents` contains the deterministic content builders
- `app.workflows` selects accounts and orchestrates content generation
- live-agent mode uses the same workflow entry points, but the placeholder branches still fall back to local deterministic output

This keeps the service predictable while leaving a clean integration point for a future model-backed implementation.

## Guardrails

- Use only fields present in the account record
- Avoid fabricated named competitors or public claims
- Keep directional estimates clearly labelled
- Keep outreach under the configured length limit
- Keep the queue local and review-only
- Fail fast when the data file is missing or malformed

## Mock Send Queue

The queue is an in-memory list of `QueueItem` records. Each queued item includes:

- a generated `queue_id`
- the originating `account_id`
- the `company_name`
- contact details where available
- the selected channel
- the message body
- selected value props
- `pending_review` status
- creation and follow-up timestamps
- guardrail flags

This is intentionally not a delivery system. It is a review queue for demo flow and later expansion.

## Production Considerations

- Add persistence for accounts, queue items, and generated artifacts
- Add authentication and authorization
- Add audit logging and traceability
- Add approval controls before any outbound send action
- Add monitoring and operational alerting
- Add retry and scheduling for follow-up work
- Add source enrichment only after review and control points are in place
- Add formal content testing for tone, claims, and length
