# YTIS - Your Technical Intelligence System

YTIS is my local-first AI source intelligence workbench for AI Developer / GenAI Application Developer portfolio work.

I built YTIS as my AIDE flagship:

- AIDE -> YTIS -> AI Developer / GenAI Application Developer

The goal is not to replace ChatGPT or to build a black-box AI product. YTIS is the local control layer around source material, evidence extraction, provider workflows, human review, saved investigations, reusable insight cards and reviewed report generation.

## What YTIS does

YTIS turns public-safe source material into structured learning and decision-support outputs.

Current working capabilities include:

- typed multi-source investigation packs;
- stable source IDs, editing, ordering and provenance-qualified evidence;
- safe local UTF-8 text and Markdown import at the domain boundary;
- transcript collection, cleaning and source-pack generation;
- deterministic and replaceable structured finding providers;
- human review of evidence-linked findings;
- local investigation persistence and reopen;
- reusable accepted-finding insight cards with explicit actions;
- advisory related-card detection using exact claims and shared evidence;
- accepted-only Markdown and complete JSON exports;
- five reviewed report templates;
- advisory duplicate-source detection;
- privacy-safe opt-in local provider telemetry;
- a focused deterministic browser demo.

YouTube transcripts were the first ingestion path, not the full product definition. The Technical Research Workbench also supports technical notes, pasted text, article notes, document notes, job descriptions, transcripts and generic public-safe text.

## Core workflow

```text
source pack
→ evidence extraction
→ grounded findings
→ human review
→ saved investigation
→ reusable insight cards
→ reviewed reports
```

Every reusable card and reviewed report is derived only from accepted findings that retain exact source-qualified evidence IDs.

## How ChatGPT fits

YTIS is not the reasoning model. ChatGPT or another explicitly configured provider can support synthesis, while YTIS controls source preparation, structured boundaries, evidence provenance, review status, persistence and reusable outputs. The deterministic offline provider remains the default and CI fixture.

## Safety boundaries

YTIS is for public-safe research and learning workflows. It does not access restricted content, does not process private customer data, does not automatically accept findings, and does not present AI output as certain fact. Human review is always required.

See `docs/safety-boundaries.md` for the full boundary model.

## Focused public demo

Run the app and open `/demo` for the smallest complete YTIS journey:

```bash
python -m ytis.app
```

The demo uses one built-in public-safe source and produces four evidence-linked findings with exact provenance and pending human-review status. It requires no uploads, credentials, network access, provider configuration, telemetry or persistence.

See `docs/public-demo.md` for the expected result and automated browser evidence.

## Inspectable portfolio example

`examples/portfolio-investigation/` contains committed source files, a complete reviewed investigation, a reusable insight card and representative outputs for all five report templates. The Windows/Linux baseline validates grounding, exact source offsets, card linkage, report evidence coverage and the human-review boundary.

## Full workflow

A typical end-to-end workflow is documented in `docs/sample-workflow.md`.

## Verification

The current cross-platform CI baseline and its explicit limits are documented in `docs/ci-baseline.md`. Browser workflows retain screenshots, traces, server logs and structured JSON check reports.

The final merge and publication gate is documented in `docs/publication-review.md`.

## Current status

YTIS is a working local portfolio MVP. It is private-first and should not be treated as a mature autonomous AI platform.

## Roadmap

See `docs/roadmap.md`.
