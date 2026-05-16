# Engine DJ Database Format

Research notes for enginedjtools development.

## Overview

Engine DJ (formerly Engine Prime) stores all DJ metadata in SQLite databases.
The actual audio files are NOT modified — everything lives in the database.

## Database Location

- **Windows:** `C:\Users\<username>\Music\Engine Library\Database2\`
- **macOS:** `~/Music/Engine Library/Database2/`

## Database Files

| File | Purpose |
|------|---------|
| `m.db` | Main metadata — tracks, playlists, crates, history, artwork |
| `p.db` | Performance data — beatgrids, cues, loops, waveforms (zlib-compressed blobs) |
| `sm.db` / `sp.db` | Serato-related variants |
| `*.db-journal` | SQLite rollback journals (temporary) |

## m.db Schema (Key Tables)

### Track
Core table for all audio files.
- `id` — SQLite PK (do NOT use as a foreign key in external tools)
- `playOrder`, `length`, `bpm`, `year`, `path`, `filename`
- `bitrate`, `bpmAnalyzed`, `trackType`, `isExternalTrack`
- `originDatabaseUuid`, `originTrackId` ← **Use these as the natural key**

### MetaData
Text metadata stored as key-value pairs.
- `id` (FK to Track.id), `type` (int enum), `text`
- Types include: title, artist, album, genre, comment, label, mix, composer, remixer

### MetaDataInteger
Numeric metadata key-value pairs.
- `id` (FK to Track.id), `type` (int enum), `value`
- Types include: musical key, rating, year, disc number, track number

### AlbumArt
- `id`, `hash`, `albumArt` (BLOB)

### Playlist / Crate
As of Engine DJ v2.0 crates and playlists were merged into a single list type.
- `id`, `title`, `parentListId`, `path` (ordered sequence of parent titles)
- `isPersisted`, `lastEditTime`, `isFolder`

### PlaylistTrackList
- `playlistId`, `trackId`, `trackIdInOriginDatabase`, `positionInPlaylist`

### Historylist / HistorylistTrackList
Session play history records.

## p.db Schema (Performance Data)

### PerformanceData
All analysis data is stored as **zlib-compressed binary blobs**.
- `id` (FK to m.db Track.id)
- `isAnalyzed`, `isRendered`
- `trackData` — BLOB: overall track analysis
- `highResolutionWaveFormData` — BLOB: high-res waveform
- `overviewWaveFormData` — BLOB: overview waveform
- `beatData` — BLOB: beat grid / tempo map
- `quickCues` — BLOB: hot cues (up to 8)
- `loops` — BLOB: stored loops
- `hasSeratoValues`, `hasRekordboxValues`, `hasTraktorValues`

### Blob Format
Each compressed blob: `[4 bytes uncompressed length][zlib-compressed data]`
Must decompress with `zlib.decompress()` to read cues, loops, beatgrids.

## Critical Rules for External Tools

1. **Never use SQLite `id` as a foreign key** — use `{originTrackId, originDatabaseUuid}` as the natural key
2. **Never modify the database schema** — Engine DJ will refuse to load databases with modified schemas
3. **All performance data requires zlib decompression** — no plain SQL access to cue points

## Format Versions

| Version | Notes |
|---------|-------|
| v1.6.0 | Legacy, incompatible with Engine DJ 4.0+ |
| v2.20.2 | Current schema version |

## Interoperability

- Engine DJ stores **everything** in the database — moving files without the database loses all cues/beatgrids/loops
- Unlike Serato/Traktor, **nothing is written back to audio file tags**
- Engine DJ 5.0 added an Import Assistant for Rekordbox, Serato, and Traktor

## Resources

- [Mixxx Engine Library Format Wiki](https://github.com/mixxxdj/mixxx/wiki/Engine-Library-Format) — best public schema docs
- [Official Third-Party Tool Guidelines](https://support.denondj.com/en/support/solutions/articles/69000834165-engine-dj-v3-0-support-for-third-party-database-tools)
- [PirateEngine (Python)](https://github.com/ssabug/piratengine) — Python tools for m.db
