from __future__ import annotations

from nicegui import ui


def apply_theme() -> None:
    ui.add_head_html("""
    <style>
    body {
        background: radial-gradient(circle at top, #091426 0%, #07111f 55%, #050b16 100%);
        overflow-x: hidden;
    }
    .ytis-page {
        color: white;
        padding: 18px 22px;
        max-width: 1500px;
        margin: 0 auto;
    }
    .ytis-card {
        background: linear-gradient(145deg, rgba(15,27,45,0.98), rgba(18,31,51,0.95));
        border: 1px solid rgba(88, 136, 255, 0.16);
        border-radius: 18px;
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.20);
    }
    .ytis-mini-card {
        background: rgba(15,27,45,0.78);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 14px;
    }
    .ytis-metric {
        background: linear-gradient(180deg, rgba(16,27,45,0.96), rgba(12,20,35,0.92));
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 16px;
    }
    .ytis-muted { color: #94a3b8; }
    .ytis-blue { color: #60a5fa; }
    .ytis-green { color: #22c55e; }
    .ytis-red { color: #ef4444; }
    .ytis-log {
        font-family: Consolas, monospace;
        font-size: 12px;
        line-height: 1.35;
        background: rgba(8, 16, 30, 0.88);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 12px;
    }
    .q-field__control { min-height: 36px !important; }
    .q-field__native { font-size: 13px !important; }
    .q-btn { font-size: 12px !important; }
    a { color: #60a5fa; text-decoration: none; }
    </style>
    """)
