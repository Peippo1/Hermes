# Hermes Claude Guide

Use this file if Claude is used on the repository.

## Priorities

- Keep the backend and frontend separated unless a task explicitly crosses the boundary.
- Keep the prototype safe, reviewable, and demo-ready.
- Avoid inventing company-specific claims, competitor names, or unsupported facts.
- Never commit secrets or real API keys.

## Local Environment

- Root `.env` is for backend secrets and should stay untracked.
- `frontend/.env` is for Vite configuration and should stay untracked.
- Example env files should remain placeholder-only.

## Useful References

- `README.md`
- `ARCHITECTURE.md`
- `PRD.md`
- `DEMO_SCRIPT.md`

## Suggested Checks

```bash
python3 -m unittest tests.test_outreach tests.test_briefing tests.test_queue_exports
cd frontend && npm install && npm run build
```

