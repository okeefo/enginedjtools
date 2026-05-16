"""Placeholder panel for tools not yet implemented."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget


class StubPanel(QWidget):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        lbl = QLabel(f"◎  {title.upper()}\n\nComing soon.")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setObjectName("panel_title")
        layout.addWidget(lbl)
