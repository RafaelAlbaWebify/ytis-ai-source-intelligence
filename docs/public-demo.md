# YTIS Public Demo

The `/demo` route is the smallest complete YTIS product journey.

It demonstrates:

1. A built-in public-safe source.
2. Deterministic sentence-level evidence extraction.
3. Evidence-linked capability, constraint, risk and recommendation findings.
4. Exact source IDs, evidence IDs and character ranges.
5. Explicit pending human-review status.

The demo intentionally does not use:

- network access;
- uploads;
- API credentials;
- provider configuration;
- local persistence;
- telemetry;
- automatic finding acceptance.

## Run locally

```bash
python -m ytis.app
```

Open `http://127.0.0.1:8080/demo` and select **Analyze demo source**.

## Expected result

The deterministic fixture produces four evidence units and four findings. Every finding cites its exact evidence unit and remains marked as pending human review.

## Automated evidence

The `Playwright Public Demo` workflow verifies the complete browser journey and retains:

- a full-page screenshot;
- a Playwright trace;
- the application server log;
- a structured JSON check report.
