# Next Vertical Slice

## Purpose

The repository now has automated proof for installation, module imports, the transactional source-pack builder, route rendering, and visible sidebar navigation.

The next milestone must prove product value rather than add more pages.

## Proposed slice

`select a deterministic source project -> inspect source evidence -> create structured findings -> review findings -> generate a report`

## User-visible outcome

A user can open one public-safe fixture project, see traceable source material, produce structured findings linked to that material, review or reject those findings, and export a Markdown and JSON report.

## Required domain concepts

- Investigation
- Source
- Evidence unit
- Finding
- Classification
- Review decision
- Report

These concepts should have explicit validated fields and should not be represented only by unrelated page-specific dictionaries.

## Proof before implementation

Automatic proof should establish:

- deterministic fixture import;
- stable source and evidence identifiers;
- schema validation for findings;
- every finding references at least one evidence identifier;
- rejected findings are excluded from the final report;
- approved findings appear in Markdown and JSON exports;
- data persists across application restart;
- Playwright can complete the workflow using visible controls;
- no network or paid LLM dependency is required for the deterministic CI path.

## Architecture boundary

The slice should use an application service independent of NiceGUI:

`UI -> application service -> domain model -> repository/provider adapters`

The NiceGUI pages should render state and invoke explicit operations. They should not own extraction, classification, persistence, and report-generation logic directly.

## Non-goals

- autonomous agents;
- arbitrary web crawling;
- paid LLM calls in required CI;
- cloud deployment;
- vector database adoption without measured retrieval need;
- broad UI redesign;
- repository rename;
- support for every source type.

## Product decision required before implementation

Choose the first real fixture scenario. Strong candidates are:

1. technical-source research;
2. support/incident evidence analysis;
3. job-description and skills-gap analysis;
4. vendor or product comparison.

The architecture can remain generic, but the first workflow and report must be optimized for one concrete daily-use scenario rather than a vague universal intelligence platform.
