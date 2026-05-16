"""Settings panel — theme manager UI."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QApplication,
    QColorDialog,
    QComboBox,
    QFontComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from enginedjtools.theme.manager import ThemeManager

# Human-readable labels for theme keys
_COLOR_LABELS: dict[str, str] = {
    "bg_primary":            "Background (primary)",
    "bg_secondary":          "Background (secondary)",
    "bg_surface":            "Surface",
    "bg_elevated":           "Elevated surface",
    "border":                "Border",
    "border_accent":         "Border (accent)",
    "accent_cyan":           "Accent — cyan",
    "accent_magenta":        "Accent — magenta",
    "accent_yellow":         "Accent — yellow",
    "text_primary":          "Text (primary)",
    "text_secondary":        "Text (secondary)",
    "text_disabled":         "Text (disabled)",
    "text_on_accent":        "Text on accent",
    "success":               "Success",
    "warning":               "Warning",
    "error":                 "Error",
    "sidebar_bg":            "Sidebar background",
    "sidebar_active_bg":     "Sidebar active background",
    "sidebar_active_border": "Sidebar active border",
    "topbar_bg":             "Topbar background",
    "button_bg":             "Button background",
    "button_hover_bg":       "Button hover background",
    "button_primary_bg":     "Primary button background",
    "button_primary_text":   "Primary button text",
    "table_header_bg":       "Table header background",
    "table_row_alt":         "Table row (alternate)",
    "input_bg":              "Input background",
    "input_border":          "Input border",
    "scrollbar_bg":          "Scrollbar background",
    "scrollbar_handle":      "Scrollbar handle",
    "waveform_a":            "Waveform colour A",
    "waveform_b":            "Waveform colour B",
}

_FONT_LABELS: dict[str, str] = {
    "display":          "Display font",
    "mono":             "Monospace font",
    "body":             "Body font",
    "display_fallback": "Display fallback",
    "mono_fallback":    "Mono fallback",
    "body_fallback":    "Body fallback",
}

_SIZE_LABELS: dict[str, str] = {
    "font_title":   "Title font size (pt)",
    "font_heading": "Heading font size (pt)",
    "font_body":    "Body font size (pt)",
    "font_small":   "Small font size (pt)",
    "font_mono":    "Mono font size (pt)",
    "font_nav":     "Nav font size (pt)",
}

_SPACING_LABELS: dict[str, str] = {
    "sidebar_width":   "Sidebar width (px)",
    "topbar_height":   "Topbar height (px)",
    "padding_sm":      "Padding small (px)",
    "padding_md":      "Padding medium (px)",
    "padding_lg":      "Padding large (px)",
    "border_radius":   "Border radius (px)",
    "border_radius_lg":"Border radius large (px)",
}


class SettingsPanel(QWidget):
    """Theme manager panel: select, edit, save, save-as, delete themes."""

    def __init__(self, theme_mgr: ThemeManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mgr = theme_mgr
        self._color_buttons: dict[str, QPushButton] = {}
        self._font_combos: dict[str, QFontComboBox] = {}
        self._size_spins: dict[str, QSpinBox] = {}
        self._spacing_spins: dict[str, QSpinBox] = {}
        self._updating = False  # guard against recursive signals

        self._build_ui()
        self._populate_theme_selector()
        theme_mgr.theme_changed.connect(self._refresh_controls)

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(12)

        title = QLabel("◎  SETTINGS")
        title.setObjectName("panel_title")
        outer.addWidget(title)

        sep = QFrame()
        sep.setObjectName("separator")
        outer.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setSpacing(16)
        self._content_layout.setContentsMargins(0, 0, 12, 0)

        self._build_theme_header()
        self._build_colors_section()
        self._build_fonts_section()
        self._build_sizes_section()
        self._build_spacing_section()

        self._content_layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

    def _build_theme_header(self) -> None:
        group = QGroupBox("THEME")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # Selector row
        sel_row = QHBoxLayout()
        self._theme_combo = QComboBox()
        self._theme_combo.currentTextChanged.connect(self._on_theme_selected)
        sel_row.addWidget(self._theme_combo, 1)

        self._save_btn = QPushButton("Save")
        self._save_btn.clicked.connect(self._on_save)
        sel_row.addWidget(self._save_btn)

        self._save_as_btn = QPushButton("Save As…")
        self._save_as_btn.clicked.connect(self._on_save_as)
        sel_row.addWidget(self._save_as_btn)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setObjectName("danger_button")
        self._delete_btn.clicked.connect(self._on_delete)
        sel_row.addWidget(self._delete_btn)

        layout.addLayout(sel_row)

        # Readonly notice
        self._readonly_lbl = QLabel("⚠  Read-only theme — use Save As… to create a custom version.")
        self._readonly_lbl.setObjectName("label_warn")
        self._readonly_lbl.hide()
        layout.addWidget(self._readonly_lbl)

        self._content_layout.addWidget(group)

    def _build_colors_section(self) -> None:
        group = QGroupBox("COLOURS")
        grid = QGridLayout(group)
        grid.setSpacing(6)
        grid.setColumnMinimumWidth(0, 220)

        for i, (key, label) in enumerate(_COLOR_LABELS.items()):
            row, col_base = divmod(i, 2)
            lbl = QLabel(label)
            btn = QPushButton()
            btn.setFixedSize(60, 26)
            btn.setToolTip(f"Edit: {label}")
            btn.clicked.connect(lambda checked, k=key: self._pick_color(k))
            self._color_buttons[key] = btn
            grid.addWidget(lbl,  row, col_base * 2)
            grid.addWidget(btn,  row, col_base * 2 + 1)

        self._content_layout.addWidget(group)

    def _build_fonts_section(self) -> None:
        group = QGroupBox("FONTS")
        grid = QGridLayout(group)
        grid.setSpacing(6)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        for i, (key, label) in enumerate(_FONT_LABELS.items()):
            row, col_base = divmod(i, 2)
            lbl = QLabel(label)
            combo = QFontComboBox()
            combo.currentFontChanged.connect(lambda font, k=key: self._on_font_changed(k, font.family()))
            self._font_combos[key] = combo
            grid.addWidget(lbl,   row, col_base * 2)
            grid.addWidget(combo, row, col_base * 2 + 1)

        self._content_layout.addWidget(group)

    def _build_sizes_section(self) -> None:
        group = QGroupBox("FONT SIZES")
        grid = QGridLayout(group)
        grid.setSpacing(6)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        for i, (key, label) in enumerate(_SIZE_LABELS.items()):
            row, col_base = divmod(i, 2)
            lbl = QLabel(label)
            spin = QSpinBox()
            spin.setRange(6, 72)
            spin.setSuffix(" pt")
            spin.valueChanged.connect(lambda v, k=key: self._on_size_changed(k, v))
            self._size_spins[key] = spin
            grid.addWidget(lbl,  row, col_base * 2)
            grid.addWidget(spin, row, col_base * 2 + 1)

        self._content_layout.addWidget(group)

    def _build_spacing_section(self) -> None:
        group = QGroupBox("SPACING")
        grid = QGridLayout(group)
        grid.setSpacing(6)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        for i, (key, label) in enumerate(_SPACING_LABELS.items()):
            row, col_base = divmod(i, 2)
            lbl = QLabel(label)
            spin = QSpinBox()
            spin.setRange(0, 800)
            spin.setSuffix(" px")
            spin.valueChanged.connect(lambda v, k=key: self._on_spacing_changed(k, v))
            self._spacing_spins[key] = spin
            grid.addWidget(lbl,  row, col_base * 2)
            grid.addWidget(spin, row, col_base * 2 + 1)

        self._content_layout.addWidget(group)

    # ── Populate / refresh ─────────────────────────────────────────────────────

    def _populate_theme_selector(self) -> None:
        self._updating = True
        self._theme_combo.clear()
        for name in self._mgr.theme_names:
            self._theme_combo.addItem(name)
        if self._mgr.current:
            idx = self._theme_combo.findText(self._mgr.current.name)
            if idx >= 0:
                self._theme_combo.setCurrentIndex(idx)
        self._updating = False
        self._refresh_controls()

    def _refresh_controls(self) -> None:
        t = self._mgr.current
        if not t:
            return
        self._updating = True

        # Readonly state
        readonly = t.readonly
        self._readonly_lbl.setVisible(readonly)
        self._save_btn.setEnabled(not readonly)
        self._delete_btn.setEnabled(not readonly)

        # Colors
        for key, btn in self._color_buttons.items():
            hex_color = t.colors.get(key, "#888888")
            self._apply_color_to_btn(btn, hex_color)

        # Fonts
        for key, combo in self._font_combos.items():
            family = t.fonts.get(key, "Arial")
            from PyQt5.QtGui import QFont  # noqa: PLC0415
            combo.setCurrentFont(QFont(family))

        # Sizes
        for key, spin in self._size_spins.items():
            spin.setValue(t.sizes.get(key, 12))

        # Spacing
        for key, spin in self._spacing_spins.items():
            spin.setValue(t.spacing.get(key, 8))

        self._updating = False

    # ── Interaction ────────────────────────────────────────────────────────────

    def _on_theme_selected(self, name: str) -> None:
        if self._updating or not name:
            return
        self._mgr.load(name)
        self._mgr.apply(QApplication.instance())

    def _pick_color(self, key: str) -> None:
        t = self._mgr.current
        if not t:
            return
        initial = QColor(t.colors.get(key, "#ffffff"))
        color = QColorDialog.getColor(initial, self, f"Choose colour — {_COLOR_LABELS.get(key, key)}")
        if not color.isValid():
            return
        hex_val = color.name().upper()
        self._mgr.update_color(key, hex_val)
        self._apply_color_to_btn(self._color_buttons[key], hex_val)
        self._mgr.apply(QApplication.instance())
        self._notify_waveform_if_needed(key, hex_val)

    def _on_font_changed(self, key: str, family: str) -> None:
        if self._updating:
            return
        self._mgr.update_font(key, family)
        self._mgr.apply(QApplication.instance())

    def _on_size_changed(self, key: str, value: int) -> None:
        if self._updating:
            return
        self._mgr.update_size(key, value)
        self._mgr.apply(QApplication.instance())

    def _on_spacing_changed(self, key: str, value: int) -> None:
        if self._updating:
            return
        self._mgr.update_spacing(key, value)
        self._mgr.apply(QApplication.instance())

    def _on_save(self) -> None:
        self._mgr.save()

    def _on_save_as(self) -> None:
        name, ok = QInputDialog.getText(self, "Save Theme As", "New theme name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if name in self._mgr.theme_names:
            QMessageBox.warning(self, "Name Taken", f"A theme named '{name}' already exists.")
            return
        self._mgr.save_as(name)
        self._populate_theme_selector()

    def _on_delete(self) -> None:
        t = self._mgr.current
        if not t or t.readonly:
            return
        answer = QMessageBox.question(
            self, "Delete Theme",
            f"Delete theme '{t.name}'? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self._mgr.delete(t.name)
        # Switch to first available theme
        if self._mgr.theme_names:
            self._mgr.load(self._mgr.theme_names[0])
            self._mgr.apply(QApplication.instance())
        self._populate_theme_selector()

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _apply_color_to_btn(btn: QPushButton, hex_color: str) -> None:
        c = QColor(hex_color)
        brightness = c.red() * 0.299 + c.green() * 0.587 + c.blue() * 0.114
        text_color = "#000000" if brightness > 128 else "#ffffff"
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {hex_color}; color: {text_color}; "
            f"border: 1px solid #444; border-radius: 3px; }}"
            f"QPushButton:hover {{ border: 1px solid #fff; }}"
        )

    def _notify_waveform_if_needed(self, key: str, hex_val: str) -> None:
        if key not in ("waveform_a", "waveform_b"):
            return
        # Find main window and update waveform
        from PyQt5.QtWidgets import QApplication  # noqa: PLC0415
        for w in QApplication.topLevelWidgets():
            if hasattr(w, "update_waveform_colors"):
                w.update_waveform_colors()
                break
