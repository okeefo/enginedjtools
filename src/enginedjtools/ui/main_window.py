"""Main application window."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
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
    ("backup_debug",  "◈", "Backup Debugger"),
    ("bad_filenames", "⚠", "Bad Filenames"),
    ("manual_backup", "◉", "Manual Backup"),
    ("library_stats", "≡", "Library Stats"),
    ("db_browser",    "⬡", "DB Browser"),
]


# ── Custom nav item widget ─────────────────────────────────────────────────────

class NavItem(QWidget):
    """Sidebar nav item with separate icon and label, left-border active state."""

    clicked = pyqtSignal()

    def __init__(self, panel_id: str, icon: str, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.panel_id = panel_id
        self._active = False

        self.setAttribute(Qt.WA_Hover, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Left active indicator strip
        self._indicator = QFrame()
        self._indicator.setObjectName("nav_indicator")
        self._indicator.setFixedWidth(3)
        self._indicator.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        layout.addWidget(self._indicator)

        # Inner content
        inner = QHBoxLayout()
        inner.setContentsMargins(16, 10, 16, 10)
        inner.setSpacing(12)

        self._icon_lbl = QLabel(icon)
        self._icon_lbl.setObjectName("nav_icon")
        self._icon_lbl.setFixedWidth(18)
        self._icon_lbl.setAlignment(Qt.AlignCenter)
        inner.addWidget(self._icon_lbl)

        self._text_lbl = QLabel(label)
        self._text_lbl.setObjectName("nav_label")
        inner.addWidget(self._text_lbl, 1)

        layout.addLayout(inner)

        self.setObjectName("nav_item")

    def set_active(self, active: bool) -> None:
        self._active = active
        for w in (self, self._indicator, self._icon_lbl, self._text_lbl):
            w.setProperty("active", active)
            w.style().unpolish(w)
            w.style().polish(w)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


# ── Main window ────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self, theme_mgr: ThemeManager, library: EngineLibrary | None = None) -> None:
        super().__init__()
        self._theme_mgr = theme_mgr
        self._library = library
        self._panels: dict[str, QWidget] = {}
        self._nav_items: list[NavItem] = []
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
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(20)

        # Current panel title (updates on navigation)
        self._panel_title_lbl = QLabel("BACKUP DEBUGGER")
        self._panel_title_lbl.setObjectName("topbar_panel_title")
        layout.addWidget(self._panel_title_lbl)

        # Waveform (fills remaining space)
        t = self._theme_mgr.current
        ca = t.c("waveform_a") if t else "#00f5ff"
        cb = t.c("waveform_b") if t else "#ff0080"
        self._waveform = WaveformWidget(ca, cb)
        layout.addWidget(self._waveform, 1)

        return bar

    def _make_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Logo section ──────────────────────────────────────
        logo_wrap = QFrame()
        logo_wrap.setObjectName("logo_wrap")
        logo_layout = QVBoxLayout(logo_wrap)
        logo_layout.setContentsMargins(20, 22, 20, 18)
        logo_layout.setSpacing(4)

        eyebrow = QLabel("ACID HOUSE CONTROL TERMINAL")
        eyebrow.setObjectName("logo_eyebrow")
        logo_layout.addWidget(eyebrow)

        logo = QLabel("ENGINE DJ\nTOOLS")
        logo.setObjectName("logo_text")
        logo_layout.addWidget(logo)

        logo_sub = QLabel("DATABASE MANAGEMENT")
        logo_sub.setObjectName("logo_sub")
        logo_layout.addWidget(logo_sub)

        layout.addWidget(logo_wrap)

        # ── Active DB pill ─────────────────────────────────────
        self._db_pill = QFrame()
        self._db_pill.setObjectName("db_pill")
        pill_layout = QVBoxLayout(self._db_pill)
        pill_layout.setContentsMargins(12, 8, 12, 8)
        pill_layout.setSpacing(3)

        self._db_pill_label = QLabel("ACTIVE DB")
        self._db_pill_label.setObjectName("db_pill_label")
        pill_layout.addWidget(self._db_pill_label)

        self._db_pill_path = QLabel("—")
        self._db_pill_path.setObjectName("db_pill_path")
        self._db_pill_path.setWordWrap(True)
        pill_layout.addWidget(self._db_pill_path)

        self._db_pill_tracks = QLabel("")
        self._db_pill_tracks.setObjectName("db_pill_tracks")
        pill_layout.addWidget(self._db_pill_tracks)

        pill_wrap = QWidget()
        pill_wrap_layout = QHBoxLayout(pill_wrap)
        pill_wrap_layout.setContentsMargins(14, 0, 14, 12)
        pill_wrap_layout.addWidget(self._db_pill)
        layout.addWidget(pill_wrap)

        self._update_db_pill()

        # ── Nav section ────────────────────────────────────────
        section_lbl = QLabel("TOOLS")
        section_lbl.setObjectName("nav_section_label")
        section_wrap = QWidget()
        section_wrap_layout = QHBoxLayout(section_wrap)
        section_wrap_layout.setContentsMargins(20, 8, 20, 4)
        section_wrap_layout.addWidget(section_lbl)
        layout.addWidget(section_wrap)

        for panel_id, icon, label in _NAV_ITEMS:
            item = NavItem(panel_id, icon, label)
            item.clicked.connect(lambda pid=panel_id: self._navigate_to(pid))
            self._nav_items.append(item)
            layout.addWidget(item)

        layout.addStretch(1)

        # Settings at bottom
        sep = QFrame()
        sep.setObjectName("sidebar_sep")
        layout.addWidget(sep)

        settings_item = NavItem("settings", "◎", "Settings")
        settings_item.clicked.connect(lambda: self._navigate_to("settings"))
        self._nav_items.append(settings_item)
        layout.addWidget(settings_item)

        # Footer
        footer = QLabel("v0.1.0")
        footer.setObjectName("sidebar_footer")
        footer_wrap = QWidget()
        footer_wrap_layout = QHBoxLayout(footer_wrap)
        footer_wrap_layout.setContentsMargins(20, 6, 20, 10)
        footer_wrap_layout.addWidget(footer)
        layout.addWidget(footer_wrap)

        return sidebar

    # ── Navigation ─────────────────────────────────────────────────────────────

    def _navigate_to(self, panel_id: str) -> None:
        if panel_id == self._active_panel_id:
            return
        self._active_panel_id = panel_id

        for item in self._nav_items:
            item.set_active(item.panel_id == panel_id)

        # Update topbar title
        label = next((lbl for pid, _icon, lbl in _NAV_ITEMS if pid == panel_id), panel_id.replace("_", " ").title())
        if panel_id == "settings":
            label = "Settings"
        self._panel_title_lbl.setText(label.upper())

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
        self._update_db_pill()
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
        for item in self._nav_items:
            item.set_active(item.panel_id == self._active_panel_id)

    def _update_db_pill(self) -> None:
        if self._library:
            # Shorten path for display
            path = str(self._library.root)
            if len(path) > 30:
                path = "…" + path[-28:]
            self._db_pill_path.setText(path)
            self._db_pill_tracks.setText(f"{self._library.track_count} tracks")
        else:
            self._db_pill_path.setText("No database loaded")
            self._db_pill_tracks.setText("")
