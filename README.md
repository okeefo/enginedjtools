# Engine DJ Tools

A rave-themed terminal UI for managing and debugging Denon Engine DJ databases.

## Features

- **Auto-discovery** — scans your drives for Engine DJ databases on startup
- **Backup Debugger** — diagnoses why Engine DJ's built-in backup fails:
  - Scans all track filenames for newlines, illegal characters, non-ASCII
  - Checks disk space (low space triggers misleading "corrupt" error)
  - Runs SQLite `PRAGMA integrity_check` on `m.db` and `p.db`
  - Attempts a test ZIP backup and reports the exact error if it fails
  - Lists existing backups
- **Bad Filename Finder** — surface tracks with problematic paths
- **Library Stats** — track counts, database health at a glance

## Requirements

- Python 3.11+
- Windows (primary target — Engine DJ is Windows/macOS)

## Install

```bash
pip install -e .
```

## Run

```bash
enginedjtools
```

Or directly:

```bash
python -m enginedjtools.app
```

## Database Location

Engine DJ stores its databases at:
- `C:\Users\<you>\Music\Engine Library\Database2\m.db` (metadata)
- `C:\Users\<you>\Music\Engine Library\Database2\p.db` (performance: cues, beatgrids, waveforms)

See `docs/engine-dj-database-format.md` for full schema notes.

## Backup Failure Debugging

See `docs/backup-failure-research.md` for known causes and the debugging approach.

The most common causes of "Unable to backup database" on exit:
1. Newlines or carriage returns in track filenames
2. Special/accented characters in filenames or Windows username
3. Insufficient disk space (Engine DJ reports "corrupt" instead of "no space")
4. Genuine database corruption (caught by `PRAGMA integrity_check`)
