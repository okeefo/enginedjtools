"""Animated waveform widget for the topbar."""

from __future__ import annotations

import math
import random

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import QSizePolicy, QWidget


class WaveformWidget(QWidget):
    """Animated frequency-bar waveform. Colors are set by the caller."""

    BAR_COUNT = 36

    def __init__(self, color_a: str = "#00f5ff", color_b: str = "#ff0080", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.color_a = QColor(color_a)
        self.color_b = QColor(color_b)

        self._phases = [random.uniform(0, 2 * math.pi) for _ in range(self.BAR_COUNT)]
        self._freqs = [random.uniform(1.0, 3.5) for _ in range(self.BAR_COUNT)]
        self._t = 0.0

        self.setFixedHeight(36)
        self.setMinimumWidth(120)
        self.setMaximumWidth(280)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setAttribute(0x02000000)  # Qt::WA_TranslucentBackground (avoid flicker)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)  # 20 fps

    def set_colors(self, color_a: str, color_b: str) -> None:
        self.color_a = QColor(color_a)
        self.color_b = QColor(color_b)
        self.update()

    def _tick(self) -> None:
        self._t += 0.08
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        n = self.BAR_COUNT
        total_gap = w * 0.4
        bar_w = max(2, int((w - total_gap) / n))
        gap = max(1, (w - bar_w * n) // (n + 1))

        for i in range(n):
            frac_pos = i / max(n - 1, 1)
            height_frac = 0.2 + 0.8 * (0.5 + 0.5 * math.sin(self._t * self._freqs[i] + self._phases[i]))
            bar_h = max(2, int(h * height_frac))

            x = gap + i * (bar_w + gap)
            y = (h - bar_h) // 2

            # Lerp color_a → color_b across bars
            r = int(self.color_a.red() + frac_pos * (self.color_b.red() - self.color_a.red()))
            g = int(self.color_a.green() + frac_pos * (self.color_b.green() - self.color_a.green()))
            b = int(self.color_a.blue() + frac_pos * (self.color_b.blue() - self.color_a.blue()))
            alpha = int(120 + 135 * height_frac)

            p.fillRect(x, y, bar_w, bar_h, QColor(r, g, b, alpha))

        p.end()
