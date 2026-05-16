"""Engine DJ Tools — application entry point."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from enginedjtools.theme.manager import ThemeManager
from enginedjtools.ui.dialogs.scan import ScanDialog
from enginedjtools.ui.main_window import MainWindow


def main() -> None:
    # High-DPI support
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Engine DJ Tools")
    app.setOrganizationName("okeefo")

    # Load and apply default theme
    theme_mgr = ThemeManager()
    if theme_mgr.theme_names:
        theme_mgr.load(theme_mgr.theme_names[0])
    theme_mgr.apply(app)

    # Startup scan
    scan_dlg = ScanDialog()
    scan_dlg.exec_()
    library = scan_dlg.selected_library

    # Main window
    win = MainWindow(theme_mgr, library)
    win.show()

    # Wire theme changes to live QSS reload
    theme_mgr.theme_changed.connect(lambda _: theme_mgr.apply(app))

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
