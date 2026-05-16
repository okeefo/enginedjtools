"""SQL query helpers for m.db."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from enginedjtools.db.models import Track


def get_all_tracks(m_db: Path) -> list[Track]:
    tracks: list[Track] = []
    with sqlite3.connect(str(m_db)) as conn:
        conn.row_factory = sqlite3.Row
        for row in conn.execute(
            "SELECT id, path, filename, bpm, length, bitrate, year, "
            "       originDatabaseUuid, originTrackId "
            "FROM Track"
        ):
            tracks.append(Track(
                id=row["id"],
                path=row["path"] or "",
                filename=row["filename"] or "",
                bpm=row["bpm"] or 0.0,
                length=row["length"] or 0,
                bitrate=row["bitrate"] or 0,
                year=row["year"],
                origin_database_uuid=row["originDatabaseUuid"] or "",
                origin_track_id=row["originTrackId"] or 0,
            ))
    return tracks


def integrity_check(db_path: Path) -> str:
    """Run SQLite PRAGMA integrity_check and return result string."""
    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute("PRAGMA integrity_check").fetchall()
    return "\n".join(r[0] for r in rows)
