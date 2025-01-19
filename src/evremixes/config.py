from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from dsutil.paths import DSPaths


@dataclass
class EvRemixesConfig:
    """Configuration for EvRemixes."""

    TRACKLIST_URL: ClassVar[str] = (
        "https://gitlab.dannystewart.com/danny/evremixes/raw/main/evtracks.json"
    )

    # Whether to download as admin (all tracks and formats direct to OneDrive)
    admin: bool

    # Whether to download instrumentals instead of regular tracks
    instrumentals: bool = False

    # Local folders
    downloads_folder: Path = field(init=False)
    music_folder: Path = field(init=False)

    # OneDrive folders (admin only)
    onedrive_folder: Path = field(init=False)
    onedrive_subfolder: str = "Music/Danny Stewart/Evanescence Remixes"
    onedrive_path: Path = field(init=False)

    def __post_init__(self):
        self.paths = DSPaths("evremixes")
        self.downloads_folder = Path(self.paths.downloads_dir)
        self.music_folder = Path(self.paths.music_dir)
        self.onedrive_folder = Path(self.paths.get_onedrive_path(self.onedrive_subfolder))
        self.onedrive_path = Path(self.onedrive_folder) / self.onedrive_subfolder

        if self.admin:
            from dsutil.text import color

            notice = "Admin mode: saving all versions and formats to custom OneDrive location."
            print(f"[{color('!', "yellow")}] {color(notice, "magenta")}\n")
