"""Scans the local machine for Engine DJ database locations."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EngineLibrary:
    root: Path          # Engine Library folder
    m_db: Path          # m.db path
    p_db: Path          # p.db path
    schema_version: str = ""
    track_count: int = 0

    def __str__(self) -> str:
        return str(self.root)


def _candidate_roots() -> list[Path]:
    """Return all plausible Engine Library root directories to check."""
    candidates: list[Path] = []

    # Standard Windows location
    music = Path(os.environ.get("USERPROFILE", "C:/Users/Default")) / "Music" / "Engine Library"
    candidates.append(music)

    # Check every drive letter A-Z for external drives
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        drive_root = Path(f"{letter}:/") / "Engine Library"
        candidates.append(drive_root)

    # Also check mounted drives under common WSL/Windows mount points
    for mount in Path("/mnt").iterdir() if Path("/mnt").exists() else []:
        candidates.append(mount / "Users" / os.environ.get("USERNAME", "") / "Music" / "Engine Library")
        candidates.append(mount / "Engine Library")

    return candidates


def _read_library(root: Path) -> EngineLibrary | None:
    """Validate and read basic stats from an Engine Library directory."""
    db2 = root / "Database2"
    m_db = db2 / "m.db"
    p_db = db2 / "p.db"

    if not m_db.exists():
        return None

    lib = EngineLibrary(root=root, m_db=m_db, p_db=p_db)

    try:
        with sqlite3.connect(str(m_db)) as conn:
            conn.row_factory = sqlite3.Row
            # Track count
            row = conn.execute("SELECT COUNT(*) FROM Track").fetchone()
            lib.track_count = row[0] if row else 0
            # Schema version from Information table if present
            try:
                row = conn.execute(
                    "SELECT value FROM Information WHERE key='schemaVersion'"
                ).fetchone()
                lib.schema_version = row[0] if row else "unknown"
            except sqlite3.Error:
                lib.schema_version = "unknown"
    except sqlite3.Error:
        return None

    return lib


def scan() -> list[EngineLibrary]:
    """Scan the machine for all Engine DJ databases. Returns discovered libraries."""
    found: list[EngineLibrary] = []
    seen: set[Path] = set()

    for root in _candidate_roots():
        try:
            resolved = root.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        lib = _read_library(root)
        if lib:
            found.append(lib)

    return found
