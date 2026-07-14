# UI Baseline

This document records the first automated browser and visual baseline for YTIS.

## Automated route proof

The Playwright route smoke test launches the real NiceGUI application in Chromium and visits every route defined by the current navigation model.

Verified results:

- 15 navigation routes checked;
- all routes returned HTTP 200;
- no browser console errors;
- no unhandled page errors;
- no server-side 5xx responses;
- no `module not available` fallback pages;
- one full-page screenshot captured per route;
- a Playwright trace retained for diagnosis.

## Visual observations

The current UI has a consistent dark visual language, reusable cards, a stable sidebar shell, and generally clear page headings. The application no longer appears to be failing at basic route rendering.

The main remaining UX problem is product focus rather than visual breakage:

- the sidebar exposes a large number of destinations for the current maturity level;
- several routes are empty-state control panels when no project is selected;
- related concepts are split across missions, analysis, evidence, intelligence, knowledge, radar, and expert-intelligence pages;
- the dashboard presents many possible next actions instead of one dominant investigation workflow;
- administrative tools such as Repair, Health, and Prompt Builder are mixed into the primary product navigation;
- users must understand internal YTIS concepts before they can complete a useful source-to-report workflow.

## Interpretation

The interface is technically renderable and visually coherent. It is not yet evidence that the complete product workflow is simple or valuable.

The next UX objective should not be a cosmetic redesign. It should be to prove and simplify one end-to-end workflow:

`create/select source -> inspect evidence -> run structured analysis -> review findings -> generate report`

## Still unverified

- navigation through visible UI controls rather than direct URLs;
- project selection persistence across pages;
- source build form submission;
- mission creation and progression;
- saved-analysis persistence;
- knowledge-card creation;
- report generation from reviewed findings;
- responsive behavior;
- accessibility and keyboard navigation.
