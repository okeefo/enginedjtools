# Engine DJ Backup Failure — Research Notes

## The Problem

When closing Engine DJ, users see: **"Library backup. Unable to backup database. Database is corrupt"**

The progress bar often reaches 98-100% before failing, making it appear to nearly complete.
The user (Keith) specifically noted seeing this consistently and suspects **line breaks / newline
characters in filenames** as the cause — this is plausible and worth investigating directly in the DB.

## Backup Mechanics

### Where backups go
`C:\Users\<username>\Music\Engine Library\Engine Library Backup\`

### What gets backed up
- The `Database2\` folder contents (`.db` files) compressed into a ZIP
- Triggered automatically every 7 days on exit, or manually via:
  Preferences → Library → System → Library Backup

### What does NOT get backed up
- The actual music files
- Databases on external drives or non-primary volumes (major known limitation)

## Known Causes of Backup Failure

### 1. Special / problematic characters in filenames or paths
- International / accented characters: `é è ç ã à â á Õ ô ò Ö ä ü`
- Newlines / carriage returns (`\n`, `\r`) in filenames — Keith's suspected cause
- Windows username containing special characters

### 2. Insufficient disk space
- Engine DJ reports "database corrupt" when the real cause is low disk space
- Reported in v2.3.2; freeing space resolved it
- Check available space on C: before diagnosing anything else

### 3. Database corruption from external causes
- Force-ejecting drives during import/sync
- Third-party tools modifying `.db` files (e.g. Soundswitch)
- Schema mismatch between Engine DJ desktop version and hardware Engine OS version

### 4. Version-specific bugs
- Engine DJ 4.3.2 introduced new backup failures
- No official fix shipped for these

### 5. Accumulated backup folder interference
- Old backups in `Engine Library Backup\` interfering with new backup creation

## Debugging Plan for enginedjtools

### Step 1 — Scan for problematic filenames
Query `m.db` Track table for `path` and `filename` values containing:
```python
import sqlite3, re

SUSPICIOUS = [
    r'\n', r'\r',                     # newlines (Keith's theory)
    r'[^\x00-\x7F]',                  # non-ASCII (accented chars etc.)
    r'[<>:"/\\|?*]',                  # Windows-illegal chars
]
```

### Step 2 — Check disk space
Programmatically check free space on the drive hosting the Engine Library.

### Step 3 — Validate database integrity
```sql
PRAGMA integrity_check;
```
Run against both `m.db` and `p.db` — if this returns anything other than `ok`, the DB is genuinely corrupt.

### Step 4 — Check backup folder state
List contents of `Engine Library Backup\` — old/partial backups may be blocking new ones.

### Step 5 — Attempt manual ZIP of Database2
Replicate what Engine DJ does: ZIP `Database2\` and see if it fails, catching the specific error.

## Proposed Tool: Backup Debugger

A tool in enginedjtools that:
1. Scans `m.db` for all tracks with problematic characters in `path` / `filename`
2. Reports disk space available vs database size
3. Runs `PRAGMA integrity_check` on both databases
4. Lists existing backups and their sizes/dates
5. Performs a test backup ZIP and reports success/failure
6. Offers to fix filenames (rename files + update DB paths) where safe to do so

## Community Consensus

Professional DJs do not trust Engine DJ's built-in backup. Recommended practice:
- Manual copies of the entire `Engine Library` folder
- Multiple redundant copies across drives and cloud storage
- Never rely solely on Engine DJ's backup feature

## References

- https://community.enginedj.com/t/engine-prime-1-6-1-library-backup-unable-to-backup-database-database-is-corrupt/33090
- https://community.enginedj.com/t/back-up-no-longer-working-on-engine-dj-2-3-2-update/44849
- https://community.enginedj.com/t/4-3-2-update-causing-backup-issues/64192
- https://community.enginedj.com/t/engine-dj-is-unreliable-unrecoverable-corrupt-database-issues/65820
- https://community.enginedj.com/t/database-backup-does-not-backup-data-from-a-mounted-non-primary-volume-restore-is-therefore-not-possible/44832
- https://support.denondj.com/en/support/solutions/articles/69000815206-engine-dj-fixing-and-preventing-engine-library-corruption
