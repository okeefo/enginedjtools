"""Theme loading, saving, and QSS generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication

_BUNDLED_THEMES = Path(__file__).parent / "themes"
_USER_THEMES = Path.home() / ".enginedjtools" / "themes"


class Theme:
    def __init__(self, data: dict[str, Any], path: Path | None = None) -> None:
        self.name: str = data["name"]
        self.readonly: bool = data.get("readonly", False)
        self.colors: dict[str, str] = dict(data.get("colors", {}))
        self.fonts: dict[str, str] = dict(data.get("fonts", {}))
        self.sizes: dict[str, int] = dict(data.get("sizes", {}))
        self.spacing: dict[str, int] = dict(data.get("spacing", {}))
        self.path: Path | None = path

    # Convenience accessors
    def c(self, key: str) -> str:
        return self.colors.get(key, "#ff00ff")

    def f(self, key: str) -> str:
        return self.fonts.get(key, "Arial")

    def s(self, key: str) -> int:
        return self.sizes.get(key, 12)

    def sp(self, key: str) -> int:
        return self.spacing.get(key, 8)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "readonly": self.readonly,
            "colors": dict(self.colors),
            "fonts": dict(self.fonts),
            "sizes": dict(self.sizes),
            "spacing": dict(self.spacing),
        }


class ThemeManager(QObject):
    """Manages themes: load, apply, save, save-as, delete."""

    theme_changed = pyqtSignal(object)  # emits Theme

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._themes: dict[str, Theme] = {}
        self._current: Theme | None = None
        self._reload()

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def current(self) -> Theme | None:
        return self._current

    @property
    def theme_names(self) -> list[str]:
        return sorted(self._themes.keys())

    def load(self, name: str) -> None:
        if name in self._themes:
            self._current = self._themes[name]
            self.theme_changed.emit(self._current)

    def apply(self, app: QApplication) -> None:
        if self._current:
            app.setStyleSheet(_build_qss(self._current))

    def save(self) -> None:
        """Persist the current theme (no-op if readonly)."""
        if self._current is None or self._current.readonly:
            return
        _USER_THEMES.mkdir(parents=True, exist_ok=True)
        path = _USER_THEMES / f"{self._current.name}.json"
        path.write_text(json.dumps(self._current.to_dict(), indent=2), encoding="utf-8")
        self._current.path = path

    def save_as(self, new_name: str) -> Theme:
        """Fork the current theme under a new name and return it."""
        if self._current is None:
            raise RuntimeError("No theme loaded")
        _USER_THEMES.mkdir(parents=True, exist_ok=True)
        data = self._current.to_dict()
        data["name"] = new_name
        data["readonly"] = False
        path = _USER_THEMES / f"{new_name}.json"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        theme = Theme(data, path)
        self._themes[new_name] = theme
        self._current = theme
        self.theme_changed.emit(self._current)
        return theme

    def delete(self, name: str) -> None:
        theme = self._themes.get(name)
        if theme is None or theme.readonly:
            return
        if theme.path and theme.path.exists():
            theme.path.unlink()
        del self._themes[name]

    def update_color(self, key: str, value: str) -> None:
        if self._current:
            self._current.colors[key] = value

    def update_font(self, key: str, value: str) -> None:
        if self._current:
            self._current.fonts[key] = value

    def update_size(self, key: str, value: int) -> None:
        if self._current:
            self._current.sizes[key] = value

    def update_spacing(self, key: str, value: int) -> None:
        if self._current:
            self._current.spacing[key] = value

    # ── Internal ──────────────────────────────────────────────────────────────

    def _reload(self) -> None:
        self._themes.clear()
        for p in sorted(_BUNDLED_THEMES.glob("*.json")):
            self._load_file(p, bundled=True)
        _USER_THEMES.mkdir(parents=True, exist_ok=True)
        for p in sorted(_USER_THEMES.glob("*.json")):
            self._load_file(p, bundled=False)

    def _load_file(self, path: Path, bundled: bool) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            t = Theme(data, path)
            if not bundled:
                t.readonly = False
            self._themes[t.name] = t
        except Exception:
            pass


# ── QSS template ──────────────────────────────────────────────────────────────

def _build_qss(t: Theme) -> str:
    return f"""
/* === BASE === */
QWidget {{
    background-color: {t.c("bg_primary")};
    color: {t.c("text_primary")};
    font-family: "{t.f("body")}", "{t.f("body_fallback")}";
    font-size: {t.s("font_body")}pt;
    border: none;
    outline: none;
}}
QMainWindow, QDialog {{
    background-color: {t.c("bg_primary")};
}}

/* === TOPBAR === */
QFrame#topbar {{
    background-color: {t.c("topbar_bg")};
    border-bottom: 1px solid rgba(0,245,255,0.12);
    min-height: {t.sp("topbar_height")}px;
    max-height: {t.sp("topbar_height")}px;
}}
QLabel#topbar_panel_title {{
    font-family: "{t.f("display")}", "{t.f("display_fallback")}";
    font-size: {t.s("font_heading")}pt;
    font-weight: bold;
    color: {t.c("text_primary")};
    letter-spacing: 2px;
}}

/* === SIDEBAR === */
QFrame#sidebar {{
    background-color: {t.c("sidebar_bg")};
    border-right: 1px solid rgba(0,245,255,0.12);
    min-width: {t.sp("sidebar_width")}px;
    max-width: {t.sp("sidebar_width")}px;
}}

/* ── Logo section ── */
QFrame#logo_wrap {{
    background-color: transparent;
    border-bottom: 1px solid rgba(0,245,255,0.10);
}}
QLabel#logo_eyebrow {{
    font-family: "{t.f("mono")}", "{t.f("mono_fallback")}";
    font-size: 8pt;
    letter-spacing: 3px;
    color: {t.c("accent_magenta")};
    background: transparent;
}}
QLabel#logo_text {{
    font-family: "{t.f("display")}", "{t.f("display_fallback")}";
    font-size: 15pt;
    font-weight: bold;
    letter-spacing: 1px;
    color: {t.c("accent_cyan")};
    line-height: 1.2;
    background: transparent;
}}
QLabel#logo_sub {{
    font-family: "{t.f("mono")}", "{t.f("mono_fallback")}";
    font-size: 8pt;
    letter-spacing: 2px;
    color: {t.c("text_secondary")};
    background: transparent;
}}

/* ── Active DB pill ── */
QFrame#db_pill {{
    background-color: rgba(238,255,0,0.05);
    border: 1px solid rgba(238,255,0,0.22);
    border-radius: {t.sp("border_radius")}px;
}}
QLabel#db_pill_label {{
    font-family: "{t.f("mono")}", "{t.f("mono_fallback")}";
    font-size: 8pt;
    letter-spacing: 3px;
    color: {t.c("accent_yellow")};
    background: transparent;
}}
QLabel#db_pill_path {{
    font-family: "{t.f("mono")}", "{t.f("mono_fallback")}";
    font-size: 8pt;
    color: {t.c("text_primary")};
    background: transparent;
}}
QLabel#db_pill_tracks {{
    font-family: "{t.f("mono")}", "{t.f("mono_fallback")}";
    font-size: 8pt;
    color: {t.c("text_secondary")};
    background: transparent;
}}

/* ── Nav section label ── */
QLabel#nav_section_label {{
    font-family: "{t.f("mono")}", "{t.f("mono_fallback")}";
    font-size: 8pt;
    letter-spacing: 3px;
    color: {t.c("text_disabled")};
    background: transparent;
}}

/* ── Nav items ── */
QWidget#nav_item {{
    background-color: transparent;
}}
QWidget#nav_item:hover {{
    background-color: rgba(0,245,255,0.05);
}}
QWidget#nav_item[active="true"] {{
    background-color: rgba(0,245,255,0.08);
}}
QFrame#nav_indicator {{
    background-color: transparent;
    border: none;
}}
QFrame#nav_indicator[active="true"] {{
    background-color: {t.c("sidebar_active_border")};
}}
QLabel#nav_icon {{
    font-size: 13pt;
    color: {t.c("text_secondary")};
    background: transparent;
}}
QLabel#nav_icon[active="true"] {{
    color: {t.c("accent_cyan")};
}}
QLabel#nav_label {{
    font-family: "{t.f("body")}", "{t.f("body_fallback")}";
    font-size: {t.s("font_nav")}pt;
    font-weight: 600;
    letter-spacing: 0.5px;
    color: {t.c("text_secondary")};
    background: transparent;
}}
QLabel#nav_label[active="true"] {{
    color: {t.c("accent_cyan")};
}}

/* ── Sidebar separator / footer ── */
QFrame#sidebar_sep {{
    background-color: rgba(0,245,255,0.08);
    max-height: 1px;
    min-height: 1px;
    border: none;
}}
QLabel#sidebar_footer {{
    font-family: "{t.f("mono")}", "{t.f("mono_fallback")}";
    font-size: 8pt;
    letter-spacing: 1px;
    color: {t.c("text_disabled")};
    background: transparent;
}}

/* === PANEL AREA === */
QWidget#panel_area {{
    background-color: {t.c("bg_primary")};
}}
QScrollArea {{
    background-color: {t.c("bg_primary")};
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background-color: {t.c("bg_primary")};
}}

/* === LABELS === */
QLabel {{
    background-color: transparent;
    color: {t.c("text_primary")};
    font-size: {t.s("font_body")}pt;
}}
QLabel#panel_title {{
    font-family: "{t.f("display")}", "{t.f("display_fallback")}";
    font-size: {t.s("font_title")}pt;
    font-weight: bold;
    color: {t.c("accent_cyan")};
    letter-spacing: 2px;
}}
QLabel#section_heading {{
    font-family: "{t.f("body")}", "{t.f("body_fallback")}";
    font-size: {t.s("font_small")}pt;
    font-weight: bold;
    color: {t.c("text_secondary")};
    letter-spacing: 2px;
}}
QLabel#label_ok    {{ color: {t.c("success")}; font-family: "{t.f("mono")}", "{t.f("mono_fallback")}"; }}
QLabel#label_error {{ color: {t.c("error")};   font-family: "{t.f("mono")}", "{t.f("mono_fallback")}"; }}
QLabel#label_warn  {{ color: {t.c("warning")}; font-family: "{t.f("mono")}", "{t.f("mono_fallback")}"; }}
QLabel#label_mono  {{ font-family: "{t.f("mono")}", "{t.f("mono_fallback")}"; font-size: {t.s("font_mono")}pt; }}

/* === BUTTONS === */
QPushButton {{
    background-color: {t.c("button_bg")};
    color: {t.c("text_primary")};
    font-family: "{t.f("body")}", "{t.f("body_fallback")}";
    font-size: {t.s("font_body")}pt;
    font-weight: bold;
    border: 1px solid {t.c("border")};
    border-radius: {t.sp("border_radius")}px;
    padding: {t.sp("padding_sm")}px {t.sp("padding_md")}px;
    letter-spacing: 1px;
}}
QPushButton:hover {{
    background-color: {t.c("button_hover_bg")};
    border-color: {t.c("text_secondary")};
}}
QPushButton:pressed {{ background-color: {t.c("bg_elevated")}; }}
QPushButton:disabled {{
    color: {t.c("text_disabled")};
    border-color: {t.c("border")};
    background-color: {t.c("bg_primary")};
}}
QPushButton#primary_button {{
    background-color: {t.c("button_primary_bg")};
    color: {t.c("button_primary_text")};
    border-color: {t.c("button_primary_bg")};
}}
QPushButton#primary_button:hover {{ background-color: {t.c("accent_cyan")}; }}
QPushButton#danger_button  {{ border-color: {t.c("error")};   color: {t.c("error")}; }}
QPushButton#danger_button:hover  {{ background-color: {t.c("error")};   color: {t.c("bg_primary")}; }}
QPushButton#warning_button {{ border-color: {t.c("warning")}; color: {t.c("warning")}; }}
QPushButton#warning_button:hover {{ background-color: {t.c("warning")}; color: {t.c("bg_primary")}; }}

/* === FRAMES / CARDS === */
QFrame#card {{
    background-color: {t.c("bg_surface")};
    border: 1px solid {t.c("border")};
    border-radius: {t.sp("border_radius_lg")}px;
}}
QFrame#alert_error {{
    background-color: #1a0510;
    border: 1px solid {t.c("error")};
    border-radius: {t.sp("border_radius")}px;
}}
QFrame#separator {{
    background-color: {t.c("border")};
    max-height: 1px;
    min-height: 1px;
}}

/* === SCROLL BARS === */
QScrollBar:vertical {{
    background-color: {t.c("scrollbar_bg")};
    width: 8px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background-color: {t.c("scrollbar_handle")};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background-color: {t.c("scrollbar_bg")};
    height: 8px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background-color: {t.c("scrollbar_handle")};
    border-radius: 4px;
    min-width: 20px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* === TABLE === */
QTableWidget {{
    background-color: {t.c("bg_surface")};
    alternate-background-color: {t.c("table_row_alt")};
    border: 1px solid {t.c("border")};
    border-radius: {t.sp("border_radius")}px;
    gridline-color: {t.c("border")};
    font-family: "{t.f("mono")}", "{t.f("mono_fallback")}";
    font-size: {t.s("font_mono")}pt;
    selection-background-color: {t.c("sidebar_active_bg")};
    selection-color: {t.c("accent_cyan")};
}}
QHeaderView::section {{
    background-color: {t.c("table_header_bg")};
    color: {t.c("text_secondary")};
    font-family: "{t.f("body")}", "{t.f("body_fallback")}";
    font-size: {t.s("font_small")}pt;
    font-weight: bold;
    letter-spacing: 1px;
    padding: {t.sp("padding_sm")}px {t.sp("padding_md")}px;
    border: none;
    border-bottom: 1px solid {t.c("border")};
    border-right: 1px solid {t.c("border")};
}}
QTableWidget::item {{ padding: {t.sp("padding_sm")}px; }}

/* === COMBO BOX === */
QComboBox {{
    background-color: {t.c("input_bg")};
    color: {t.c("text_primary")};
    border: 1px solid {t.c("input_border")};
    border-radius: {t.sp("border_radius")}px;
    padding: {t.sp("padding_sm")}px {t.sp("padding_md")}px;
    font-size: {t.s("font_body")}pt;
    min-width: 140px;
}}
QComboBox:focus {{ border-color: {t.c("accent_cyan")}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background-color: {t.c("bg_elevated")};
    color: {t.c("text_primary")};
    border: 1px solid {t.c("border")};
    selection-background-color: {t.c("sidebar_active_bg")};
    selection-color: {t.c("accent_cyan")};
    outline: none;
}}

/* === SPIN BOX === */
QSpinBox {{
    background-color: {t.c("input_bg")};
    color: {t.c("text_primary")};
    border: 1px solid {t.c("input_border")};
    border-radius: {t.sp("border_radius")}px;
    padding: {t.sp("padding_sm")}px {t.sp("padding_md")}px;
    font-size: {t.s("font_body")}pt;
}}
QSpinBox:focus {{ border-color: {t.c("accent_cyan")}; }}
QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {t.c("bg_elevated")};
    border: none;
    width: 16px;
}}

/* === LINE EDIT === */
QLineEdit {{
    background-color: {t.c("input_bg")};
    color: {t.c("text_primary")};
    border: 1px solid {t.c("input_border")};
    border-radius: {t.sp("border_radius")}px;
    padding: {t.sp("padding_sm")}px {t.sp("padding_md")}px;
    font-size: {t.s("font_body")}pt;
    selection-background-color: {t.c("sidebar_active_bg")};
    selection-color: {t.c("accent_cyan")};
}}
QLineEdit:focus {{ border-color: {t.c("accent_cyan")}; }}

/* === PROGRESS BAR === */
QProgressBar {{
    background-color: {t.c("bg_elevated")};
    border: 1px solid {t.c("border")};
    border-radius: {t.sp("border_radius")}px;
    text-align: center;
    color: {t.c("text_secondary")};
    font-size: {t.s("font_small")}pt;
    max-height: 16px;
}}
QProgressBar::chunk {{
    background-color: {t.c("accent_cyan")};
    border-radius: {t.sp("border_radius")}px;
}}
QProgressBar#progress_warn::chunk  {{ background-color: {t.c("warning")}; }}
QProgressBar#progress_error::chunk {{ background-color: {t.c("error")}; }}

/* === GROUP BOX === */
QGroupBox {{
    border: 1px solid {t.c("border")};
    border-radius: {t.sp("border_radius_lg")}px;
    margin-top: 1.2em;
    padding: {t.sp("padding_md")}px;
    font-family: "{t.f("body")}", "{t.f("body_fallback")}";
    font-size: {t.s("font_small")}pt;
    font-weight: bold;
    color: {t.c("text_secondary")};
    letter-spacing: 1px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 {t.sp("padding_sm")}px;
    color: {t.c("text_secondary")};
}}

/* === TOOL TIP === */
QToolTip {{
    background-color: {t.c("bg_elevated")};
    color: {t.c("text_primary")};
    border: 1px solid {t.c("border")};
    padding: {t.sp("padding_sm")}px {t.sp("padding_md")}px;
    font-size: {t.s("font_small")}pt;
}}

/* === STATUS BAR === */
QStatusBar {{
    background-color: {t.c("bg_secondary")};
    color: {t.c("text_secondary")};
    font-size: {t.s("font_small")}pt;
    border-top: 1px solid {t.c("border")};
}}

/* === FONT COMBO BOX === */
QFontComboBox {{
    background-color: {t.c("input_bg")};
    color: {t.c("text_primary")};
    border: 1px solid {t.c("input_border")};
    border-radius: {t.sp("border_radius")}px;
    padding: {t.sp("padding_sm")}px {t.sp("padding_md")}px;
    font-size: {t.s("font_body")}pt;
}}
QFontComboBox:focus {{ border-color: {t.c("accent_cyan")}; }}
QFontComboBox QAbstractItemView {{
    background-color: {t.c("bg_elevated")};
    color: {t.c("text_primary")};
    border: 1px solid {t.c("border")};
    selection-background-color: {t.c("sidebar_active_bg")};
    selection-color: {t.c("accent_cyan")};
}}
"""
