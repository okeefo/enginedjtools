# Engine DJ Tools — User Guide

## Overview

Engine DJ Tools is a desktop application for managing Denon Engine DJ databases. It reads and writes the same SQLite databases that Engine DJ uses, so changes take effect immediately the next time Engine DJ opens.

> **Always close Engine DJ before making changes** — the app writes directly to `m.db` and conflicts with an open Engine DJ instance can corrupt the database.

---

## Getting Started

1. Launch the app (`enginedjtools` or `python -m enginedjtools.app`)
2. The app scans your drives for Engine DJ databases on startup
3. If multiple libraries are found, select the one you want to work with
4. Use **⟳ RESCAN** if you've connected an external drive after startup
5. Use **Browse…** to manually locate a library folder

### Where Engine DJ stores its database

- **Music folder (OneDrive):** `C:\Users\<you>\Music\Engine Library\Database2\`
- **OneDrive:** `C:\Users\<you>\OneDrive\Music\Engine Library\Database2\`
- **External drives:** `H:\Engine Library\Database2\` (or any drive letter)

The app discovers all of these automatically.

---

## Tools Reference

### Backup Debugger

Diagnoses why Engine DJ's built-in backup fails. Run this first if you see "Unable to backup database" or "database is corrupted" errors.

**What it checks:**

| Check | What it means |
|-------|---------------|
| Free space | < 2 GB free triggers a misleading "corrupt" error |
| DB integrity | `PRAGMA integrity_check` on `m.db` and `p.db` |
| Track filenames | Newlines, carriage returns, and illegal characters that break the ZIP step |
| OneDrive detection | Engine DJ backup fails when the library is inside an OneDrive folder |
| Test ZIP | Actually attempts to ZIP `Database2/` — reproduces the exact failure |
| Existing backups | Lists past backups with sizes |

**OneDrive warning:** If your library is in OneDrive, the backup cycle fails because OneDrive holds file locks during the rename step. Fix: in OneDrive settings → Manage backup, stop backing up your Music folder, or move `Engine Library` to `C:\Users\<you>\Music\` (outside OneDrive).

---

### Bad Filenames

Scans every track in the database for filenames that could cause problems:

- **Newlines / carriage returns** in the stored path — primary cause of backup failure
- **Illegal Windows characters** (`< > " | ? *` and control chars) in filename components

Click **FIX** on a row to strip the problematic characters. Only fixes the database record — the actual file on disk is not renamed (the characters wouldn't be in a real filename anyway).

---

### Missing Files

Scans every track and checks whether the audio file exists on disk. Engine DJ paths are stored relative to the library root, so a track at `../Music/Artist/Track.mp3` is resolved from the library root's parent directory.

- **REMOVE** deletes the Track row from the database (Engine DJ will clean up orphaned playlist references on next open)
- **Remove All Missing** bulk-removes all missing tracks

---

### Manual Backup

Creates a timestamped ZIP of the `Database2/` folder:

```
Engine Library/
  Engine Library Backup/
    manual_backup_20260517_143022.zip
```

Use this before making bulk changes or as a regular scheduled backup. The app's manual backup is independent of Engine DJ's built-in backup.

---

### Library Stats

At-a-glance health check for your library:

- **Total tracks** — full count of all Track records in the database
- **With BPM** — tracks where Engine DJ has detected the tempo (uses `bpmAnalyzed` if the manual BPM field is empty)
- **With Key** — tracks where a musical key (0–23) has been stored
- **With Waveform** — tracks that have overview waveform data in `PerformanceData`
- **Crates / Playlists** — count of collections
- **DB Size** — size of `m.db` on disk
- **Schema Version** — the Engine DJ database schema version

The **Coverage** table shows the percentage and missing count for BPM, Key, and Waveform. Use the **NO BPM / NO KEY / NO WAVEFORM** filters in the Tracks panel to find the missing tracks and re-analyse them in Engine DJ.

---

### Collections, Crates and Playlists — What's the Difference?

In Engine DJ, **Crates** and **Playlists** are stored in exactly the same database table (`Playlist`). They are structurally identical at the database level — the distinction is only in how Engine DJ's own UI presents them.

- **Crates** — unordered containers, like tags or folders. Great for grouping by genre, mood, or source.
- **Playlists** — ordered lists where the track order is preserved.
- **Nesting** — both crates and playlists support sub-folders. A crate can contain sub-crates; a playlist can contain sub-playlists.

**Can a track be in multiple collections?** Yes. A track can belong to any number of collections simultaneously. The `PlaylistEntity` junction table stores one row per (collection, track) pair, so adding a track to a second collection doesn't remove it from the first.

In Engine DJ Tools, all crates and playlists are referred to collectively as **Collections**.

---

### Collections

Browse and manage your Engine DJ playlists and crates.

**Left panel:** Collection tree. Collections are expandable — click the arrow (▸/▾) to expand. Click a collection name to load its tracks.

**Right panel:** Track list for the selected collection.

| Column | Notes |
|--------|-------|
| TITLE | Track title |
| ARTIST | Artist name |
| BPM | Analysed BPM (uses `bpmAnalyzed` if the manual BPM field is empty) |
| KEY | Camelot notation — gold = major, purple = minor |
| TYPE | File format (mp3, flac, wav, etc.) |
| LEN | Duration |

**Search:** Filter the track list by title or artist.

**Add Track (+ ADD TRACK):** Opens a native file picker. Adds the selected file to the database (with `isAnalyzed = 0`) and to the current collection. Engine DJ will auto-queue it for BPM/key analysis next time you open it.

**Remove track (✕):** Removes the track from the collection only — the track record stays in the database.

#### Double-click a track

Opens the embedded media player.

#### Right-click a track

Shows a context menu:

| Option | Action |
|--------|--------|
| INFO | Opens the track info panel (full metadata, album art, waveform) |
| PLAY | Loads the track into the player and starts playback |
| PAUSE / RESUME | Pauses or resumes playback |
| STOP | Stops playback and resets to the beginning |
| ADD TO COLLECTION | Opens the collection picker to add the track to another collection |
| REMOVE FROM COLLECTION | Removes the track from the current collection |

#### Multi-select

- **Ctrl+Click** — toggle a single track in/out of the selection
- **Shift+Click** — select a contiguous range from the last clicked track
- A **selection bar** appears at the bottom showing the count of selected tracks with **ADD TO COLLECTION** (bulk-adds all selected to a collection you pick) and **CLEAR** buttons

---

### Tracks

Shows tracks in your library grouped by **Label → Album**.

**Left panel:** Expandable label tree → album sub-items with track counts.

**Right panel:** Track list for the selected group.

| Column | Notes |
|--------|-------|
| TITLE | Track title |
| ARTIST | Artist name |
| BPM | Analysed BPM |
| KEY | Camelot notation |
| TYPE | File format |
| LEN | Duration |
| COLLECTIONS | Comma-separated list of all collections the track belongs to. Empty = uncollected. |

**ALL / UNCOLLECTED toggle:** Switch between showing every track in the library or only tracks not yet added to any collection. Use this to find imported-but-unorganised tracks.

**Quality filters:**

| Filter | What it shows |
|--------|--------------|
| ALL | All tracks in the selected group |
| NO BPM | Tracks where Engine DJ has not yet determined the BPM |
| NO KEY | Tracks where no musical key has been detected |
| NO WAVEFORM | Tracks that haven't been fully analysed (no overview waveform stored) |

Use these to find tracks that still need Engine DJ analysis. Open Engine DJ and right-click → Re-analyse to fix them.

**Multi-select:** Same Ctrl+Click / Shift+Click behaviour as the Collections panel — use the selection bar to bulk-add to a collection.

Use this panel to discover tracks you've imported but haven't organised yet.

---

### Media Player

The media player strip appears at the top of the content area (below the toolbar) when a track is loaded, and **persists across panel switches** — you can navigate between Collections and Tracks without interrupting playback.

**Controls:**

| Button | Action |
|--------|--------|
| ▶ / ⏸ | Play / Pause |
| ⏹ | Stop (resets to beginning) |
| ⏏ | Eject — unloads the track and hides the player |
| ▼ HIDE | Hides the player strip (only available when stopped/paused) |
| 🔊 slider | Volume |

**Waveform:** The coloured waveform is drawn from the pre-analysed data stored in `PerformanceData.overviewWaveFormData`:
- Orange-red = low frequency (bass)
- Green = mid frequency
- Cyan = high frequency (treble)

**Seeking:** Click anywhere on the waveform to jump to that position. Click and drag the needle to scrub.

**Technical note:** Audio is served via a local HTTP server (`127.0.0.1`) to work around WebKit's `file://` cross-path restrictions. Seeking requires Range request support, which this server provides.

---

### Track Info Panel

Right-click → **INFO** to open a full detail panel for a track.

Shows: title, artist, album, genre, label, year, BPM, key (musical name + Camelot), length, file type, bitrate, file size, analysed status, date added, full file path.

Also shows: album art (from the Engine DJ database) and the overview waveform.

---

### Engine Logs

Browses Engine DJ's application log files at:

```
%LOCALAPPDATA%\AIR Music Technology\EnginePrime\Logs\Log_*.txt
```

Log files are named with the session **start** timestamp. Select a log from the dropdown to view it.

**Warnings only** checkbox: filters to show only lines containing `[W]` (warnings) or `[E]` (errors).

Colour coding:
- Yellow = warnings `[W]`
- Red = errors `[E]`
- Grey = informational

---

### Settings

Colour theme editor. Adjust the CSS colour variables that define the UI's appearance. Save as a named theme; switch between themes from the dropdown.

The default theme is **Acid House** (dark cyberpunk with neon cyan accents).

Bundled themes (read-only):

| Theme | Style |
|-------|-------|
| Acid House | Dark, neon cyan — default |
| Deep Space | Dark purple, cosmic |
| Carbon | Dark IBM grey |
| Daylight | Light blue, clean |
| Warm Paper | Light cream, editorial |

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `F1` | Open the User Manual |
| `Escape` | Close any open modal, context menu, or info panel |
| `Ctrl+Click` | Toggle a single track in/out of the selection |
| `Shift+Click` | Select a contiguous range of tracks |
| `Double-click` | Open the waveform player for a track |

---

## Key Concepts

### Engine DJ key numbering

Engine DJ stores the musical key as an integer 0–23:

| Integer | Key | Camelot |
|---------|-----|---------|
| 0 | C major | 8B |
| 1 | D♭ major | 3B |
| 2 | D major | 10B |
| 3 | E♭ major | 5B |
| 4 | E major | 12B |
| 5 | F major | 7B |
| 6 | F♯ major | 2B |
| 7 | G major | 9B |
| 8 | A♭ major | 4B |
| 9 | A major | 11B |
| 10 | B♭ major | 6B |
| 11 | B major | 1B |
| 12 | C minor | 5A |
| 13 | C♯ minor | 12A |
| 14 | D minor | 7A |
| 15 | E♭ minor | 2A |
| 16 | E minor | 9A |
| 17 | F minor | 4A |
| 18 | F♯ minor | 11A |
| 19 | G minor | 6A |
| 20 | A♭ minor | 1A |
| 21 | A minor | 8A |
| 22 | B♭ minor | 3A |
| 23 | B minor | 10A |

### Track analysis

Engine DJ analyses tracks for BPM and key when they are added or when you right-click → **Re-analyse**. If you add a track via the app's **Add Track** button, it is inserted with `isAnalyzed = 0`, which tells Engine DJ to queue it for analysis the next time you open the library.

### OneDrive and Engine DJ

Engine DJ's backup process creates a temporary folder, rotates it, and deletes the old backup. OneDrive holds file locks during this cycle, which causes the rotation to fail with "database corrupted". The two known fixes:

1. **Exclude from OneDrive sync:** OneDrive settings → Manage backup → stop backing up Music folder
2. **Move the library:** Move `Engine Library` to `C:\Users\<you>\Music\` (outside the OneDrive folder)

After moving, re-open Engine DJ and point it to the new location (it will ask on first launch if the old path is missing).

### Two Engine DJ libraries

If you use both an external drive and your Music folder, you may have two separate Engine DJ databases — one for local files and one for streaming services. The app discovers both and lets you switch between them. Changes in one database do not affect the other.
