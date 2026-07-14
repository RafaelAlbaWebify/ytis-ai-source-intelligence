# CI Baseline

This document records what the initial GitHub-based baseline proves and what it deliberately does not prove.

## Verified on clean GitHub runners

The `Baseline CI` workflow runs on:

- Ubuntu latest with Python 3.12;
- Windows latest with Python 3.12.

It verifies:

- declared runtime dependencies install successfully;
- `pip check` finds no broken dependency relationships;
- Python sources compile;
- the existing publication-positioning check passes;
- `ytis.app` imports;
- all current `ytis.core` and `ytis.ui` modules import;
- navigation labels and routes are unique;
- an empty `AppState` can initialize and load an empty project registry;
- the existing transactional source builder completes an offline fixture workflow;
- duplicate rolling-caption text is collapsed;
- transcript index, combined Markdown, prompt, summary, registry, and ZIP are generated;
- the generated ZIP passes integrity and required-content checks.

## Architecture observations

The characterization report currently records broad exception handlers as warnings rather than failures. These warnings are evidence for later targeted refactoring; they must not be removed blindly because some handlers may be intentional recovery boundaries.

The verified baseline confirms that the source-pack core is reusable. It does not yet establish that the higher-level intelligence, mission, knowledge-card, or browser workflows are correct.

## Not yet verified

- launching and serving the complete NiceGUI application in CI;
- rendering every route in a browser;
- browser console and network-error monitoring;
- mission lifecycle behavior;
- saved-analysis and knowledge-card persistence;
- claim-to-evidence grounding;
- structured extraction or classification quality;
- LLM-provider integration;
- PDF or multi-source ingestion;
- accessibility and responsive UX;
- performance with large source packs.

## Next proof layer

The next safe layer is browser smoke testing with Playwright against deterministic local fixture data. It should visit each registered route, detect unhandled browser errors, and retain screenshots and traces without introducing product behavior changes.
