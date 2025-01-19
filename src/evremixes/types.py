from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TrackType = Literal["Regular Tracks", "Instrumentals", "Both"]

DownloadMode = Literal["regular", "instrumental", "both"]

FileFormat = Literal["flac", "m4a"]

FormatChoice = Literal[
    "FLAC",
    "ALAC (Apple Lossless)",
    "Download all tracks directly to OneDrive",
]

LocationChoice = Literal[
    "Downloads folder",
    "Music folder",
    "OneDrive folder",
    "Enter a custom path",
]


@dataclass
class AlbumInfo:
    """Data for an album."""

    album_name: str
    album_artist: str
    artist_name: str
    genre: Literal["Electronic"]
    year: int
    cover_art_url: str
    tracks: list[TrackMetadata]


@dataclass
class TrackMetadata:
    """Data for a track."""

    track_name: str
    file_url: str
    inst_url: str
    start_date: str
    track_number: int
