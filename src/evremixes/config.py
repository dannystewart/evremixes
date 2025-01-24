from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

from dsutil.paths import DSPaths

if TYPE_CHECKING:
    from pathlib import Path

    from evremixes.types import AudioFormat, VersionType


@dataclass
class UserChoices:
    """Dataclass to hold the user's download choices at runtime."""

    version: VersionType
    audio_format: AudioFormat
    location: Path


@dataclass
class EvRemixesConfig:
    """Configuration for the downloader."""

    TRACKLIST_URL: ClassVar[str] = (
        "https://gitlab.dannystewart.com/danny/evremixes/raw/main/evtracks.json"
    )

    # Whether to download as admin (all tracks and formats direct to OneDrive)
    admin: bool

    # Whether to download instrumentals instead of regular tracks
    instrumentals: bool = False

    # Local folders
    downloads_path: Path = field(init=False)
    music_path: Path = field(init=False)

    # OneDrive folders (admin only)
    onedrive_folder: Path = field(init=False)
    onedrive_subfolder: str = "Music/Danny Stewart/Evanescence Remixes"
    onedrive_path: Path = field(init=False)

    def __post_init__(self):
        self.paths = DSPaths("evremixes")
        self.downloads_path = self.paths.downloads_dir
        self.music_path = self.paths.get_music_path("Danny Stewart")
        self.onedrive_folder = self.paths.get_onedrive_path(self.onedrive_subfolder)
        self.onedrive_path = self.onedrive_folder / self.onedrive_subfolder
