"""Backup Debugger panel."""

from __future__ import annotations

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from enginedjtools.scanner import EngineLibrary


class _DiagnosticWorker(QThread):
    result_ready = pyqtSignal(object)  # BackupReport

    def __init__(self, lib: EngineLibrary) -> None:
        super().__init__()
        self._lib = lib

    def run(self) -> None:
        from enginedjtools.tools.backup_debugger import run as run_debug  # noqa: PLC0415
        self.result_ready.emit(run_debug(self._lib))


class BackupDebugPanel(QWidget):
    """Diagnose why Engine DJ backup fails."""

    def __init__(self, library: EngineLibrary | None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._library = library
        self._worker: _DiagnosticWorker | None = None
        self._build_ui()
        if library:
            self._run_diagnostics()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        # Title row
        title_row = QHBoxLayout()
        title = QLabel("◈  BACKUP DEBUGGER")
        title.setObjectName("panel_title")
        title_row.addWidget(title)
        title_row.addStretch()
        self._run_btn = QPushButton("▶  RUN DIAGNOSTICS")
        self._run_btn.setObjectName("primary_button")
        self._run_btn.clicked.connect(self._run_diagnostics)
        self._run_btn.setEnabled(self._library is not None)
        title_row.addWidget(self._run_btn)
        root.addLayout(title_row)

        # Status label
        self._status_lbl = QLabel("Ready." if self._library else "No Engine DJ database selected.")
        self._status_lbl.setObjectName("label_mono")
        root.addWidget(self._status_lbl)

        # Separator
        sep = QFrame()
        sep.setObjectName("separator")
        root.addWidget(sep)

        # Results scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._results_container = QWidget()
        self._results_layout = QVBoxLayout(self._results_container)
        self._results_layout.setSpacing(6)
        self._results_layout.setContentsMargins(0, 0, 0, 0)
        self._results_layout.addStretch()
        scroll.setWidget(self._results_container)
        root.addWidget(scroll, 1)

        # Tracks table (hidden until results arrive)
        self._tracks_section = QWidget()
        tracks_vlayout = QVBoxLayout(self._tracks_section)
        tracks_vlayout.setContentsMargins(0, 0, 0, 0)
        tracks_vlayout.setSpacing(6)

        tracks_heading = QLabel("⚠  PROBLEMATIC TRACKS")
        tracks_heading.setObjectName("section_heading")
        tracks_vlayout.addWidget(tracks_heading)

        self._tracks_table = QTableWidget(0, 3)
        self._tracks_table.setHorizontalHeaderLabels(["ID", "PATH", "ISSUES"])
        self._tracks_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._tracks_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._tracks_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._tracks_table.verticalHeader().setVisible(False)
        self._tracks_table.setAlternatingRowColors(True)
        self._tracks_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tracks_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._tracks_table.setMaximumHeight(240)
        tracks_vlayout.addWidget(self._tracks_table)
        self._tracks_section.hide()
        root.addWidget(self._tracks_section)

    # ── Logic ──────────────────────────────────────────────────────────────────

    def set_library(self, library: EngineLibrary) -> None:
        self._library = library
        self._run_btn.setEnabled(True)
        self._status_lbl.setText("Ready.")

    def _run_diagnostics(self) -> None:
        if not self._library:
            return
        self._clear_results()
        self._run_btn.setEnabled(False)
        self._status_lbl.setText("Running diagnostics…")
        self._tracks_section.hide()
        self._worker = _DiagnosticWorker(self._library)
        self._worker.result_ready.connect(self._on_result)
        self._worker.start()

    def _on_result(self, report) -> None:
        self._run_btn.setEnabled(True)
        self._status_lbl.setText("Diagnostics complete.")
        self._render_report(report)

    def _clear_results(self) -> None:
        while self._results_layout.count() > 1:  # keep the trailing stretch
            item = self._results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _render_report(self, report) -> None:
        t = report

        # Disk space
        space_pct = max(0, min(100, int(100 * (1 - t.free_space_gb / max(t.free_space_gb + t.db_size_mb / 1024, 0.1)))))
        space_bar = self._make_bar(
            f"Free disk space:  {t.free_space_gb:.1f} GB",
            space_pct,
            "progress_error" if t.low_disk_space else None,
        )
        self._add_result(space_bar)

        # DB size
        self._add_result(self._make_row("Database size:", f"{t.db_size_mb:.1f} MB"))

        # Integrity
        m_ok = t.m_db_integrity.strip() == "ok"
        p_ok = t.p_db_integrity.strip() == "ok"
        self._add_result(self._make_row("m.db integrity:", t.m_db_integrity.strip(), ok=m_ok))
        self._add_result(self._make_row("p.db integrity:", t.p_db_integrity.strip(), ok=p_ok))

        # Test backup
        bk_text = "✓  Backup ZIP succeeded" if t.test_backup_ok else f"✗  {t.test_backup_error}"
        self._add_result(self._make_row("Test backup:", bk_text, ok=t.test_backup_ok))

        # Existing backups
        self._add_result(self._make_row("Existing backups:", str(len(t.existing_backups))))
        for bk in t.existing_backups[:5]:
            lbl = QLabel(f"    {bk.name}")
            lbl.setObjectName("label_mono")
            self._add_result(lbl)

        # Tracks
        if t.track_issues:
            self._populate_tracks(t.track_issues)
            self._tracks_section.show()
        else:
            ok_lbl = QLabel("✓  No problematic filenames found.")
            ok_lbl.setObjectName("label_ok")
            self._add_result(ok_lbl)

    def _add_result(self, widget: QWidget) -> None:
        self._results_layout.insertWidget(self._results_layout.count() - 1, widget)

    def _make_row(self, label: str, value: str, ok: bool | None = None) -> QWidget:
        w = QWidget()
        w.setObjectName("card")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(10, 6, 10, 6)

        lbl = QLabel(label)
        lbl.setObjectName("section_heading")
        lbl.setMinimumWidth(200)
        layout.addWidget(lbl)

        val = QLabel(value)
        if ok is True:
            val.setObjectName("label_ok")
        elif ok is False:
            val.setObjectName("label_error")
        else:
            val.setObjectName("label_mono")
        layout.addWidget(val, 1)
        return w

    def _make_bar(self, label: str, pct: int, bar_id: str | None = None) -> QWidget:
        w = QWidget()
        w.setObjectName("card")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(4)

        lbl = QLabel(label)
        lbl.setObjectName("section_heading")
        layout.addWidget(lbl)

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(pct)
        bar.setFormat(f"{pct}% used")
        if bar_id:
            bar.setObjectName(bar_id)
        layout.addWidget(bar)
        return w

    def _populate_tracks(self, issues: list) -> None:
        self._tracks_table.setRowCount(0)
        for issue in issues:
            row = self._tracks_table.rowCount()
            self._tracks_table.insertRow(row)
            self._tracks_table.setItem(row, 0, QTableWidgetItem(str(issue.track_id)))
            self._tracks_table.setItem(row, 1, QTableWidgetItem(issue.path))
            self._tracks_table.setItem(row, 2, QTableWidgetItem("; ".join(issue.issues)))
