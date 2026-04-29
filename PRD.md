# Hermes PRD

## Problem Definition

Commercial teams in experience commerce and location-based entertainment spend time turning messy account data into outreach and meeting prep. Inputs arrive as Google Sheets CSV exports, local CSV/XLSX files, or partial notes. The work is repetitive, needs review, and is easy to make inconsistent.

Hermes addresses that gap with a deterministic-first workflow that produces usable sales material from the same account record, while keeping human review in the loop and avoiding real outbound side effects.

## Users / Personas

- Sales reps who need outreach drafts and meeting briefs
- Commercial managers who want a quick read on account context
- Sales operations or revenue operations users who need consistent outputs
- Demo reviewers or interviewers evaluating workflow quality and safety

## Goals

- Ingest account data from Google Sheets CSV exports or local CSV/XLSX files
- Normalize source columns into a stable account schema
- Generate deterministic outreach drafts by default
- Generate meeting briefing notes from the same source record
- Simulate a reviewable outbound queue without real sending
- Export demo artifacts as CSV, JSON, and Markdown
- Surface data-source diagnostics and fallback behavior clearly
- Keep the system easy to test and iterate on with pytest and a TDD-style loop

## Non-Goals

- Real outbound sending
- Authentication or role-based access control
- CRM integration or CRM write-back
- Google Sheets write-back
- Persistent database storage
- Automated scheduling or retry infrastructure
- External enrichment pipelines
- Hidden side effects

## Core Workflows

1. Load account data from the bundled sample file, a local override, or a Google Sheet CSV export.
2. Normalize source headers and merge duplicate or partially populated rows into a usable account record.
3. Review loaded accounts through the API and inspect data-source metadata.
4. Generate outreach drafts from an account record.
5. Generate briefing notes from the same account record and meeting context.
6. Add a draft to the mock queue for human review.
7. Export sample outputs for review as CSV, JSON, and Markdown.
8. Fall back to deterministic output if live generation is disabled or unavailable.

## System Overview

- Data source layer: loads Google Sheet CSV exports, local CSV/XLSX files, or bundled sample data
- Data loader layer: normalizes headers, coerces metrics, groups account/contact rows, and records source diagnostics
- Generation layer: produces outreach and briefing content from account records
- Guardrail layer: limits unsupported claims, keeps language grounded in source data, and flags fallback conditions
- Queue layer: stores outbound items locally for review only
- Export layer: writes demo artifacts for outreach, briefing, queue, and reporting flows
- Live AI path: optional and env-gated; deterministic generation remains the default

## Design Principles

- Deterministic-first: the default path should be repeatable and reviewable
- Human review before action: queue items are mock review artifacts, not sent messages
- Safe AI usage: live generation is optional, gated, and expected to fall back cleanly
- Source fidelity: outputs should stay grounded in the loaded account record
- Minimal surface area: keep behavior narrow and avoid adding new system dependencies
- Testability: keep workflow logic easy to cover with automated tests and fixture-based inputs
- Low surprise: data-source diagnostics and fallback behavior should be explicit

## Guardrails / Safety Model

- No real sending
- No hidden outbound automation
- No CRM or Sheets write-back
- No authentication or privileged user flows
- No invented competitors or unsupported claims
- Directional estimates only when exact values are not known
- Fallback to deterministic output when live generation is disabled or fails
- External environment variables are cleared in tests to keep behavior deterministic
- Queue items remain review-only and local to the application

## Success Metrics

- Valid CSV and XLSX files load successfully
- Google Sheet CSV exports normalize consistently
- Outreach and briefing outputs stay grounded in the source data
- Optional live generation falls back cleanly when unavailable
- Queue items are created, reviewed, and exported without real sending
- Export artifacts are generated reliably in repeatable test runs
- pytest and unittest coverage continue to pass in CI and locally
- The workflow is understandable in a demo without extra explanation

## Future Improvements

- Add authenticated access and role-based controls
- Add CRM integration after the prototype stage
- Add audit logging and observability
- Add approval workflows before any external delivery action
- Add follow-up scheduling and retry logic
- Add source enrichment and quality scoring
- Add persistent storage for accounts, queue items, and generated artifacts
- Add more template variants for team-specific workflows
