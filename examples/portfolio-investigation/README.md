# Portfolio Investigation Example

This folder is a committed, public-safe example of the YTIS research workflow.

## Contents

- `source-architecture.md` and `source-delivery.md`: the exact source texts;
- `investigation.json`: typed sources, evidence ranges, grounded findings, and human review decisions;
- `insight-card.json`: a reusable action created from an accepted finding;
- `technical-lessons.md`: a reviewed report containing only accepted grounded findings.

## Traceability

Every finding cites a source-qualified evidence ID. Evidence offsets are zero-based and use an exclusive end position, so each recorded evidence text can be reproduced directly from its source content.

## Safety boundary

The example contains no private data, network fetching, API credentials, autonomous acceptance, or unsupported credibility score. The review decisions are explicit fixture data for portfolio demonstration.
