# Release evidence next step

GitHub-hosted jobs currently fail before checkout, so the immediate validation path is the repository-local Windows validator.

Run `scripts/Run-YTIS-Release-Validation.ps1` from a clean checkout of `integration/roadmap-87`.

Expected outcome:

- every Baseline CI command executes in workflow order;
- every Playwright journey executes;
- the real TRACE-aligned UI screenshots are captured;
- individual logs and structured reports are preserved;
- one timestamped review ZIP is created directly in Downloads;
- the repository remains clean after generated artifacts are collected.

Upload that ZIP for visual and technical review. Any demonstrated failure should be corrected from its included log before the validator is repeated.

The local evidence path does not replace the final Windows/Linux GitHub Actions matrix. PR #23 remains draft until hosted jobs execute and pass on the exact merge commit.
