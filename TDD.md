# Hermes TDD Workflow

Purpose:
Ensure safe iteration on AI workflow logic using test-driven development.

Principles:
- Test behavior via public API endpoints
- Do not test internal implementation
- Deterministic outputs must be stable under test

Workflow:
1. Write failing test (RED)
2. Implement minimal change (GREEN)
3. Refactor safely

Focus areas:
- outreach generation
- briefing generation
- queue behavior
- data loading + fallback
- live-agent fallback

Rules:
- one behavior per test
- no speculative features
- tests must survive refactors
