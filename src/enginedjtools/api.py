"""Python API exposed to the web UI via pywebview."""

from __future__ import annotations

import re
import sqlite3
import threading
import urllib.parse
from pathlib import Path
from typing import Any

from enginedjtools.scanner import EngineLibrary, _read_library

# ── Local HTTP server for audio playback ──────────────────────────────────────
# WebKit in pywebview blocks cross-path file:// audio; a localhost server fixes
# that and adds Range-request support so seeking works correctly.

_audio_port: int | None = None
_audio_lock  = threading.Lock()
_AUDIO_EXTS  = {'.mp3', '.flac', '.wav', '.aiff', '.aif', '.ogg', '.m4a', '.aac', '.wma', '.opus'}


def _start_audio_server() -> int:
    """Start a minimal localhost HTTP server for audio file serving (once per process)."""
    global _audio_port
    with _audio_lock:
        if _audio_port is not None:
            return _audio_port

        import http.server  # noqa: PLC0415
        import mimetypes    # noqa: PLC0415

        class _Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *_args: object) -> None:
                pass  # silence console output

            def do_GET(self) -> None:  # noqa: N802
                qs  = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                raw = qs.get("p", [""])[0]
                if not raw:
                    self.send_error(400); return
                fp = Path(raw)
                if not fp.is_file() or fp.suffix.lower() not in _AUDIO_EXTS:
                    self.send_error(404); return

                mime, _ = mimetypes.guess_type(str(fp))
                size = fp.stat().st_size
                rng  = self.headers.get("Range", "")

                try:
                    with open(str(fp), "rb") as fh:
                        if rng.startswith("bytes="):
                            parts  = rng[6:].split("-")
                            start  = int(parts[0]) if parts[0] else 0
                            end    = int(parts[1]) if len(parts) > 1 and parts[1] else size - 1
                            length = end - start + 1
                            self.send_response(206)
                            self.send_header("Content-Type",  mime or "audio/mpeg")
                            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                            self.send_header("Content-Length", str(length))
                            self.send_header("Accept-Ranges", "bytes")
                            self.send_header("Access-Control-Allow-Origin", "*")
                            self.end_headers()
                            fh.seek(start)
                            self.wfile.write(fh.read(length))
                        else:
                            self.send_response(200)
                            self.send_header("Content-Type",   mime or "audio/mpeg")
                            self.send_header("Content-Length", str(size))
                            self.send_header("Accept-Ranges",  "bytes")
                            self.send_header("Access-Control-Allow-Origin", "*")
                            self.end_headers()
                            self.wfile.write(fh.read())
                except OSError:
                    pass

        srv = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
        _audio_port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        return _audio_port


class Api:
    """Methods on this class are callable from JS as window.pywebview.api.*"""

    def __init__(self) -> None:
        self._library: EngineLibrary | None = None

    # ── Library discovery ─────────────────────────────────────────────────────

    def get_startup_state(self) -> dict[str, Any]:
        """Single call that returns everything needed at startup.

        Returns active theme data, cached known libraries, and the last-used
        library path — so the JS side can skip scanning on subsequent launches.
        """
        import json  # noqa: PLC0415
        settings = _load_settings()
        theme_name = settings.get("active_theme", "Acid House")
        theme_data = self.load_theme(theme_name)
        if not theme_data:
            theme_name = "Acid House"
            theme_data = json.loads(_bundled_theme_path().read_text(encoding="utf-8"))
        return {
            "active_theme":        {"name": theme_name, "data": theme_data},
            "known_libraries":     settings.get("known_libraries", []),
            "active_library_path": settings.get("active_library"),
        }

    def scan_libraries(self) -> list[dict[str, Any]]:
        """Force a fresh filesystem scan and cache the results."""
        from enginedjtools.scanner import scan  # noqa: PLC0415
        libs = scan()
        result = [_lib_to_dict(lib) for lib in libs]
        settings = _load_settings()
        settings["known_libraries"] = result
        _save_settings(settings)
        return result

    def get_libraries(self) -> list[dict[str, Any]]:
        """Scan the machine for Engine DJ libraries (kept for compatibility)."""
        return self.scan_libraries()

    def select_library(self, path: str) -> dict[str, Any] | None:
        """Set the active library by its root path and persist the choice."""
        lib = _read_library(Path(path))
        if lib:
            self._library = lib
            settings = _load_settings()
            settings["active_library"] = path
            _save_settings(settings)
            return _lib_to_dict(lib)
        return None

    def browse_for_library(self) -> dict[str, Any] | None:
        """Open a folder-picker dialog and try to load a library from the chosen path."""
        import webview  # noqa: PLC0415
        result = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
        if not result:
            return None
        lib_dict = self.select_library(result[0])
        if lib_dict:
            settings = _load_settings()
            known = settings.get("known_libraries", [])
            if not any(k["path"] == lib_dict["path"] for k in known):
                known.append(lib_dict)
                settings["known_libraries"] = known
                _save_settings(settings)
        return lib_dict

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
            "in_onedrive": report.in_onedrive,
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

        # Strip newlines and carriage-returns — the primary Engine DJ backup killer.
        # These cannot exist in real Windows filenames so the cleaned path IS the
        # real file path; no rename needed.
        _STRIP_NEWLINES = re.compile(r"[\r\n]")
        # Characters illegal in Windows filename *components* (not separators).
        _STRIP_ILLEGAL  = re.compile(r'[<>"|?*\x00-\x08\x0b-\x0c\x0e-\x1f]')

        fixed = 0
        skipped_missing: list[int] = []

        try:
            with sqlite3.connect(str(self._library.m_db)) as conn:
                for tid in track_ids:
                    row = conn.execute(
                        "SELECT path, filename FROM Track WHERE id=?", (tid,)
                    ).fetchone()
                    if not row:
                        continue
                    old_path, old_name = row[0] or "", row[1] or ""

                    new_path = _STRIP_ILLEGAL.sub("", _STRIP_NEWLINES.sub("", old_path))
                    new_name = _STRIP_ILLEGAL.sub("", _STRIP_NEWLINES.sub("", old_name))

                    if new_path == old_path and new_name == old_name:
                        continue  # nothing to fix

                    # Safety check: verify the cleaned path actually points to a real file.
                    # DB paths are relative to library root, so resolve before checking.
                    # If it doesn't exist, leave the DB untouched — a broken reference is
                    # better than a silently wrong one.
                    try:
                        resolved = (self._library.root / new_path).resolve()
                        if not resolved.exists():
                            skipped_missing.append(tid)
                            continue
                    except (OSError, ValueError):
                        skipped_missing.append(tid)
                        continue

                    conn.execute(
                        "UPDATE Track SET path=?, filename=? WHERE id=?",
                        (new_path, new_name, tid),
                    )
                    fixed += 1
                conn.commit()
        except sqlite3.Error as e:
            return {"ok": False, "error": str(e)}

        result: dict[str, Any] = {"ok": True, "fixed": fixed}
        if skipped_missing:
            result["skipped"] = len(skipped_missing)
            result["skipped_ids"] = skipped_missing[:20]
        return result

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

    # ── Missing files ─────────────────────────────────────────────────────────────

    def find_missing_files(self) -> dict[str, Any]:
        """Check every track in the DB and return those whose file does not exist on disk."""
        if not self._library:
            return {"error": "No library selected"}
        missing: list[dict[str, Any]] = []
        total = 0
        try:
            with sqlite3.connect(str(self._library.m_db)) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("SELECT id, path, filename FROM Track").fetchall()
            total = len(rows)
            base = self._library.root  # DB paths are relative to the library root
            for row in rows:
                track_id = row["id"]
                path     = row["path"]     or ""
                filename = row["filename"] or ""
                if not path:
                    missing.append({"track_id": track_id, "path": "(no path stored)", "filename": filename})
                    continue
                try:
                    resolved = (base / path).resolve()
                    if not resolved.exists():
                        missing.append({"track_id": track_id, "path": path, "filename": filename})
                except (OSError, ValueError):
                    missing.append({"track_id": track_id, "path": path, "filename": filename})
        except sqlite3.Error as e:
            return {"error": str(e)}
        return {"total": total, "missing": missing}

    def remove_track_from_db(self, track_id: int) -> dict[str, Any]:
        """Remove a single track record from m.db.

        WARNING: This only removes the Track row.  Engine DJ will clean up
        orphaned playlist/crate references the next time it opens the library.
        """
        if not self._library:
            return {"ok": False, "error": "No library selected"}
        try:
            with sqlite3.connect(str(self._library.m_db)) as conn:
                conn.execute("DELETE FROM Track WHERE id=?", (track_id,))
                conn.commit()
            return {"ok": True}
        except sqlite3.Error as e:
            return {"ok": False, "error": str(e)}

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

    # ── Active theme persistence ──────────────────────────────────────────────────

    def get_active_theme(self) -> dict[str, Any]:
        """Return the saved active theme name + full data. Called at startup."""
        import json  # noqa: PLC0415
        settings = _load_settings()
        name = settings.get("active_theme", "Acid House")
        data = self.load_theme(name)
        if not data:
            name = "Acid House"
            data = json.loads(_bundled_theme_path().read_text(encoding="utf-8"))
        return {"name": name, "data": data}

    def set_active_theme(self, name: str) -> None:
        """Persist the user's active theme choice."""
        settings = _load_settings()
        settings["active_theme"] = name
        _save_settings(settings)

    def save_window_size(self, width: int, height: int) -> None:
        """Persist the window viewport size so it can be restored on next launch."""
        settings = _load_settings()
        settings["window_width"]  = int(width)
        settings["window_height"] = int(height)
        _save_settings(settings)

    # ── Engine DJ log viewer ──────────────────────────────────────────────────────

    def get_engine_log_files(self) -> list[dict[str, Any]]:
        """List Engine DJ application log files, newest first (up to 30)."""
        log_dir = _engine_log_dir()
        if not log_dir.exists():
            return []
        logs = sorted(log_dir.glob("Log_*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
        return [
            {"name": p.name, "size_kb": round(p.stat().st_size / 1024, 1)}
            for p in logs[:30]
        ]

    def get_engine_log_content(self, filename: str) -> dict[str, Any]:
        """Read a specific Engine DJ log file. filename must be a bare filename, no path."""
        log_dir = _engine_log_dir()
        # Security: reject any path traversal
        if "/" in filename or "\\" in filename or ".." in filename:
            return {"error": "Invalid filename"}
        path = log_dir / filename
        if not path.exists():
            return {"error": "File not found"}
        try:
            return {"content": path.read_text(encoding="utf-8", errors="replace")}
        except OSError as e:
            return {"error": str(e)}

    # ── Collections (crates / playlists) ─────────────────────────────────────────

    def get_collections(self) -> list[dict[str, Any]]:
        """Return all playlists/crates as a flat list with parentListId for tree building."""
        if not self._library:
            return []
        try:
            with sqlite3.connect(str(self._library.m_db)) as conn:
                rows = conn.execute(
                    "SELECT id, title, parentListId, lastEditTime FROM Playlist ORDER BY title"
                ).fetchall()
            return [
                {"id": r[0], "title": r[1], "parentListId": r[2], "lastEditTime": r[3]}
                for r in rows
            ]
        except sqlite3.Error:
            return []

    def get_collection_tracks(self, list_id: int) -> list[dict[str, Any]]:
        """Return tracks in a specific collection, ordered by artist then title."""
        if not self._library:
            return []
        try:
            with sqlite3.connect(str(self._library.m_db)) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("""
                    SELECT t.id, t.title, t.artist, t.album,
                           COALESCE(t.bpm, t.bpmAnalyzed) AS bpm,
                           t.key, t.length, t.isAnalyzed, t.rating,
                           t.fileType, t.path, t.albumArtId
                    FROM Track t
                    JOIN PlaylistEntity pe ON pe.trackId = t.id
                    WHERE pe.listId = ?
                    ORDER BY t.artist, t.title
                """, (list_id,)).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error:
            return []

    def get_track_info(self, track_id: int) -> dict[str, Any]:
        """Return full metadata for one track, including album art as a data URI."""
        if not self._library:
            return {"error": "No library selected"}
        try:
            with sqlite3.connect(str(self._library.m_db)) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("""
                    SELECT id, title, artist, album, genre, label, composer, remixer,
                           comment, year, rating,
                           COALESCE(bpm, bpmAnalyzed) AS bpm,
                           key, length, fileType, fileBytes, bitrate,
                           path, filename, isAnalyzed, dateAdded, albumArtId
                    FROM Track WHERE id=?
                """, (track_id,)).fetchone()
                if not row:
                    return {"error": "Track not found"}

                info = dict(row)
                art_id = info.pop("albumArtId", None)

                db_path = info.get("path") or ""
                info["abs_path"] = ""
                info["file_url"] = ""
                if db_path:
                    try:
                        abs_path = (self._library.root / db_path).resolve()
                        info["abs_path"] = str(abs_path)
                        if abs_path.is_file():
                            port = _start_audio_server()
                            info["file_url"] = (
                                f"http://127.0.0.1:{port}/"
                                f"?p={urllib.parse.quote(str(abs_path))}"
                            )
                    except Exception:
                        pass

                import base64  # noqa: PLC0415
                info["album_art_b64"] = ""
                if art_id:
                    art_row = conn.execute(
                        "SELECT albumArt FROM AlbumArt WHERE id=?", (art_id,)
                    ).fetchone()
                    if art_row and art_row[0]:
                        b64 = base64.b64encode(bytes(art_row[0])).decode("ascii")
                        info["album_art_b64"] = f"data:image/png;base64,{b64}"

                return info
        except sqlite3.Error as e:
            return {"error": str(e)}

    def get_waveform_data(self, track_id: int) -> dict[str, Any]:
        """Return the overview waveform as [[low, mid, high], ...] amplitude triples (0-255)."""
        if not self._library:
            return {"samples": []}
        try:
            with sqlite3.connect(str(self._library.m_db)) as conn:
                row = conn.execute(
                    "SELECT overviewWaveFormData FROM PerformanceData WHERE trackId=?",
                    (track_id,)
                ).fetchone()
                if not row or not row[0]:
                    return {"samples": []}

                import zlib  # noqa: PLC0415
                raw = bytes(row[0])
                try:
                    data = zlib.decompress(raw[4:])
                except Exception:
                    return {"samples": []}

                # 27-byte header, then N × 3-byte samples: (low, mid, high) freq amplitudes
                HEADER = 27
                n = (len(data) - HEADER) // 3
                samples = [[data[HEADER + i*3], data[HEADER + i*3 + 1], data[HEADER + i*3 + 2]]
                           for i in range(n)]
                return {"samples": samples}
        except sqlite3.Error as e:
            return {"samples": [], "error": str(e)}

    def add_track_to_collection(self, list_id: int, track_id: int) -> dict[str, Any]:
        """Add a track to a collection (append to end of linked list)."""
        if not self._library:
            return {"ok": False, "error": "No library selected"}
        try:
            with sqlite3.connect(str(self._library.m_db)) as conn:
                # Already a member?
                if conn.execute(
                    "SELECT 1 FROM PlaylistEntity WHERE listId=? AND trackId=?",
                    (list_id, track_id)
                ).fetchone():
                    return {"ok": True, "already_present": True}

                # Get this database's UUID
                db_uuid = (conn.execute(
                    "SELECT databaseUuid FROM PlaylistEntity LIMIT 1"
                ).fetchone() or ("",))[0]

                # Current tail of the linked list (nextEntityId = 0 means last)
                tail = conn.execute(
                    "SELECT id FROM PlaylistEntity WHERE listId=? AND nextEntityId=0",
                    (list_id,)
                ).fetchone()

                conn.execute(
                    "INSERT INTO PlaylistEntity (listId, trackId, databaseUuid, nextEntityId, membershipReference)"
                    " VALUES (?,?,?,0,1)",
                    (list_id, track_id, db_uuid)
                )
                new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

                if tail:
                    conn.execute(
                        "UPDATE PlaylistEntity SET nextEntityId=? WHERE id=?",
                        (new_id, tail[0])
                    )
                conn.commit()
            return {"ok": True}
        except sqlite3.Error as e:
            return {"ok": False, "error": str(e)}

    def remove_track_from_collection(self, list_id: int, track_id: int) -> dict[str, Any]:
        """Remove a track from a collection, maintaining the linked-list order."""
        if not self._library:
            return {"ok": False, "error": "No library selected"}
        try:
            with sqlite3.connect(str(self._library.m_db)) as conn:
                entity = conn.execute(
                    "SELECT id, nextEntityId FROM PlaylistEntity WHERE listId=? AND trackId=?",
                    (list_id, track_id)
                ).fetchone()
                if not entity:
                    return {"ok": False, "error": "Track not in collection"}

                entity_id, next_entity_id = entity

                # Re-link the previous node past the deleted one
                prev = conn.execute(
                    "SELECT id FROM PlaylistEntity WHERE listId=? AND nextEntityId=?",
                    (list_id, entity_id)
                ).fetchone()
                if prev:
                    conn.execute(
                        "UPDATE PlaylistEntity SET nextEntityId=? WHERE id=?",
                        (next_entity_id, prev[0])
                    )

                conn.execute("DELETE FROM PlaylistEntity WHERE id=?", (entity_id,))
                conn.commit()
            return {"ok": True}
        except sqlite3.Error as e:
            return {"ok": False, "error": str(e)}

    def search_tracks(self, query: str) -> list[dict[str, Any]]:
        """Full-text search across title, artist, album. Returns up to 200 matches."""
        if not self._library or not query.strip():
            return []
        like = f"%{query.strip()}%"
        try:
            with sqlite3.connect(str(self._library.m_db)) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("""
                    SELECT id, title, artist, album, bpm, key, length, isAnalyzed, rating
                    FROM Track
                    WHERE title LIKE ? OR artist LIKE ? OR album LIKE ?
                    ORDER BY artist, title
                    LIMIT 200
                """, (like, like, like)).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error:
            return []

    def get_track_tree(self, uncollected_only: bool = False) -> list[dict[str, Any]]:
        """Return label→album groups. If uncollected_only, exclude tracks in any collection."""
        if not self._library:
            return []
        try:
            with sqlite3.connect(str(self._library.m_db)) as conn:
                where = (
                    "WHERE t.id NOT IN (SELECT DISTINCT trackId FROM PlaylistEntity)"
                    if uncollected_only else ""
                )
                rows = conn.execute(f"""
                    SELECT COALESCE(t.label, '') AS label,
                           COALESCE(t.album, '') AS album,
                           COUNT(*) AS count
                    FROM Track t
                    {where}
                    GROUP BY label, album
                    ORDER BY label COLLATE NOCASE, album COLLATE NOCASE
                """).fetchall()
            return [{"label": r[0], "album": r[1], "count": r[2]} for r in rows]
        except sqlite3.Error:
            return []

    def get_tracks_in_group(self, label: str, album: str, uncollected_only: bool = False) -> list[dict[str, Any]]:
        """Return tracks for a label+album group. If uncollected_only, exclude tracks in any collection."""
        if not self._library:
            return []
        try:
            with sqlite3.connect(str(self._library.m_db)) as conn:
                conn.row_factory = sqlite3.Row
                extra = (
                    "AND t.id NOT IN (SELECT DISTINCT trackId FROM PlaylistEntity)"
                    if uncollected_only else ""
                )
                rows = conn.execute(f"""
                    SELECT t.id, t.title, t.artist, t.album,
                           COALESCE(t.bpm, t.bpmAnalyzed) AS bpm,
                           t.key, t.length, t.isAnalyzed, t.rating,
                           t.fileType, t.path, t.albumArtId
                    FROM Track t
                    WHERE COALESCE(t.label, '') = ?
                      AND COALESCE(t.album, '') = ?
                      {extra}
                    ORDER BY t.artist, t.title
                """, (label, album)).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error:
            return []

    def get_collections_for_track(self, track_id: int) -> list[dict[str, Any]]:
        """Return all collections with a 'member' flag showing if the track belongs to each."""
        if not self._library:
            return []
        try:
            with sqlite3.connect(str(self._library.m_db)) as conn:
                rows = conn.execute("""
                    SELECT p.id, p.title, p.parentListId,
                           EXISTS(
                               SELECT 1 FROM PlaylistEntity pe
                               WHERE pe.listId = p.id AND pe.trackId = ?
                           ) AS member
                    FROM Playlist p
                    ORDER BY p.title COLLATE NOCASE
                """, (track_id,)).fetchall()
            return [{"id": r[0], "title": r[1], "parentListId": r[2], "member": bool(r[3])}
                    for r in rows]
        except sqlite3.Error:
            return []

    def browse_for_track(self) -> dict[str, Any]:
        """Open a native file picker so the user can select an audio file."""
        import webview  # noqa: PLC0415
        if not self._library:
            return {"error": "No library selected"}
        initial_dir = _resolve_initial_dir(self._library)
        result = webview.windows[0].create_file_dialog(
            webview.OPEN_DIALOG,
            directory=initial_dir,
            allow_multiple=False,
            file_types=(
                "Audio Files (*.mp3;*.flac;*.wav;*.aiff;*.ogg;*.m4a;*.aac;*.wma;*.opus)",
                "All Files (*.*)",
            ),
        )
        if not result:
            return {"path": None}
        return {"path": result[0]}

    def add_track_to_collection_from_file(self, list_id: int, file_path: str) -> dict[str, Any]:
        """Insert a file as a new Track row (isAnalyzed=0) and add it to a collection.

        Engine DJ will auto-queue the track for analysis the next time it starts.
        If the track path already exists in the DB the existing record is reused.
        """
        import datetime  # noqa: PLC0415
        if not self._library:
            return {"ok": False, "error": "No library selected"}

        fp = Path(file_path)
        if not fp.is_file():
            return {"ok": False, "error": "File not found"}

        # Build a path relative to the library-root's parent directory,
        # matching Engine DJ's convention of "../Music/Artist/Track.mp3".
        lib_parent = self._library.root.parent
        try:
            rel = fp.relative_to(lib_parent)
            db_path = "../" + str(rel).replace("\\", "/")
        except ValueError:
            # File is on a different drive/volume — store the absolute path.
            db_path = str(fp)

        try:
            with sqlite3.connect(str(self._library.m_db)) as conn:
                existing = conn.execute(
                    "SELECT id FROM Track WHERE path=?", (db_path,)
                ).fetchone()
                if existing:
                    track_id = existing[0]
                    result = self.add_track_to_collection(list_id, track_id)
                    return {**result, "track_id": track_id, "title": fp.stem, "already_existed": True}

                now_str = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                file_bytes = fp.stat().st_size
                ext = fp.suffix.lstrip(".").lower()

                conn.execute(
                    "INSERT INTO Track"
                    " (title, artist, album, path, filename, fileType, fileBytes,"
                    "  isAnalyzed, isAvailable, dateAdded, dateCreated, rating, year, bpm)"
                    " VALUES (?,?,?,?,?,?,?,0,1,?,?,0,0,0)",
                    (fp.stem, "", "", db_path, fp.name, ext, file_bytes, now_str, now_str),
                )
                new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                conn.commit()

            # Persist the folder so the dialog reopens in the same place.
            settings = _load_settings()
            settings["last_add_track_folder"] = str(fp.parent)
            _save_settings(settings)

            result = self.add_track_to_collection(list_id, new_id)
            return {**result, "track_id": new_id, "title": fp.stem}
        except sqlite3.Error as e:
            return {"ok": False, "error": str(e)}


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


def _settings_path() -> Path:
    return Path.home() / ".enginedjtools" / "settings.json"


def _engine_log_dir() -> Path:
    """Path to Engine DJ's application log directory."""
    import os  # noqa: PLC0415
    local_app = os.environ.get("LOCALAPPDATA")
    if local_app:
        return Path(local_app) / "AIR Music Technology" / "EnginePrime" / "Logs"
    return Path.home() / "AppData" / "Local" / "AIR Music Technology" / "EnginePrime" / "Logs"


def _resolve_initial_dir(library: EngineLibrary) -> str:
    """Return the best initial directory for the Add Track file dialog.

    Priority:
      1. Last-used folder (saved in settings) — walks up to first existing ancestor.
      2. Drive root that holds the Engine Library (e.g. /mnt/h/).
      3. C drive (/mnt/c).
      4. First existing drive letter /mnt/a .. /mnt/z.
      5. User home.
    """
    settings = _load_settings()
    saved = settings.get("last_add_track_folder")
    if saved:
        p = Path(saved)
        while True:
            if p.exists() and p.is_dir():
                return str(p)
            parent = p.parent
            if parent == p:
                break
            p = parent

    # Drive root in WSL: /mnt/<letter>
    parts = library.root.parts
    if len(parts) >= 3 and parts[1] == "mnt":
        drive_root = Path("/mnt") / parts[2]
        if drive_root.exists():
            return str(drive_root)

    for letter in "c" + "abdefghijklmnopqrstuvwxyz":
        d = Path(f"/mnt/{letter}")
        if d.exists():
            return str(d)

    return str(Path.home())


def _load_settings() -> dict:
    import json  # noqa: PLC0415
    p = _settings_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_settings(data: dict) -> None:
    import json  # noqa: PLC0415
    p = _settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
