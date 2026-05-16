"""Rave / cyberpunk colour theme for enginedjtools."""

RAVE_CSS = """
/* ── Global ─────────────────────────────────────────────────── */
Screen {
    background: #0a0a0f;
    color: #e0e0e0;
}

/* ── Header ─────────────────────────────────────────────────── */
#app-header {
    background: #0a0a0f;
    color: #00ffff;
    text-style: bold;
    border-bottom: solid #00ffff;
    height: 3;
    content-align: center middle;
}

/* ── Footer ─────────────────────────────────────────────────── */
#app-footer {
    background: #0a0a0f;
    color: #444466;
    border-top: solid #1a1a2e;
    height: 1;
}

/* ── Menu items ──────────────────────────────────────────────── */
.menu-item {
    background: #0f0f1a;
    color: #00ffff;
    border: solid #1a1a3e;
    margin: 0 2 1 2;
    padding: 1 2;
    height: 5;
}

.menu-item:hover {
    background: #1a1a3e;
    border: solid #00ffff;
    color: #ffffff;
}

.menu-item:focus {
    background: #1a1a3e;
    border: solid #ff00ff;
    color: #ff00ff;
}

.menu-item .item-title {
    text-style: bold;
    color: #00ffff;
}

.menu-item .item-desc {
    color: #888899;
}

/* ── Status panel ────────────────────────────────────────────── */
#status-panel {
    background: #0f0f1a;
    border: solid #1a1a3e;
    margin: 1 2;
    padding: 1 2;
}

/* ── DB path label ───────────────────────────────────────────── */
#db-path {
    color: #ff00ff;
    text-style: italic;
}

/* ── Scan progress ───────────────────────────────────────────── */
#scan-label {
    color: #ffff00;
    text-style: bold;
}

/* ── Report panels ───────────────────────────────────────────── */
.report-ok {
    color: #00ff88;
    text-style: bold;
}

.report-warn {
    color: #ffff00;
    text-style: bold;
}

.report-error {
    color: #ff0033;
    text-style: bold;
}

/* ── DataTable ───────────────────────────────────────────────── */
DataTable {
    background: #0a0a0f;
    color: #ccccdd;
}

DataTable > .datatable--header {
    background: #1a1a3e;
    color: #00ffff;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: #2a2a5e;
    color: #ffffff;
}

/* ── Buttons ─────────────────────────────────────────────────── */
Button {
    background: #1a1a3e;
    color: #00ffff;
    border: solid #00ffff;
}

Button:hover {
    background: #00ffff;
    color: #0a0a0f;
}

Button.-primary {
    background: #1a1a3e;
    color: #ff00ff;
    border: solid #ff00ff;
}

Button.-primary:hover {
    background: #ff00ff;
    color: #0a0a0f;
}
"""
