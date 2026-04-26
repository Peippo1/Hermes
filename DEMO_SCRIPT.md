# Demo Script

## 5-Minute Walkthrough

### 0:00 to 0:30

Show `GET /health`.

Talking points:

- Hermes is a production-shaped prototype
- it loads structured account data from CSV or a Google Sheets export
- it generates outreach and briefing material
- it keeps outbound work in a mock review queue

### 0:30 to 1:15

Show `GET /accounts` and `GET /accounts/{account_id}`.

Talking points:

- account data comes from CSV or XLSX
- column names are normalised into a stable schema
- the backend works from source records rather than manual copywriting

### 1:15 to 2:15

Show `POST /generate/outreach`.

Talking points:

- deterministic generation is the default
- the message follows the account signal and objective
- the output stays short enough to review quickly
- the copy remains company-neutral and avoids unsupported claims

### 2:15 to 3:15

Show `POST /generate/briefing`.

Talking points:

- the note is structured for sales prep, not generic summarisation
- it covers company context, persona, opportunity, value, objections, and next step
- the quantified value case is directional and derived from source data

### 3:15 to 4:00

Show `POST /queue/outreach` and `GET /queue`.

Talking points:

- outbound work stays in memory only
- the queue is a review step, not a send step
- each item includes the generated message, timestamps, and guardrail flags

### 4:00 to 5:00

Show `POST /export/examples`.

Talking points:

- Hermes generates 3 outreach examples, 2 briefing notes, and 3 queued items
- the export artifacts are easy to inspect and reuse
- the system is designed to be demo-ready without external infrastructure

## Local Demo Flow

1. Start the backend.

```bash
python3 -m uvicorn app.main:app --reload
```

2. Start the frontend in a separate terminal.

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

3. Set `VITE_API_BASE_URL` in `frontend/.env` to `http://127.0.0.1:8000` for connected mode, or leave it blank to use mock mode.

4. Walk through the backend endpoints and then show the frontend reacting to the selected account, generated output, queue, and exports.

5. If the backend is unavailable, leave `VITE_API_BASE_URL` unset and continue in mock mode.

## Hosted Demo Flow

1. Use the deployed backend URL from Render.
2. Set `VITE_API_BASE_URL` in the deployed frontend to the Render URL.
3. Open the Vercel site and show the same account, outreach, briefing, queue, and export flow.

## Fallback If Backend Is Unavailable

- The frontend switches to mock mode when `VITE_API_BASE_URL` is missing.
- The frontend also falls back to mock mode if the backend is unavailable or a request fails.
- The UI surfaces the fallback in the status panel so the demo can continue without interruption.
- The workflow stays usable without blocking the rest of the demo.

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
- frontend falls back to mock mode instead of blocking the demo

## Productionisation Plan

- CRM integration
- authenticated users
- audit logs
- approval workflow
- observability
- cost tracking
- CRM / Sheets write-back
- persistent storage for accounts, queue items, and generated artifacts
- controlled delivery channels only after explicit approval
- richer output templates for different sales motions
- stronger content testing and reporting

## What I Would Improve With More Time

- add persisted queue state and history
- add richer guardrails around tone and claims
- add better observability and tracing
- add controlled scheduling for follow-up tasks
- add more output variants for different commercial motions
