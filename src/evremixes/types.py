from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


class Format(StrEnum):
    """File format choices."""

    FLAC = "flac"
    ALAC = "m4a"

    @property
    def menu_name(self) -> str:
        """Return the display name for the format."""
        return "FLAC" if self == Format.FLAC else "ALAC"

    @property
    def display_name(self) -> str:
        """Return the display name for the format."""
        return "FLAC" if self == Format.FLAC else "ALAC"

    @property
    def extension(self) -> str:
        """Return the file extension for the format."""
        return self.value


class TrackType(StrEnum):
    """Track type choices."""

    ORIGINAL = "Originals"
    INSTRUMENTAL = "Instrumentals"
    BOTH = "Both"


class Location(StrEnum):
    """Download location choices."""

    DOWNLOADS = "Downloads folder"
    MUSIC = "Music folder"
    ONEDRIVE = "OneDrive folder"
    CUSTOM = "Custom path"


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
