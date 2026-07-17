# Portfolio Investigation Example

This folder is a committed, public-safe example of the YTIS research workflow.

## Contents

- `source-architecture.md` and `source-delivery.md`: the exact source texts;
- `investigation.json`: typed sources, evidence ranges, grounded findings, and human review decisions;
- `insight-card.json`: a reusable action created from an accepted finding;
- `source-credibility.md`: provenance and coverage without an autonomous credibility score;
- `business-model.md`: evidence-backed business signals and risks;
- `technical-lessons.md`: capabilities, constraints, risks and recommendations;
- `learning-roadmap.md`: evidence-backed learning priorities;
- `opportunity-analysis.md`: opportunity signals balanced against constraints and risks.

## Traceability

Every finding cites a source-qualified evidence ID. Evidence offsets are zero-based and use an exclusive end position, so each recorded evidence text can be reproduced directly from its source content.

The cross-platform `portfolio_example_smoke.py` proof reloads the investigation through the real repository, validates grounding, checks every offset against the original source text, validates the insight card schema, and confirms that all five reports retain every evidence ID and the human-review boundary.

## Safety boundary

The example contains no private data, network fetching, API credentials, autonomous acceptance, or unsupported credibility score. The review decisions are explicit fixture data for portfolio demonstration.
