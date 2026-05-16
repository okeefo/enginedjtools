"""Diagnose Engine DJ backup failures."""

from __future__ import annotations

import re
import shutil
import sqlite3
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from enginedjtools.db.queries import integrity_check
from enginedjtools.scanner import EngineLibrary

# Newline variants — primary cause of Engine DJ backup failure
_NEWLINES = re.compile(r'[\r\n]')

# Characters that are truly illegal in Windows filename *components* but that
# also appear legitimately in full paths (: in drive letter, / and \ as
# separators, spaces, etc.).  We check each path component individually so
# we don't false-positive on "H:\Music\Artist.mp3".
# Illegal in a filename component: < > " | ? *  plus control chars except \t
_COMPONENT_ILLEGAL = re.compile(r'[<>"|?*\x00-\x08\x0b-\x0c\x0e-\x1f]')


@dataclass
class TrackIssue:
    track_id: int
    path: str
    issues: list[str]


@dataclass
class BackupReport:
    library: EngineLibrary
    free_space_gb: float
    db_size_mb: float
    m_db_integrity: str
    p_db_integrity: str
    track_issues: list[TrackIssue] = field(default_factory=list)
    existing_backups: list[Path] = field(default_factory=list)
    test_backup_ok: bool = False
    test_backup_error: str = ""

    @property
    def has_integrity_errors(self) -> bool:
        return self.m_db_integrity.strip() != "ok" or self.p_db_integrity.strip() != "ok"

    @property
    def has_problematic_tracks(self) -> bool:
        return len(self.track_issues) > 0

    @property
    def low_disk_space(self) -> bool:
        return self.free_space_gb < 2.0


def _check_free_space(path: Path) -> float:
    """Return free space in GB for the drive containing path."""
    try:
        usage = shutil.disk_usage(str(path))
        return usage.free / (1024 ** 3)
    except OSError:
        return -1.0


def _db_size_mb(lib: EngineLibrary) -> float:
    total = 0
    for db in [lib.m_db, lib.p_db]:
        try:
            total += db.stat().st_size
        except OSError:
            pass
    return total / (1024 ** 2)


def _describe_chars(s: str, pattern: re.Pattern) -> str:
    """Return a short description of matched characters for display."""
    chars = sorted(set(pattern.findall(s)))
    return ", ".join(repr(c) for c in chars[:5])


def _check_path_components(full_path: str) -> list[str]:
    """Check each filename component of a path for truly-illegal characters.

    Splits on both / and \\ so drive letters and separators are not flagged.
    """
    bad: list[str] = []
    # Normalise separators and split into components
    components = re.split(r'[\\/]', full_path)
    for part in components:
        # Skip drive-letter token ("H:", "C:", "") — colon is valid there
        if re.fullmatch(r'[A-Za-z]:', part) or part == "":
            continue
        m = _COMPONENT_ILLEGAL.search(part)
        if m:
            chars = _describe_chars(part, _COMPONENT_ILLEGAL)
            bad.append(f"illegal char in filename component ({chars})")
            break
    return bad


def _scan_tracks(m_db: Path) -> list[TrackIssue]:
    issues: list[TrackIssue] = []
    try:
        with sqlite3.connect(str(m_db)) as conn:
            conn.row_factory = sqlite3.Row
            for row in conn.execute("SELECT id, path, filename FROM Track"):
                track_id = row["id"]
                path     = row["path"]     or ""
                filename = row["filename"] or ""
                combined = path + filename
                found: list[str] = []

                if _NEWLINES.search(combined):
                    found.append("newline/carriage-return in stored path")

                found.extend(_check_path_components(path))
                if filename:
                    m = _COMPONENT_ILLEGAL.search(filename)
                    if m:
                        chars = _describe_chars(filename, _COMPONENT_ILLEGAL)
                        found.append(f"illegal char in filename ({chars})")

                # Non-ASCII (é, ñ, etc.) is valid on NTFS — not flagged

                if found:
                    issues.append(TrackIssue(
                        track_id=track_id,
                        path=path or filename,
                        issues=found,
                    ))
    except sqlite3.Error:
        pass
    return issues


def _list_existing_backups(lib: EngineLibrary) -> list[Path]:
    backup_dir = lib.root / "Engine Library Backup"
    if not backup_dir.exists():
        return []
    return sorted(backup_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)


def _test_backup(lib: EngineLibrary) -> tuple[bool, str]:
    """Attempt to ZIP Database2 to a temp file to replicate what Engine DJ does."""
    import tempfile
    db2 = lib.root / "Database2"
    try:
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        with zipfile.ZipFile(str(tmp_path), "w", zipfile.ZIP_DEFLATED) as zf:
            for f in db2.rglob("*"):
                if f.is_file():
                    zf.write(str(f), f.relative_to(db2))
        tmp_path.unlink(missing_ok=True)
        return True, ""
    except Exception as e:
        return False, str(e)


def run(lib: EngineLibrary) -> BackupReport:
    """Run all backup diagnostics against the given Engine Library."""
    free_gb = _check_free_space(lib.root)
    db_mb = _db_size_mb(lib)

    m_integrity = integrity_check(lib.m_db) if lib.m_db.exists() else "m.db not found"
    p_integrity = integrity_check(lib.p_db) if lib.p_db.exists() else "p.db not found"

    track_issues = _scan_tracks(lib.m_db) if lib.m_db.exists() else []
    existing_backups = _list_existing_backups(lib)
    test_ok, test_err = _test_backup(lib)

    return BackupReport(
        library=lib,
        free_space_gb=free_gb,
        db_size_mb=db_mb,
        m_db_integrity=m_integrity,
        p_db_integrity=p_integrity,
        track_issues=track_issues,
        existing_backups=existing_backups,
        test_backup_ok=test_ok,
        test_backup_error=test_err,
    )
