# Evidence-linked architecture review — Opportunity Analysis

**Research question:** Which capabilities, constraints, risks, and next actions are supported by the source pack?

## Review boundary

- Only human-accepted findings are included.
- Opportunity signals remain evidence-backed proposals.

## Opportunity signals

### Local evidence-linked analysis

- Category: `capability`
- Claim: The workbench supports local evidence-linked analysis and JSON persistence.
- Evidence: `source-001:e001`

### Retain evidence in reusable outputs

- Category: `recommendation`
- Claim: Source-qualified evidence should be retained in cards and reports.
- Evidence: `source-002:e002`

## Constraints and risks

### Human review boundary

- Category: `constraint`
- Claim: Human review is required before findings become reusable outputs.
- Evidence: `source-001:e002`

### Provenance loss risk

- Category: `risk`
- Claim: Presenting generated claims without provenance is a major risk.
- Evidence: `source-002:e001`

## Category balance

- capability: 1
- constraint: 1
- recommendation: 1
- risk: 1

## Accepted evidence register

- `finding-001` → `source-001:e001`
- `finding-002` → `source-001:e002`
- `finding-003` → `source-002:e001`
- `finding-004` → `source-002:e002`
