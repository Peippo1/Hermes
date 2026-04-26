# Hermes

Hermes is a production-shaped FastAPI prototype for AI sales enablement in the experience commerce and location-based entertainment market.

It helps teams turn account lists into:

- personalised outreach drafts
- pre-meeting briefing notes
- a local mock outbound queue
- reviewable export artifacts

## What Problem It Solves

Commercial teams often have account data scattered across exports, spreadsheets, CRM notes, and manual research. That makes it slow to prepare outreach, prep for meetings, and create consistent follow-up material.

Hermes reduces that work by:

- loading account data from CSV or XLSX
- normalising the source columns into a consistent schema
- generating deterministic outreach and briefing content from the same source record
- keeping outbound work in a mock review queue
- exporting examples for review and iteration

## Run Locally

```bash
python3 -m uvicorn app.main:app --reload
```

By default, Hermes loads `data/sample_accounts.csv`.

To use a different CSV or XLSX file:

```bash
export HERMES_DATA_PATH=/path/to/accounts.csv
python3 -m uvicorn app.main:app --reload
```

The app fails fast at startup if the data file is missing or malformed.

Live-agent mode is optional. The backend remains deterministic by default.

```bash
export HERMES_USE_LIVE_AGENTS=true
export OPENAI_API_KEY=your_key_here
export HERMES_MODEL=gpt-4.1-mini
```

## Frontend

The repo includes a lightweight Vite + React + TypeScript frontend in `frontend/`.

Run it locally:

```bash
cd frontend
npm install
npm run dev
```

If the backend is running on another origin, set:

```bash
cp .env.example .env
```

Then update `VITE_API_BASE_URL` in `frontend/.env` to the backend base URL, for example:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

If `VITE_API_BASE_URL` is missing, the UI switches to demo mock mode and uses local sample data.

## Render Deploy

To deploy the backend on Render:

1. Create a new Render web service.
2. Connect the GitHub repository.
3. Set the build command to `pip install -r requirements.txt`.
4. Set the start command to `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
5. Add environment variables:
   - `OPENAI_API_KEY` if live-agent mode will be used
   - `HERMES_USE_LIVE_AGENTS=false`
   - `HERMES_MODEL=gpt-4.1-mini`
   - `CORS_ORIGINS` with the frontend origin, such as the local Vite URL and the eventual Vercel URL
   - `HERMES_DATA_PATH` only if you want to override the bundled sample export
6. Set the health check path to `/health`.

The backend starts with the bundled sample data by default, so no extra database setup is required for the first deployment.

## Vercel Deploy

To deploy the frontend to Vercel:

1. Import the repository into Vercel.
2. Set the project root to `frontend`.
3. Add `VITE_API_BASE_URL` as an environment variable if you want the deployed UI to call a backend API.
4. Use the default Vite build command, `npm run build`.
5. Use the default output directory, `dist`.

If you deploy the frontend without a backend URL, it still runs in mock mode for demos.

## Demo Walkthrough

1. Check the app is ready.

```bash
curl http://127.0.0.1:8000/health
```

2. List loaded accounts.

```bash
curl http://127.0.0.1:8000/accounts
```

3. Inspect a single account.

```bash
curl http://127.0.0.1:8000/accounts/ACCT-001
```

4. Generate outreach.

```bash
curl -X POST http://127.0.0.1:8000/generate/outreach \
  -H 'Content-Type: application/json' \
  -d '{"account_id":"ACCT-001"}'
```

5. Generate a briefing.

```bash
curl -X POST http://127.0.0.1:8000/generate/briefing \
  -H 'Content-Type: application/json' \
  -d '{"account_id":"ACCT-001","meeting_persona":"Commercial Director","focus":"commercial"}'
```

6. Queue outreach.

```bash
curl -X POST http://127.0.0.1:8000/queue/outreach \
  -H 'Content-Type: application/json' \
  -d '{"account_id":"ACCT-001"}'
```

7. Export examples.

```bash
curl -X POST http://127.0.0.1:8000/export/examples
```

## What Outputs Are Generated

- `GET /accounts` returns the normalised account records.
- `POST /generate/outreach` returns a structured outreach draft.
- `POST /generate/briefing` returns a structured briefing note with markdown and supporting fields.
- `POST /queue/outreach` adds a local queue item with follow-up timestamps and guardrail flags.
- `GET /queue` returns the current queue contents and queue size.
- `POST /export/examples` writes `outputs/outreach_examples.csv`, `outputs/outreach_examples.json`, `outputs/briefing_note_1.md`, `outputs/briefing_note_2.md`, and `outputs/send_queue.json`.

The export bundle contains 3 outreach examples, 2 briefing notes, and 3 queued outreach items.

## Current Limitations

- No real outbound sending
- No persistent database
- No authentication or role-based access control
- No CRM synchronization
- No scheduler for follow-up automation
- No enrichment from external systems
- No observability stack beyond the API surface

## Productionisation Plan

- Add authentication and access control
- Move accounts, queue items, and generated artifacts into persistent storage
- Add audit logging and traceability
- Integrate approved delivery channels with explicit send controls
- Add retry, scheduling, and follow-up workflows
- Expand test coverage around loader edge cases and content quality
- Add observability and operational alerting
- Layer in enrichment only after source fidelity and approval flows are in place

## API Surface

- `GET /health`
- `GET /accounts`
- `GET /accounts/{account_id}`
- `POST /generate/outreach`
- `POST /generate/briefing`
- `POST /queue/outreach`
- `GET /queue`
- `POST /export/examples`

## Notes

Hermes is intentionally narrow. The goal is to keep the prototype production-shaped enough to be credible in a commercial demo, while still being deterministic, reviewable, and safe to run locally.
