"""Main menu screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Label, Static
from textual.containers import Vertical, ScrollableContainer


MENU_ITEMS = [
    ("🔍  Backup Debugger",   "Diagnose why Engine DJ backup is failing", "backup_debug"),
    ("💾  Manual Backup",      "Reliably back up your library to any location", "manual_backup"),
    ("📊  Library Stats",      "Track counts, playlist overview, database health", "stats"),
    ("⚠️   Bad Filename Finder", "Find tracks with illegal or problematic characters", "bad_filenames"),
    ("🗄️   Database Browser",   "Browse tracks, playlists and crates", "browser"),
]

LOGO = r"""
  ███████╗███╗   ██╗ ██████╗ ██╗███╗   ██╗███████╗    ██████╗      ██╗
  ██╔════╝████╗  ██║██╔════╝ ██║████╗  ██║██╔════╝    ██╔══██╗     ██║
  █████╗  ██╔██╗ ██║██║  ███╗██║██╔██╗ ██║█████╗      ██║  ██║     ██║
  ██╔══╝  ██║╚██╗██║██║   ██║██║██║╚██╗██║██╔══╝      ██║  ██║██   ██║
  ███████╗██║ ╚████║╚██████╔╝██║██║ ╚████║███████╗    ██████╔╝╚█████╔╝
  ╚══════╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝╚═╝  ╚═══╝╚══════╝    ╚═════╝  ╚════╝
                         T O O L S
"""


class MenuItem(Static):
    """A single clickable menu entry."""

    def __init__(self, title: str, description: str, action_id: str) -> None:
        super().__init__(classes="menu-item")
        self._title = title
        self._description = description
        self._action_id = action_id

    def compose(self) -> ComposeResult:
        yield Label(self._title, classes="item-title")
        yield Label(self._description, classes="item-desc")

    def on_click(self) -> None:
        self.app.push_screen(self._action_id)


class HomeScreen(Screen):
    """The main menu."""

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Static(LOGO, id="app-header")

        db_path = getattr(self.app, "active_library", None)
        db_label = str(db_path) if db_path else "No database selected"
        yield Static(f"  ◈  Active library: {db_label}", id="db-path")

        yield ScrollableContainer(
            *[MenuItem(title, desc, action) for title, desc, action in MENU_ITEMS],
            id="menu-container",
        )
        yield Footer()
