# Product Requirements Document

## Problem

Commercial teams working in experience commerce and location-based entertainment often spend too much time turning account data into usable sales material. Source information arrives as exports, spreadsheets, or partial notes, and the preparation work for outreach and meetings is repetitive and inconsistent.

## Users

- Sales reps preparing outreach and follow-up
- Commercial managers reviewing account opportunities
- Sales operations teams standardising workflows
- Stakeholders reviewing sample outputs and process quality

## Goals

- Load account data from CSV or XLSX files
- Normalise source columns into a stable account schema
- Generate deterministic outreach drafts from account records
- Generate briefing notes for sales meetings
- Queue outreach locally for review before any send step
- Export example outputs for review and iteration

## Non-Goals

- Real sending
- CRM synchronization
- Authentication and role management
- Automated enrichment
- Scheduling or automation of follow-ups
- Persistent storage

## Core Workflows

1. Load accounts from a file in `data/`
2. Review the account list through `GET /accounts`
3. Open a single account with `GET /accounts/{account_id}`
4. Generate outreach with `POST /generate/outreach`
5. Generate a briefing with `POST /generate/briefing`
6. Queue outreach through `POST /queue/outreach`
7. Review the queue with `GET /queue`
8. Export sample outputs with `POST /export/examples`

## Success Metrics

- Account data loads successfully from valid CSV and XLSX files
- Outreach drafts stay grounded in the source account data
- Briefing notes include the required sales sections and directional estimates
- Queue items remain local and reviewable
- Export artifacts are generated reliably
- The demo flow is understandable without additional explanation

## Guardrails

- Do not invent named competitors or public claims
- Do not invent metrics that are not derived from the account record
- Keep outreach and briefing language company-neutral
- Keep the queue as a mock review step only
- Fail fast when the account file is missing or malformed
- Label estimates as directional when exact values are not known

## Future Improvements

- Add persistent storage for accounts, queue items, and generated artifacts
- Add authenticated access and role-based controls
- Add audit logging and observability
- Add approval workflows before any external send action
- Add follow-up scheduling and retry logic
- Add source enrichment and quality scoring
- Add better document templating for team-specific use cases
