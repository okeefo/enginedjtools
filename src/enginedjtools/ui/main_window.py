"""Main application window."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from enginedjtools.scanner import EngineLibrary
from enginedjtools.theme.manager import ThemeManager
from enginedjtools.ui.panels.backup_debug import BackupDebugPanel
from enginedjtools.ui.panels.settings import SettingsPanel
from enginedjtools.ui.panels.stub import StubPanel
from enginedjtools.ui.widgets.waveform import WaveformWidget

_NAV_ITEMS = [
    ("backup_debug",  "◈  BACKUP DEBUGGER"),
    ("bad_filenames", "⚠  BAD FILENAMES"),
    ("manual_backup", "◉  MANUAL BACKUP"),
    ("library_stats", "≡  LIBRARY STATS"),
    ("db_browser",    "⬡  DB BROWSER"),
]


class MainWindow(QMainWindow):
    def __init__(self, theme_mgr: ThemeManager, library: EngineLibrary | None = None) -> None:
        super().__init__()
        self._theme_mgr = theme_mgr
        self._library = library
        self._panels: dict[str, QWidget] = {}
        self._nav_buttons: list[QPushButton] = []
        self._active_panel_id = ""

        self.setWindowTitle("Engine DJ Tools")
        self.setMinimumSize(1100, 680)

        self._build_ui()
        self._navigate_to("backup_debug")

        theme_mgr.theme_changed.connect(self._on_theme_changed)

    # ── Construction ───────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_topbar())

        body = QWidget()
        body.setObjectName("panel_area")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        body_layout.addWidget(self._make_sidebar())

        self._stack = QStackedWidget()
        self._stack.setObjectName("panel_area")
        body_layout.addWidget(self._stack, 1)

        root.addWidget(body, 1)

    def _make_topbar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("topbar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 20, 0)
        layout.setSpacing(16)

        title = QLabel("◈  ENGINE DJ TOOLS")
        title.setObjectName("app_title")
        layout.addWidget(title)

        t = self._theme_mgr.current
        ca = t.c("waveform_a") if t else "#00f5ff"
        cb = t.c("waveform_b") if t else "#ff0080"
        self._waveform = WaveformWidget(ca, cb)
        layout.addWidget(self._waveform)

        layout.addStretch()

        self._db_label = QLabel()
        self._db_label.setObjectName("db_info")
        self._db_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._update_db_label()
        layout.addWidget(self._db_label)

        return bar

    def _make_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(2)

        for panel_id, label in _NAV_ITEMS:
            btn = self._make_nav_btn(panel_id, label)
            layout.addWidget(btn)

        layout.addStretch()

        settings_btn = self._make_nav_btn("settings", "◎  SETTINGS")
        layout.addWidget(settings_btn)

        return sidebar

    def _make_nav_btn(self, panel_id: str, label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setObjectName("nav_button")
        btn.setProperty("active", False)
        btn.setProperty("panel_id", panel_id)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.clicked.connect(lambda _checked, pid=panel_id: self._navigate_to(pid))
        self._nav_buttons.append(btn)
        return btn

    # ── Navigation ─────────────────────────────────────────────────────────────

    def _navigate_to(self, panel_id: str) -> None:
        if panel_id == self._active_panel_id:
            return
        self._active_panel_id = panel_id

        for btn in self._nav_buttons:
            active = btn.property("panel_id") == panel_id
            btn.setProperty("active", active)
            # Force QSS re-evaluation after property change
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if panel_id not in self._panels:
            self._panels[panel_id] = self._create_panel(panel_id)
            self._stack.addWidget(self._panels[panel_id])

        self._stack.setCurrentWidget(self._panels[panel_id])

    def _create_panel(self, panel_id: str) -> QWidget:
        if panel_id == "backup_debug":
            return BackupDebugPanel(self._library)
        if panel_id == "settings":
            return SettingsPanel(self._theme_mgr)
        return StubPanel(panel_id.replace("_", " "))

    # ── Public ─────────────────────────────────────────────────────────────────

    def set_library(self, library: EngineLibrary) -> None:
        self._library = library
        self._update_db_label()
        # Update backup debug panel if already created
        panel = self._panels.get("backup_debug")
        if isinstance(panel, BackupDebugPanel):
            panel.set_library(library)

    def update_waveform_colors(self) -> None:
        t = self._theme_mgr.current
        if t:
            self._waveform.set_colors(t.c("waveform_a"), t.c("waveform_b"))

    # ── Slots ──────────────────────────────────────────────────────────────────

    def _on_theme_changed(self, _theme) -> None:
        self.update_waveform_colors()
        # Re-polish nav buttons so active state repaints with new colours
        for btn in self._nav_buttons:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _update_db_label(self) -> None:
        if self._library:
            self._db_label.setText(
                f"{self._library.root}   |   {self._library.track_count} tracks"
            )
        else:
            self._db_label.setText("No database loaded")
