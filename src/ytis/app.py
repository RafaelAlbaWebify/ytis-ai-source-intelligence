from __future__ import annotations

from nicegui import ui
from ytis.ui.layout import register_pages

APP_VERSION = "v0.5.5"

def main() -> None:
    register_pages(app_version=APP_VERSION)
    ui.run(
        title="YTIS - YouTube Intelligence System",
        host="127.0.0.1",
        port=8080,
        reload=False,
        dark=True,
    )

if __name__ in {"__main__", "__mp_main__"}:
    main()
