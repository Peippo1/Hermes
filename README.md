# Hermes

Hermes is a FastAPI prototype for sales enablement in experience commerce and location-based entertainment.

It is built to demo a simple flow:

1. Load accounts from a CSV or XLSX export.
2. Generate one structured outreach draft for a selected account.
3. Generate one markdown briefing note for a selected account.
4. Add outreach to a local mock queue.
5. Export sample outputs for review.

## What is included

- `GET /health`
- `GET /accounts`
- `GET /accounts/{account_id}`
- `POST /generate/outreach`
- `POST /generate/briefing`
- `POST /queue/outreach`
- `GET /queue`
- `POST /export/examples`

## Run

```bash
python3 -m uvicorn app.main:app --reload
```

The app loads account data from `data/sample_accounts.csv` by default. To use your own export, set `HERMES_DATA_PATH` to a CSV or XLSX file.

If the configured file is missing or malformed, the app stops at startup with a clear error message.

Live agent-backed generation is optional. The prototype works without an API key and stays deterministic by default.

```bash
export HERMES_USE_LIVE_AGENTS=true
export AGENT_API_KEY=your_key_here
```

## Test the accounts endpoints

With the server running, check the loaded accounts:

```bash
curl http://127.0.0.1:8000/accounts
```

Inspect one account by id:

```bash
curl http://127.0.0.1:8000/accounts/ACCT-001
```

If you point `HERMES_DATA_PATH` at a bad file, the app will fail fast before serving requests. That makes data issues obvious during startup instead of surfacing later in the demo.

## Demo script

### 1. Start with the accounts

Open `GET /accounts` first and show that the file loader normalises the source export into:

- `company_name`
- `category`
- `sub_category`
- `description`
- `hq_location`
- `number_of_sites`
- `estimated_annual_visits`
- `estimated_average_ticket_price`
- `estimated_transaction_volume`
- `estimated_annual_revenue`
- `region`

Then open `GET /accounts/{account_id}` for one of the returned ids to show a single account record.

### 2. Show outreach generation

Call `POST /generate/outreach` with one `account_id`. Point out that the response is structured JSON with:

- `persona`
- `role_reasoning`
- `selected_value_props`
- `business_insight`
- `estimated_impact`
- `message`
- `risk_flags`

### 3. Show the briefing note

Call `POST /generate/briefing` for the same account and show the markdown sections:

- company overview
- individual/persona profile
- value case
- quantified impact
- talking points
- likely objections
- competitive context
- recommended next step

### 4. Queue the outreach

Call `POST /queue/outreach` and show that the item is stored locally with:

- `account`
- `persona`
- `channel`
- `message`
- `status = pending_review`
- `created_at`
- `follow_up_day_3`
- `follow_up_day_7`

### 5. Export examples

Call `POST /export/examples` to produce the sample files in `outputs/`:

- `outreach_examples.csv`
- `outreach_examples.json`
- `briefing_note_1.md`
- `briefing_note_2.md`
- `send_queue.json`

## Trade-offs

- Orchestration stays in Python so the demo is predictable.
- Agents are only used for the judgement-heavy drafting path.
- The send queue is mock-only, so there is no delivery risk.
- The data model is intentionally small and opinionated to keep the demo readable.

## What productionisation would require

- Authentication and role-based access control
- Persistent storage for accounts, drafts, and queue state
- Real delivery integrations with approval workflows
- Observability, logging, and audit trails
- Automated tests for loader, validation, and export behavior
- Better source validation and account enrichment
- Retry and scheduling infrastructure for follow-up handling
