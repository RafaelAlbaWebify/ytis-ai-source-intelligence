# YTIS - Your Technical Intelligence System

YTIS is a local-first AI source intelligence workbench for applied AI and GenAI application portfolio work.

The goal is not to replace ChatGPT or to build a black-box AI product. YTIS is the local control layer around source material, evidence extraction, provider workflows, human review, saved investigations, reusable insight cards and reviewed report generation.

## What YTIS does

YTIS turns public-safe source material into structured learning and decision-support outputs.

Current capabilities include:

- typed multi-source investigation packs;
- stable source IDs, editing, ordering and provenance-qualified evidence;
- safe local UTF-8 text and Markdown import;
- a version-stable Local Source Import page that creates saved investigations;
- deterministic no-network public-reference metadata capture;
- transcript collection, cleaning and source-pack generation;
- deterministic and replaceable structured finding providers;
- human review of evidence-linked findings;
- local investigation persistence and reopen;
- reusable accepted-finding insight cards with explicit actions;
- an Insight Card Library with advisory exact relationships;
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

## Operational interface

YTIS follows the maintained TRACE operational visual system rather than a dark neon AI-dashboard style:

- light grey canvas and white operational panels;
- fixed TRACE navy sidebar;
- restrained blue, green, amber and red state colours;
- compact KPI rows, registers, forms and status badges;
- thin borders, modest radii and minimal decoration.

See `docs/visual-system.md` for the enforced visual contract and explicit non-goals.

## Run locally

```bash
python -m ytis.app
```

Open `/start` for the focused onboarding page. It links to the four primary paths while preserving every specialist route in the sidebar.

Useful routes:

- `/start` — choose the demo, local import, full workbench or card library;
- `/technical-research` — full source-pack, review, card and report workbench;
- `/local-source-import` — import a local `.txt`, `.md` or `.markdown` path, analyze it and save the investigation;
- `/insight-cards` — inspect persisted cards and advisory exact relationships;
- `/demo` — smallest deterministic public-safe journey.

The path-based local import control intentionally avoids relying on incompatible NiceGUI 2.x and 3.x upload APIs while the repository still permits NiceGUI 2.x. The hardened importer remains responsible for extension, UTF-8, size, path and symlink validation.

## How ChatGPT fits

YTIS is not the reasoning model. ChatGPT or another explicitly configured provider can support synthesis, while YTIS controls source preparation, structured boundaries, evidence provenance, review status, persistence and reusable outputs. The deterministic offline provider remains the default and CI fixture.

## Safety boundaries

YTIS is for public-safe research and learning workflows. It does not access restricted content, process private customer data, automatically accept findings or present AI output as certain fact. Human review is always required.

See `docs/safety-boundaries.md` for the full boundary model.

## Focused public demo

The `/demo` route uses one built-in public-safe source and produces four evidence-linked findings with exact provenance and pending human-review status. It requires no uploads, credentials, network access, provider configuration, telemetry or persistence.

See `docs/public-demo.md` for the expected result and automated browser evidence.

## Inspectable portfolio example

`examples/portfolio-investigation/` contains committed source files, a complete reviewed investigation, a reusable insight card and representative outputs for all five report templates. The Windows/Linux baseline validates grounding, exact source offsets, card linkage, report evidence coverage and the human-review boundary.

## Verification

The cross-platform CI baseline and its explicit limits are documented in `docs/ci-baseline.md`. Browser workflows retain screenshots, traces, server logs and structured JSON check reports.

When GitHub-hosted runners are unavailable, `scripts/Run-YTIS-Release-Validation.ps1` runs the exact baseline commands and all browser journeys on a clean Windows checkout, then creates one evidence ZIP directly in Downloads. See `docs/local-release-validation.md`. This fallback supports diagnosis and visual review but does not replace the final Windows/Linux CI gate.

## Release status

YTIS `v1.0.0` is the first public portfolio release. It is a completed local-first portfolio MVP, not a mature autonomous AI platform or a replacement for human research judgment.

See `docs/roadmap.md` for possible future development.
