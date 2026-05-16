"""Startup scan screen — discovers Engine DJ databases."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Label, LoadingIndicator, Static
from textual.worker import Worker, WorkerState
from textual.containers import Vertical

from enginedjtools.scanner import EngineLibrary, scan


class ScanScreen(Screen):
    """Shown at startup while scanning for Engine DJ databases."""

    def compose(self) -> ComposeResult:
        yield Static(
            "\n  ◈  ENGINE DJ TOOLS  ◈\n  Scanning for databases...",
            id="scan-label",
        )
        yield LoadingIndicator()
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self._do_scan, exclusive=True)

    async def _do_scan(self) -> list[EngineLibrary]:
        return scan()

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.SUCCESS:
            libraries: list[EngineLibrary] = event.worker.result
            if not libraries:
                self.app.push_screen("no_db")
            elif len(libraries) == 1:
                self.app.active_library = libraries[0]
                self.app.push_screen("home")
            else:
                self.app.found_libraries = libraries
                self.app.push_screen("choose_db")
