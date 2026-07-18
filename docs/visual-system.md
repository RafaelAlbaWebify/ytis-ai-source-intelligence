# YTIS Visual System

YTIS uses the maintained TRACE operational interface as its visual baseline, refined with the dense enterprise layouts shown in the Production Suite and Dashforge references.

## Design objective

The interface must look like a professional local operations and research tool, not a consumer SaaS landing page or a neon AI dashboard.

## Core shell

- Light application canvas: `#f6f8fb`.
- White operational panels.
- Fixed dark navy sidebar using `#071a33` and `#0b2342`.
- Blue primary actions using `#135fca` or `#1976e9`.
- Wide desktop workspace with a compact persistent navigation rail.
- Inter/system UI typography.

## Component rules

- One-pixel slate borders.
- Small-to-medium radii, normally 7–11 px.
- Very restrained panel shadows.
- Compact buttons, fields, badges and table rows.
- Colour is reserved for state and action, not decoration.
- Green means accepted/ready.
- Amber means pending/advisory/missing review.
- Red means rejected/error.
- Blue means action/information.

## Page composition

Primary pages should follow this order:

```text
operational title + short description + primary action
------------------------------------------------------
compact KPI/status row
main register, workbench, table or form panel
secondary details, relationships, history or output
```

## Explicit non-goals

Do not introduce:

- full-page dark mode as the default;
- neon glow or glassmorphism;
- unrelated blue/green/purple/orange feature-card palettes;
- oversized marketing cards;
- invented dashboard statistics;
- decorative gradients across content panels;
- large empty areas where an operational register or table is appropriate.

## Verification

The Start Here Playwright journey checks the rendered visual contract in Chromium:

- light `#f6f8fb` body canvas;
- white operational panels;
- TRACE navy sidebar gradient;
- restrained panel radius;
- all primary navigation journeys;
- visible human-review boundary.

Portfolio screenshots must come from the same commit that passes the complete workflow matrix and is merged.
