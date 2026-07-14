from __future__ import annotations

from nicegui import ui
from ytis.ui.layout import register_pages
from ytis.ui.pages_technical_research import register_technical_research_page

APP_VERSION = "v0.10.0"


def main() -> None:
    register_technical_research_page(app_version=APP_VERSION)
    register_pages(app_version=APP_VERSION)
    ui.run(
        title="YTIS - AI Source Intelligence Workbench",
        host="127.0.0.1",
        port=8080,
        reload=False,
        dark=True,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
