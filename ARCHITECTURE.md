# Architecture

## Overview

Hermes uses deterministic Python orchestration for loading, filtering, queueing, and exporting. Agent-backed generation is isolated behind a small adapter so the rest of the system remains predictable.

## Layers

### API Layer

`app/main.py` exposes the FastAPI application and route handlers.

### Configuration Layer

`app/config.py` reads environment variables and resolves file paths.

### Data Layer

`app/data_loader.py` loads account rows from CSV or spreadsheet exports and normalises them into Pydantic records.

### Generation Layer

`app/agents.py` contains the fallback drafting logic and the live-agent switch point.

### Workflow Layer

`app/workflows.py` selects accounts, builds outputs, and queues outbound drafts.

### Queue Layer

`app/send_queue.py` stores queued drafts in memory only.

### Export Layer

`app/exporters.py` writes CSV, JSON, and Markdown artifacts.

## Data Flow

1. Load account rows.
2. Normalise them into records.
3. Generate outreach or briefing notes.
4. Optionally queue outreach drafts.
5. Export outputs for review.

## Guardrails

- Use only supplied fields for personalisation.
- Do not invent metrics or partnerships.
- Use tentative language where data is sparse.
- Never send real messages from the prototype.

## Live Agent Path

The live path is intentionally narrow. It should only be used for judgement-heavy text generation while Python keeps control over account selection, queueing, validation, and export.

