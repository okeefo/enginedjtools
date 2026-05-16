"""Engine DJ Tools — main application entry point."""

from __future__ import annotations

from textual.app import App

from enginedjtools.scanner import EngineLibrary
from enginedjtools.ui.screens.backup_debug import BackupDebugScreen
from enginedjtools.ui.screens.home import HomeScreen
from enginedjtools.ui.screens.scan import ScanScreen
from enginedjtools.ui.theme import RAVE_CSS


class EngineDJToolsApp(App):
    """The main enginedjtools TUI application."""

    CSS = RAVE_CSS

    SCREENS = {
        "home": HomeScreen,
        "scan": ScanScreen,
        "backup_debug": BackupDebugScreen,
    }

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    # Set by ScanScreen / ChooseDbScreen after discovery
    active_library: EngineLibrary | None = None
    found_libraries: list[EngineLibrary] = []

    def on_mount(self) -> None:
        self.push_screen("scan")


def main() -> None:
    EngineDJToolsApp().run()


if __name__ == "__main__":
    main()
