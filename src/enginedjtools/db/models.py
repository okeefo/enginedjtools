"""Dataclasses mirroring the Engine DJ m.db schema."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Track:
    id: int
    path: str
    filename: str
    bpm: float
    length: int          # seconds
    bitrate: int
    year: int | None
    origin_database_uuid: str
    origin_track_id: int

    @property
    def display_path(self) -> str:
        return self.path or self.filename


@dataclass
class Playlist:
    id: int
    title: str
    parent_id: int | None
    is_folder: bool
