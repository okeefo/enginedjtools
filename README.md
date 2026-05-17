# Engine DJ Tools

A cyberpunk-aesthetic desktop app for managing Denon Engine DJ databases — built with Python + pywebview, running as a native desktop window with a full HTML/CSS/JS UI.

---

## Features

| Tool | Description |
|------|-------------|
| **Backup Debugger** | Diagnoses why Engine DJ's built-in backup fails |
| **Bad Filenames** | Finds tracks with illegal chars, newlines, or encoding issues |
| **Missing Files** | Lists tracks whose audio files no longer exist on disk |
| **Manual Backup** | Creates a timestamped ZIP of `Database2/` with one click |
| **Library Stats** | Track counts, schema version, DB size, BPM/year coverage |
| **Collections** | Browse and manage playlists/crates; add/remove tracks; media player |
| **Tracks** | All tracks *not* in any collection, grouped by label → album |
| **Engine Logs** | Browse Engine DJ application log files in-app |
| **Settings** | Theme editor with colour customisation |

---

## Requirements

- Python 3.11+
- Windows (or WSL with a graphical display) — Engine DJ runs on Windows
- `pywebview >= 5.0`

```bash
pip install -e .
```

## Run

```bash
enginedjtools
# or
python -m enginedjtools.app
```

---

## Architecture

```
src/enginedjtools/
  app.py          — pywebview window setup, entry point
  api.py          — Python methods exposed to JS (window.pywebview.api.*)
  scanner.py      — auto-discovers Engine Library locations
  db/
    queries.py    — SQLite helpers (integrity_check, etc.)
  tools/
    backup_debugger.py  — all backup diagnostic logic
  ui/web/
    index.html    — single-page UI (HTML + CSS + JS, self-contained)
  theme/themes/
    acid_house.json     — default cyberpunk colour theme
```

The UI is a **single HTML file** with no external dependencies. All Python logic is invoked via `await pywebview.api.<method>()` from JavaScript.

---

## Database Structure

Engine DJ stores everything in SQLite:

| File | Contents |
|------|----------|
| `Database2/m.db` | Track metadata, playlists, album art |
| `Database2/p.db` | Performance data (waveforms, cue points, beat grids) |

**Key tables in m.db:**

- `Track` — one row per track, including `path` (relative to library root), `bpm`/`bpmAnalyzed`, `key` (integer 0–23), `fileType`, `albumArtId`, `isAnalyzed`
- `Playlist` / `PlaylistEntity` — collections and crates; PlaylistEntity uses a linked list (`nextEntityId`) for ordering
- `AlbumArt` — PNG/JPEG blobs keyed by `albumArtId`
- `PerformanceData` — per-track waveform/cue data; `overviewWaveFormData` is zlib-compressed, 27-byte header + 1024 × 3-byte samples (low/mid/high frequency amplitudes)

**Path format:** The `path` column stores a relative path from the library root's *parent* directory. Example: if the library is at `H:\Engine Library\`, a track at `H:\Music\Artist\Track.mp3` is stored as `../Music/Artist/Track.mp3`.

**Key encoding:** `Track.key` is an integer 0–23 mapping to musical keys (0 = C major, 12 = C minor). See `COL_KEY_MAP` in `index.html` for the full Camelot-wheel mapping.

---

## Backup Failure — Known Causes

Engine DJ's backup creates `Engine Library Backup Temporary`, then tries to rotate it. Common failures:

1. **Newlines or carriage returns** in stored track paths — breaks the ZIP step
2. **OneDrive file locks** — OneDrive holds file handles during the rename/delete cycle, causing "failure while creating rollback databases"
3. **Disk space** — Engine DJ reports "database corrupted" when there isn't enough space for the ZIP
4. **SQLite corruption** — genuine DB issues (caught by `PRAGMA integrity_check`)

**OneDrive fix:** Exclude your `Music\Engine Library` folder from OneDrive sync in OneDrive settings → Manage backup → stop backing up Music. Or move the library entirely off OneDrive.

---

## Audio Playback

The embedded media player serves audio via a local HTTP server (`127.0.0.1:<random-port>`) because pywebview's GTK WebKit blocks cross-path `file://` URLs. The server supports Range requests so seeking works correctly.

---

## Contributing

- Branch: `dev/production-ready` for active development
- The UI is entirely in `src/enginedjtools/ui/web/index.html` — no build step
- Theme variables are CSS custom properties; a new theme is a JSON file in `theme/themes/`
