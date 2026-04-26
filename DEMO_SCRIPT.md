# Demo Script

## 5-Minute Walkthrough

### 0:00 to 0:30

Show `GET /health` and explain that Hermes is a production-shaped prototype: it loads structured account data, generates sales material, and keeps outbound actions in a local review queue.

### 0:30 to 1:15

Show `GET /accounts` and `GET /accounts/{account_id}`.

Talking points:

- account data is loaded from a CSV or XLSX file
- column names are normalised into a stable schema
- the backend is designed to work from source records rather than manual copywriting

### 1:15 to 2:15

Show `POST /generate/outreach`.

Talking points:

- the response is deterministic by default
- the message is grounded in the account signal and objective
- the output is brief enough to review quickly
- the copy stays company-neutral and avoids unsupported claims

### 2:15 to 3:15

Show `POST /generate/briefing`.

Talking points:

- the note is structured for sales prep, not for generic summarisation
- it covers company context, persona, opportunity, value, objections, and next step
- the quantified value case is directional and derived from the source data

### 3:15 to 4:00

Show `POST /queue/outreach` and `GET /queue`.

Talking points:

- outbound work is kept in memory only
- the queue is a review step, not a send step
- each item includes the generated message, timestamps, and guardrail flags

### 4:00 to 5:00

Show `POST /export/examples`.

Talking points:

- Hermes generates 3 outreach examples, 2 briefing notes, and 3 queued items
- the export artifacts are easy to inspect and reuse
- the system is designed to be demo-ready without requiring external infrastructure

## What To Show

- health check
- account list
- single account lookup
- outreach generation
- briefing generation
- queue creation
- export bundle generation

## Key Talking Points

- Hermes turns raw account exports into usable sales output
- the prototype is deterministic by default
- the queue is mock-only and safe to run locally
- the copy is grounded in supplied account data
- the app is shaped like a service that could be extended into production

## Trade-Offs Made

- no real sending
- no database
- no CRM integration
- no enrichment pipeline
- no automation scheduler
- no heavy agent dependency by default

## What I Would Improve With More Time

- add persistence for accounts and queue items
- add approval and audit controls
- add richer output templates for different sales motions
- add stronger content testing and reporting
- add observability and operational dashboards
- add a controlled send step with explicit approvals
