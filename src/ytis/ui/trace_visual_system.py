from __future__ import annotations

from nicegui import ui


def install_trace_visual_system() -> None:
    """Install the shared light operational visual system used by TRACE.

    The selectors intentionally have higher specificity than the legacy inline
    dark-theme rules in ``layout.py`` so existing pages can migrate without a
    risky all-at-once renderer rewrite.
    """

    ui.add_head_html(
        """
        <style id="ytis-trace-visual-system">
        :root,
        html body {
            --ytis-bg: #f6f8fb;
            --ytis-surface: #ffffff;
            --ytis-surface-soft: #f7f9fc;
            --ytis-border: #e1e6ee;
            --ytis-border-strong: #cfd7e3;
            --ytis-text: #172033;
            --ytis-text-secondary: #5f6b80;
            --ytis-text-muted: #7b8799;
            --ytis-navy-950: #071a33;
            --ytis-navy-900: #0b2342;
            --ytis-blue-700: #135fca;
            --ytis-blue-600: #1976e9;
            --ytis-blue-100: #e8f2ff;
            --ytis-green-700: #287a4a;
            --ytis-green-100: #e7f6ed;
            --ytis-amber-700: #95620d;
            --ytis-amber-100: #fff3d6;
            --ytis-red-700: #a63c35;
            --ytis-red-100: #fdebea;
            --ytis-radius-sm: 7px;
            --ytis-radius-md: 11px;
            --ytis-shadow-panel: 0 1px 2px rgba(16, 34, 61, .04), 0 8px 24px rgba(16, 34, 61, .045);
        }

        html body,
        html body .q-layout,
        html body .q-page-container,
        html body .q-page,
        html body .nicegui-content {
            background: var(--ytis-bg) !important;
            color: var(--ytis-text) !important;
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
        }

        html body .ytis-page {
            max-width: 1600px !important;
            padding: 28px 32px 48px !important;
            color: var(--ytis-text) !important;
            overflow-x: visible !important;
        }

        html body .ytis-header {
            min-height: 48px !important;
            padding: 0 20px 0 10px !important;
            background: rgba(255, 255, 255, .97) !important;
            border-bottom: 1px solid var(--ytis-border) !important;
            color: var(--ytis-text) !important;
            box-shadow: none !important;
            backdrop-filter: none !important;
        }

        html body .ytis-sidebar {
            top: 48px !important;
            background: linear-gradient(180deg, var(--ytis-navy-950), var(--ytis-navy-900)) !important;
            border-right: 1px solid rgba(255, 255, 255, .06) !important;
            box-shadow: 1px 0 0 rgba(16, 34, 61, .08) !important;
        }

        html body .ytis-brand-title { color: #ffffff !important; font-size: 19px !important; }
        html body .ytis-brand-subtitle { color: #cbd5e1 !important; font-size: 10px !important; }
        html body .ytis-nav-group { color: rgba(255, 255, 255, .46) !important; }
        html body .ytis-nav-button,
        html body .ytis-nav-rail-button { color: rgba(255, 255, 255, .86) !important; }
        html body .ytis-nav-button:hover,
        html body .ytis-nav-rail-button:hover {
            background: rgba(255, 255, 255, .075) !important;
            color: #ffffff !important;
        }
        html body .ytis-nav-active {
            background: var(--ytis-blue-600) !important;
            border: 1px solid rgba(255, 255, 255, .08) !important;
            color: #ffffff !important;
            box-shadow: none !important;
        }
        html body .ytis-current-project-box { border-color: rgba(255, 255, 255, .10) !important; }
        html body .ytis-current-project-box .text-slate-500 { color: rgba(255, 255, 255, .45) !important; }
        html body .ytis-current-project-box .text-slate-300 { color: rgba(255, 255, 255, .78) !important; }

        html body .ytis-card,
        html body .ytis-mini-card,
        html body .ytis-metric,
        html body .q-card {
            background: var(--ytis-surface) !important;
            border: 1px solid var(--ytis-border) !important;
            border-radius: var(--ytis-radius-md) !important;
            color: var(--ytis-text) !important;
            box-shadow: var(--ytis-shadow-panel) !important;
        }
        html body .ytis-mini-card { background: var(--ytis-surface-soft) !important; }
        html body .ytis-metric { min-height: 92px !important; }

        html body .text-slate-300,
        html body .text-slate-400,
        html body .ytis-muted { color: var(--ytis-text-secondary) !important; }
        html body .text-slate-500,
        html body .text-slate-600 { color: var(--ytis-text-muted) !important; }
        html body .text-blue-300,
        html body .text-blue-400,
        html body .ytis-blue { color: var(--ytis-blue-700) !important; }
        html body .text-green-300,
        html body .text-green-400,
        html body .ytis-green { color: var(--ytis-green-700) !important; }
        html body .text-amber-300 { color: var(--ytis-amber-700) !important; }
        html body .text-red-300 { color: var(--ytis-red-700) !important; }

        html body .q-field__control,
        html body .q-input input,
        html body .q-textarea textarea,
        html body .q-select .q-field__native {
            background: #ffffff !important;
            color: var(--ytis-text) !important;
        }
        html body .q-field__label,
        html body .q-field__native,
        html body .q-field__input { color: var(--ytis-text-secondary) !important; }
        html body .q-field__control:before { border-color: var(--ytis-border-strong) !important; }
        html body .q-field--focused .q-field__control:after { border-color: var(--ytis-blue-600) !important; }
        html body .q-field--focused .q-field__control { box-shadow: 0 0 0 3px rgba(25, 118, 233, .14) !important; }

        html body .q-btn {
            border-radius: var(--ytis-radius-sm) !important;
            box-shadow: none !important;
            font-weight: 700 !important;
            letter-spacing: 0 !important;
        }
        html body .q-btn.bg-primary { background: var(--ytis-blue-700) !important; }
        html body .q-btn.text-primary:not(.bg-primary) { color: var(--ytis-blue-700) !important; }
        html body .q-btn--outline:before { border-color: var(--ytis-border-strong) !important; }

        html body .q-badge {
            border-radius: 999px !important;
            font-size: 11px !important;
            font-weight: 700 !important;
            box-shadow: none !important;
        }
        html body .q-badge.bg-blue,
        html body .q-badge.text-blue { background: var(--ytis-blue-100) !important; color: var(--ytis-blue-700) !important; }
        html body .q-badge.bg-green,
        html body .q-badge.text-green { background: var(--ytis-green-100) !important; color: var(--ytis-green-700) !important; }
        html body .q-badge.bg-orange,
        html body .q-badge.bg-amber,
        html body .q-badge.text-orange,
        html body .q-badge.text-amber { background: var(--ytis-amber-100) !important; color: var(--ytis-amber-700) !important; }
        html body .q-badge.bg-red,
        html body .q-badge.text-red { background: var(--ytis-red-100) !important; color: var(--ytis-red-700) !important; }
        html body .q-badge.bg-purple,
        html body .q-badge.text-purple { background: var(--ytis-blue-100) !important; color: var(--ytis-blue-700) !important; }

        html body .q-separator { background: var(--ytis-border) !important; }
        html body .q-table,
        html body table { background: #ffffff !important; color: var(--ytis-text) !important; }
        html body .q-table th {
            background: var(--ytis-surface-soft) !important;
            color: var(--ytis-text-secondary) !important;
            font-size: 11px !important;
            font-weight: 800 !important;
            text-transform: uppercase;
            letter-spacing: .04em;
        }
        html body .q-table td { border-color: var(--ytis-border) !important; }

        html body .ytis-operational-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 20px;
            padding-bottom: 22px;
            border-bottom: 1px solid var(--ytis-border);
        }
        html body .ytis-operational-header h1,
        html body .ytis-page-title {
            margin: 0;
            color: var(--ytis-text) !important;
            font-size: 26px !important;
            line-height: 1.15 !important;
            letter-spacing: -.025em;
        }
        html body .ytis-kpi-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
            gap: 12px;
            width: 100%;
        }
        html body .ytis-kpi-card {
            min-height: 92px;
            padding: 16px;
            border: 1px solid var(--ytis-border);
            border-radius: var(--ytis-radius-md);
            background: #ffffff;
            box-shadow: var(--ytis-shadow-panel);
        }
        html body .ytis-kpi-label {
            color: var(--ytis-text-muted) !important;
            font-size: 11px !important;
            font-weight: 800 !important;
            letter-spacing: .055em;
            text-transform: uppercase;
        }
        html body .ytis-kpi-value {
            margin-top: 8px;
            color: var(--ytis-text) !important;
            font-size: 24px !important;
            font-weight: 800 !important;
            line-height: 1;
        }

        @media (max-width: 760px) {
            html body .ytis-page { padding: 20px 16px 36px !important; }
            html body .ytis-operational-header { flex-direction: column; }
        }
        </style>
        """,
        shared=True,
    )
