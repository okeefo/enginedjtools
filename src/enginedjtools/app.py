"""Engine DJ Tools — application entry point."""

from __future__ import annotations

from pathlib import Path

import webview

from enginedjtools.api import Api


def main() -> None:
    api = Api()
    html = Path(__file__).parent / "ui" / "web" / "index.html"

    webview.create_window(
        "Engine DJ Tools",
        url=str(html),
        js_api=api,
        width=1280,
        height=800,
        min_size=(1024, 650),
        background_color="#05050c",
        text_select=False,
    )
    webview.start()


if __name__ == "__main__":
    main()
