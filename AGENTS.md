# Hermes Agent Guide

This file is the root compatibility alias for agent tooling.

## Core Rules

- Keep wording company-neutral.
- Do not add real sending, real outbound automation, or hidden side effects.
- Do not place secrets in tracked files.
- Keep backend and frontend changes separate unless the task explicitly spans both.
- Prefer deterministic behavior by default.
- Preserve API schemas unless the user explicitly asks for a change.

## Secrets

- Root `.env` is for local backend secrets only.
- `frontend/.env` is for frontend runtime config only.
- Example env files must stay placeholder-only.

## Useful Commands

```bash
python3 -m unittest tests.test_outreach tests.test_briefing tests.test_queue_exports
python3 -m uvicorn app.main:app --reload
cd frontend && npm install && npm run build
```

