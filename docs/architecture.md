# enginedjtools — Architecture

## Language & Framework

**Python 3.11+ with Textual**

Textual (https://textual.textualize.io/) is a modern Python TUI framework that produces
full terminal UIs with CSS-like styling, mouse support, reactive data bindings, and
proper widget layouts — all running in the terminal with a neon-on-black rave aesthetic
that suits a DJ tool perfectly.

Why not a desktop GUI (PyQt5/tkinter)?
- Textual apps start instantly and run anywhere Python runs
- The terminal aesthetic fits the DJ/rave theme naturally
- SQLite interaction is trivial with Python's built-in sqlite3
- No PyInstaller bundling headaches

## Project Structure

```
enginedjtools/
├── src/
│   ├── enginedjtools/
│   │   ├── __init__.py
│   │   ├── app.py              # Main Textual app entry point
│   │   ├── scanner.py          # Engine DJ database discovery
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── connection.py   # SQLite connection management
│   │   │   ├── models.py       # Dataclasses for Track, Playlist etc.
│   │   │   └── queries.py      # All SQL queries
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── backup_debugger.py   # Backup failure diagnosis
│   │   │   └── ...                  # Future tools
│   │   └── ui/
│   │       ├── __init__.py
│   │       ├── screens/
│   │       │   ├── home.py          # Main menu screen
│   │       │   ├── scanner.py       # DB scan results screen
│   │       │   └── backup_debug.py  # Backup debugger screen
│   │       └── theme.py             # Rave colour theme / CSS
├── tests/
├── docs/
├── pyproject.toml
└── README.md
```

## Startup Flow

1. App launches → splash screen with rave animation
2. Scans common Engine DJ locations + all drives for `m.db` / `p.db`
3. Shows discovered databases — user selects active one
4. Main menu appears with tool list

## Tools (Planned)

| Tool | Description |
|------|-------------|
| Backup Debugger | Diagnose why backup fails; scan for bad filenames, check disk space, PRAGMA integrity_check |
| Library Scanner | Browse tracks, playlists, crates |
| Bad Filename Finder | Find tracks with newlines, special chars, illegal Windows chars in paths |
| Manual Backup | Reliable ZIP backup of Database2 to user-chosen location |
| Database Health | Run integrity checks, report stats |

## Theme

Rave / cyberpunk aesthetic:
- Background: near-black `#0a0a0f`
- Primary accent: neon cyan `#00ffff`
- Secondary accent: hot pink / magenta `#ff00ff`
- Warning: acid yellow `#ffff00`
- Error: neon red `#ff0033`
- Font: monospace throughout
- Borders: double-line with neon glow effect via colour contrast
