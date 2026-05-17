"""Engine DJ Tools — application entry point."""

from __future__ import annotations

from pathlib import Path

import webview

from enginedjtools.api import Api
from enginedjtools.api import _load_settings


def main() -> None:
    api  = Api()
    html = Path(__file__).parent / "ui" / "web" / "index.html"

    settings = _load_settings()
    width    = max(1024, int(settings.get("window_width",  1280)))
    height   = max(650,  int(settings.get("window_height", 800)))

    webview.create_window(
        "Engine DJ Tools",
        url=str(html),
        js_api=api,
        width=width,
        height=height,
        min_size=(1024, 650),
        background_color="#05050c",
        text_select=False,
    )
    webview.start()


if __name__ == "__main__":
    main()
