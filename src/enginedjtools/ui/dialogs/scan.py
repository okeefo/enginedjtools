"""Startup library scan dialog."""

from __future__ import annotations

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from enginedjtools.scanner import EngineLibrary


class _ScanWorker(QThread):
    done = pyqtSignal(list)  # list[EngineLibrary]

    def run(self) -> None:
        from enginedjtools.scanner import scan  # noqa: PLC0415
        self.done.emit(scan())


class ScanDialog(QDialog):
    """Scans for Engine DJ libraries on startup.

    Access the chosen library via `.selected_library` after exec_() returns.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Engine DJ Tools — Scanning…")
        self.setModal(True)
        self.setMinimumWidth(520)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.selected_library: EngineLibrary | None = None

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        self._status = QLabel("Scanning for Engine DJ databases…")
        self._status.setObjectName("label_mono")
        layout.addWidget(self._status)

        self._list = QListWidget()
        self._list.hide()
        layout.addWidget(self._list)

        self._browse_btn = QPushButton("Browse manually…")
        self._browse_btn.hide()
        self._browse_btn.clicked.connect(self._browse)
        layout.addWidget(self._browse_btn)

        self._ok_box = QDialogButtonBox(QDialogButtonBox.Ok)
        self._ok_box.hide()
        self._ok_box.accepted.connect(self._accept_selection)
        layout.addWidget(self._ok_box)

        self._worker = _ScanWorker()
        self._worker.done.connect(self._on_scan_done)
        self._worker.start()

    def _on_scan_done(self, libraries: list[EngineLibrary]) -> None:
        if not libraries:
            self._status.setText("No Engine DJ database found.")
            self._browse_btn.show()
            return

        if len(libraries) == 1:
            self.selected_library = libraries[0]
            self._status.setText(f"Found: {libraries[0].root}\n{libraries[0].track_count} tracks")
            self.accept()
            return

        self._status.setText(f"Found {len(libraries)} Engine DJ libraries. Choose one:")
        for lib in libraries:
            item = QListWidgetItem(f"{lib.root}  [{lib.track_count} tracks]")
            item.setData(Qt.UserRole, lib)
            self._list.addItem(item)
        self._list.setCurrentRow(0)
        self._list.show()
        self._ok_box.show()

    def _accept_selection(self) -> None:
        item = self._list.currentItem()
        if item:
            self.selected_library = item.data(Qt.UserRole)
        self.accept()

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Engine Library folder")
        if not path:
            return
        from pathlib import Path  # noqa: PLC0415

        from enginedjtools.scanner import _read_library  # noqa: PLC0415
        lib = _read_library(Path(path))
        if lib:
            self.selected_library = lib
            self.accept()
        else:
            self._status.setText(f"No valid Engine DJ database found at:\n{path}")
