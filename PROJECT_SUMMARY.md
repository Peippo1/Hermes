# PROJECT SUMMARY

Hermes is a production-shaped prototype for AI sales enablement in the experience commerce and location-based entertainment space. It ingests account data, turns that data into personalised outreach and briefing content, and presents the output through a lightweight frontend with a mock outbound queue and export/report flows. The system is designed to demonstrate a realistic workflow from account list to draft outreach, briefing notes, and reviewable queue items, while keeping sending and review safely controlled.

## What Is Implemented

- Google Sheet / CSV account ingestion, with local CSV/XLSX fallback support
- FastAPI backend for account, outreach, briefing, queue, and export endpoints
- Deterministic outreach generation by default
- Deterministic briefing generation by default
- Mock outbound queue for review-only workflow simulation
- Report/export layer for outreach, briefing, queue, and summary artifacts
- Optional OpenAI live generation behind an environment flag
- Vercel frontend for the demo experience
- Render backend for hosted API deployment

## How The Workflows Map To The Brief

- Personalised outreach: Hermes generates account-specific outreach drafts using company signals, contact details, and value propositions. This maps directly to the personalised outreach requirement.
- Outbound send automation / mock queue: Hermes simulates a send workflow through a local-only queue. Items are created, reviewed, and exported, but no real messages are sent.
- Meeting briefing notes: Hermes generates structured briefing notes with company context, opportunity framing, talking points, objections, and directional value estimates for sales preparation.

## Guardrails

- No real sending
- Human review before any outbound action
- Deterministic fallback when live generation is unavailable
- No unsupported claims
- Directional estimates only

## Intentionally Out Of Scope

- CRM write-back
- Google Sheets write-back
- LinkedIn/email sending
- Authentication and role-based access control
- Production database

## Production Next Steps

- CRM integration
- Authenticated users
- Audit logs
- Approval workflow
- Observability
- Cost tracking
- CRM / Sheets write-back
