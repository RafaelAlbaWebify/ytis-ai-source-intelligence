# Multi-source investigation slice

The Technical Research Workbench should treat an investigation as a source pack rather than a single text field.

## Required behavior

- Stage two or more public-safe technical sources before analysis.
- Assign stable source IDs in insertion order (`source-001`, `source-002`, ...).
- Preserve each source title and content separately.
- Analyze the complete source pack in one provider execution.
- Keep every evidence unit linked to its originating source ID.
- Save and reopen the complete source pack.
- Preserve source provenance in Markdown and JSON reports.
- Keep human review and approved-only report behavior unchanged.

## Safety boundaries

- No network fetching.
- No automatic source discovery.
- No provider-controlled persistence or reporting.
- No automatic acceptance of findings.
