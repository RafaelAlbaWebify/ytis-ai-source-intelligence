# YTIS Publication Readiness Review

This document defines the evidence required before the consolidated roadmap branch can be merged or presented as the current portfolio release.

## Reviewer entry points

1. `README.md` — product purpose, workflow, safety boundaries and verification summary.
2. `/demo` — smallest deterministic browser journey.
3. `/technical-research` — complete source-to-reviewed-output workbench.
4. `/local-source-import` — version-stable local text/Markdown ingestion into a saved investigation.
5. `/insight-cards` — persisted reusable cards and advisory exact relationships.
6. `examples/portfolio-investigation/` — inspectable source, investigation, card and five report templates.
7. `docs/roadmap.md` — completed capabilities and remaining polish.
8. `docs/safety-boundaries.md` — non-goals and human-review constraints.

## Required merge evidence

The pull request must not merge until all jobs execute and pass:

- Windows and Linux baseline;
- route smoke;
- visible navigation interaction;
- technical research workbench;
- multi-source workbench;
- source-pack editing workbench;
- reusable outputs workbench;
- local source import and insight card library;
- structured provider workbench;
- provider configuration guard;
- local telemetry workbench;
- public demo.

A workflow result with no checkout step, no logs and `steps: None` is an infrastructure failure, not successful validation.

## Required browser artifacts

Successful browser jobs must retain, where configured:

- final full-page screenshot;
- Playwright trace;
- application server log;
- structured JSON check report.

Screenshots used in portfolio material must come from a successful workflow run for the same commit that is merged.

## Safety review

Before publication, confirm:

- no credentials or tokens are committed;
- no private customer or employer data appears in fixtures or screenshots;
- all example inputs are public-safe or synthetic;
- findings are not automatically accepted;
- cards and reviewed reports use accepted grounded findings only;
- source credibility reports do not invent an autonomous score;
- duplicate and related-source/card handling remains advisory;
- local-path import remains limited to explicit user-selected UTF-8 text and Markdown files;
- telemetry contains metadata only and remains opt-in/local;
- no network source fetching is enabled by default.

## Portfolio quality review

Confirm that a reviewer can understand, without repository archaeology:

- the source → evidence → finding → review → card/report workflow;
- the distinction between deterministic offline behavior and replaceable providers;
- exact provenance through source IDs, evidence IDs and offsets;
- local persistence boundaries;
- the focused demo versus the full workbench;
- the local import and card-library routes;
- the current limitations and non-goals.

## Current release blocker

GitHub Actions jobs are still completing before checkout with no executable steps. PR #23 must remain draft and unmerged until the full matrix actually runs and passes.
