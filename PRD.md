# Product Requirements Document

## Overview

Hermes is a workflow prototype for sales enablement teams working across experience commerce and location-based entertainment.

## Goals

1. Load target account data from CSV or spreadsheet exports.
2. Generate personalised outreach for selected accounts.
3. Generate pre-meeting briefing notes for selected accounts.
4. Add generated outreach to a mock outbound queue.
5. Export generated outputs as CSV, JSON, and Markdown.

## Non-Goals

- Real email delivery
- Real social message delivery
- Contact enrichment
- CRM sync
- Scheduling automation

## User Stories

- As a sales operator, I want to import accounts so I can work from a shared list.
- As a sales operator, I want outreach drafts that reflect the source data without hallucinated claims.
- As a sales operator, I want a briefing note before a meeting so I can prepare quickly.
- As a reviewer, I want generated content to remain in a mock queue until approved.
- As a stakeholder, I want exportable examples for review and iteration.

## Requirements

- Accept CSV and spreadsheet exports.
- Support account selection by account ID.
- Use structured outputs for all generated content.
- Preserve guardrails around tone, evidence, and source fidelity.
- Keep queue operations in memory only.
- Provide export artifacts for generated examples.

## Acceptance Criteria

- The health endpoint reports the app is ready.
- The accounts endpoint returns loaded records.
- Outreach generation returns structured drafts.
- Briefing generation returns structured notes.
- Queueing stores items only in the mock queue.
- Exporting writes CSV, JSON, and Markdown artifacts.
