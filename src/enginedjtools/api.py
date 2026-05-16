"""Python API exposed to the web UI via pywebview."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from enginedjtools.scanner import EngineLibrary, _read_library


class Api:
    """Methods on this class are callable from JS as window.pywebview.api.*"""

    def __init__(self) -> None:
        self._library: EngineLibrary | None = None

    # ── Library discovery ─────────────────────────────────────────────────────

    def get_libraries(self) -> list[dict[str, Any]]:
        """Scan the machine for Engine DJ libraries."""
        from enginedjtools.scanner import scan  # noqa: PLC0415
        libs = scan()
        return [_lib_to_dict(lib) for lib in libs]

    def select_library(self, path: str) -> dict[str, Any] | None:
        """Set the active library by its root path."""
        lib = _read_library(Path(path))
        if lib:
            self._library = lib
            return _lib_to_dict(lib)
        return None

    def browse_for_library(self) -> dict[str, Any] | None:
        """Open a folder-picker dialog and try to load a library from the chosen path."""
        import webview  # noqa: PLC0415
        result = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
        if not result:
            return None
        return self.select_library(result[0])

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def run_diagnostics(self) -> dict[str, Any]:
        """Run all backup diagnostics. Blocking — JS awaits the returned Promise."""
        if not self._library:
            return {"error": "No library selected"}
        from enginedjtools.tools.backup_debugger import run as run_debug  # noqa: PLC0415
        report = run_debug(self._library)
        return {
            "free_space_gb": round(report.free_space_gb, 2),
            "db_size_mb": round(report.db_size_mb, 2),
            "m_db_integrity": report.m_db_integrity.strip(),
            "p_db_integrity": report.p_db_integrity.strip(),
            "test_backup_ok": report.test_backup_ok,
            "test_backup_error": report.test_backup_error,
            "low_disk_space": report.low_disk_space,
            "existing_backups": [
                {
                    "name": b.name,
                    "size_mb": round(b.stat().st_size / (1024 * 1024), 1),
                }
                for b in report.existing_backups[:10]
            ],
            "track_issues": [
                {
                    "track_id": t.track_id,
                    "path": t.path,
                    "issues": t.issues,
                }
                for t in report.track_issues
            ],
        }

    # ── Fix tracks ────────────────────────────────────────────────────────────

    def fix_track(self, track_id: int) -> dict[str, Any]:
        """Strip newline / illegal characters from a single track's DB path."""
        return self._fix_tracks([track_id])

    def fix_all_tracks(self) -> dict[str, Any]:
        """Fix every track that has problematic filename characters."""
        if not self._library:
            return {"ok": False, "error": "No library selected"}
        try:
            with sqlite3.connect(str(self._library.m_db)) as conn:
                rows = conn.execute("SELECT id FROM Track").fetchall()
            track_ids = [r[0] for r in rows]
            return self._fix_tracks(track_ids)
        except sqlite3.Error as e:
            return {"ok": False, "error": str(e)}

    def _fix_tracks(self, track_ids: list[int]) -> dict[str, Any]:
        if not self._library:
            return {"ok": False, "error": "No library selected"}
        _STRIP = re.compile(r"[\r\n]")
        fixed = 0
        errors: list[str] = []
        try:
            with sqlite3.connect(str(self._library.m_db)) as conn:
                for tid in track_ids:
                    row = conn.execute(
                        "SELECT path, filename FROM Track WHERE id=?", (tid,)
                    ).fetchone()
                    if not row:
                        continue
                    old_path, old_name = row[0] or "", row[1] or ""
                    new_path = _STRIP.sub("", old_path)
                    new_name = _STRIP.sub("", old_name)
                    if new_path != old_path or new_name != old_name:
                        conn.execute(
                            "UPDATE Track SET path=?, filename=? WHERE id=?",
                            (new_path, new_name, tid),
                        )
                        fixed += 1
                conn.commit()
        except sqlite3.Error as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True, "fixed": fixed}

    # ── Theme ─────────────────────────────────────────────────────────────────

    def get_theme(self) -> dict[str, Any]:
        """Load the active theme JSON (used by Settings panel)."""
        import json  # noqa: PLC0415
        theme_path = _bundled_theme_path()
        return json.loads(theme_path.read_text(encoding="utf-8"))

    def get_user_themes(self) -> list[str]:
        """Return names of all available themes."""
        import json  # noqa: PLC0415
        names = []
        for p in _user_themes_dir().glob("*.json"):
            try:
                names.append(json.loads(p.read_text())["name"])
            except Exception:
                pass
        names.insert(0, "Acid House")  # bundled default always first
        return names

    def save_theme_as(self, name: str, data: dict[str, Any]) -> dict[str, Any]:
        """Save a named user theme."""
        import json  # noqa: PLC0415
        dest = _user_themes_dir() / f"{name}.json"
        data["name"] = name
        data["readonly"] = False
        dest.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return {"ok": True}

    def load_theme(self, name: str) -> dict[str, Any]:
        """Load any theme by name — bundled or user."""
        import json  # noqa: PLC0415
        if name == "Acid House":
            return json.loads(_bundled_theme_path().read_text(encoding="utf-8"))
        for p in _user_themes_dir().glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if data.get("name") == name:
                    return data
            except Exception:
                pass
        return {}

    def delete_theme(self, name: str) -> dict[str, Any]:
        """Delete a user theme by name (readonly themes cannot be deleted)."""
        import json  # noqa: PLC0415
        for p in _user_themes_dir().glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if data.get("name") == name:
                    if data.get("readonly", False):
                        return {"ok": False, "error": "Cannot delete a readonly theme"}
                    p.unlink()
                    return {"ok": True}
            except Exception:
                pass
        return {"ok": False, "error": "Theme not found"}

    # ── Track issues ──────────────────────────────────────────────────────────────

    def get_track_issues(self) -> list[dict[str, Any]]:
        """Scan all tracks for bad filenames. Standalone — no full diagnostic run."""
        if not self._library:
            return []
        from enginedjtools.tools.backup_debugger import _scan_tracks  # noqa: PLC0415
        issues = _scan_tracks(self._library.m_db)
        return [{"track_id": t.track_id, "path": t.path, "issues": t.issues} for t in issues]

    # ── Library stats ─────────────────────────────────────────────────────────────

    def get_library_stats(self) -> dict[str, Any]:
        """Return track counts and DB metadata for the Library Stats panel."""
        if not self._library:
            return {"error": "No library selected"}
        try:
            with sqlite3.connect(str(self._library.m_db)) as conn:
                track_count = conn.execute("SELECT COUNT(*) FROM Track").fetchone()[0]
                bpm_count   = conn.execute("SELECT COUNT(*) FROM Track WHERE bpm > 0").fetchone()[0]
                year_count  = conn.execute("SELECT COUNT(*) FROM Track WHERE year IS NOT NULL AND year > 0").fetchone()[0]
                try:
                    crate_count = conn.execute("SELECT COUNT(*) FROM Crate").fetchone()[0]
                except sqlite3.Error:
                    crate_count = 0
                try:
                    playlist_count = conn.execute("SELECT COUNT(*) FROM Playlist").fetchone()[0]
                except sqlite3.Error:
                    playlist_count = 0
            db_size_mb = 0.0
            for db in [self._library.m_db, self._library.p_db]:
                try:
                    db_size_mb += db.stat().st_size / (1024 * 1024)
                except OSError:
                    pass
            return {
                "track_count":    track_count,
                "bpm_count":      bpm_count,
                "year_count":     year_count,
                "crate_count":    crate_count,
                "playlist_count": playlist_count,
                "db_size_mb":     round(db_size_mb, 1),
                "schema_version": self._library.schema_version,
            }
        except sqlite3.Error as e:
            return {"error": str(e)}

    # ── Manual backup ─────────────────────────────────────────────────────────────

    def run_backup(self) -> dict[str, Any]:
        """Create a timestamped ZIP backup of the Database2 folder."""
        import datetime  # noqa: PLC0415
        import zipfile   # noqa: PLC0415
        if not self._library:
            return {"ok": False, "error": "No library selected"}
        db2 = self._library.root / "Database2"
        backup_dir = self._library.root / "Engine Library Backup"
        backup_dir.mkdir(exist_ok=True)
        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = backup_dir / f"manual_backup_{ts}.zip"
        try:
            with zipfile.ZipFile(str(dest), "w", zipfile.ZIP_DEFLATED) as zf:
                for f in db2.rglob("*"):
                    if f.is_file():
                        zf.write(str(f), f.relative_to(db2))
            size_mb = round(dest.stat().st_size / (1024 * 1024), 1)
            return {"ok": True, "path": str(dest), "name": dest.name, "size_mb": size_mb}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def list_backups(self) -> list[dict[str, Any]]:
        """List existing backup ZIPs sorted newest first."""
        if not self._library:
            return []
        backup_dir = self._library.root / "Engine Library Backup"
        if not backup_dir.exists():
            return []
        zips = sorted(backup_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
        return [
            {"name": z.name, "size_mb": round(z.stat().st_size / (1024 * 1024), 1)}
            for z in zips[:20]
        ]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _lib_to_dict(lib: EngineLibrary) -> dict[str, Any]:
    return {
        "path": str(lib.root),
        "m_db": str(lib.m_db),
        "p_db": str(lib.p_db),
        "track_count": lib.track_count,
        "schema_version": lib.schema_version,
    }


def _bundled_theme_path() -> Path:
    return Path(__file__).parent / "theme" / "themes" / "acid_house.json"


def _user_themes_dir() -> Path:
    d = Path.home() / ".enginedjtools" / "themes"
    d.mkdir(parents=True, exist_ok=True)
    return d
