"""Backup Debugger screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Label, Static, DataTable
from textual.containers import Vertical, ScrollableContainer
from textual.worker import Worker, WorkerState

from enginedjtools.tools.backup_debugger import BackupReport, run as run_debug


class BackupDebugScreen(Screen):
    """Diagnose Engine DJ backup failures."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("r", "rerun", "Re-run"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._report: BackupReport | None = None

    def compose(self) -> ComposeResult:
        yield Static("  ◈  BACKUP DEBUGGER", id="app-header")
        yield Static("  Running diagnostics...", id="scan-label")
        yield ScrollableContainer(id="report-container")
        yield Footer()

    def on_mount(self) -> None:
        self._run_diagnostics()

    def action_rerun(self) -> None:
        container = self.query_one("#report-container")
        container.remove_children()
        self.query_one("#scan-label").update("  Running diagnostics...")
        self._run_diagnostics()

    def _run_diagnostics(self) -> None:
        self.run_worker(self._do_run, exclusive=True)

    async def _do_run(self) -> BackupReport:
        lib = self.app.active_library
        return run_debug(lib)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.SUCCESS:
            self._report = event.worker.result
            self._render_report(self._report)

    def _render_report(self, report: BackupReport) -> None:
        self.query_one("#scan-label").update("  Diagnostics complete.")
        container = self.query_one("#report-container")
        container.remove_children()

        def row(label: str, value: str, css_class: str = "") -> Static:
            text = f"  {label:<28} {value}"
            return Static(text, classes=css_class)

        # Disk space
        space_cls = "report-error" if report.low_disk_space else "report-ok"
        container.mount(row("Free disk space:", f"{report.free_space_gb:.1f} GB", space_cls))
        container.mount(row("Database size:", f"{report.db_size_mb:.1f} MB"))

        # Integrity
        m_cls = "report-ok" if report.m_db_integrity.strip() == "ok" else "report-error"
        p_cls = "report-ok" if report.p_db_integrity.strip() == "ok" else "report-error"
        container.mount(row("m.db integrity:", report.m_db_integrity.strip(), m_cls))
        container.mount(row("p.db integrity:", report.p_db_integrity.strip(), p_cls))

        # Test backup
        bk_cls = "report-ok" if report.test_backup_ok else "report-error"
        bk_val = "✓ Backup ZIP succeeded" if report.test_backup_ok else f"✗ {report.test_backup_error}"
        container.mount(row("Test backup:", bk_val, bk_cls))

        # Existing backups
        container.mount(row("Existing backups:", str(len(report.existing_backups))))
        for bk in report.existing_backups[:5]:
            container.mount(Static(f"    {bk.name}"))

        # Problematic tracks
        container.mount(Static(""))
        if report.track_issues:
            container.mount(Static(
                f"  ⚠  {len(report.track_issues)} track(s) with problematic filenames:",
                classes="report-warn",
            ))
            for issue in report.track_issues[:50]:
                container.mount(Static(f"    [{issue.track_id}] {issue.path}"))
                for i in issue.issues:
                    container.mount(Static(f"         → {i}", classes="report-error"))
        else:
            container.mount(Static("  ✓  No problematic filenames found.", classes="report-ok"))
