from __future__ import annotations

from typing import TYPE_CHECKING

from dsutil import configure_traceback
from dsutil.env import DSEnv
from dsutil.shell import handle_keyboard_interrupt

from evremixes.config import EvRemixesConfig
from evremixes.download_helper import DownloadHelper
from evremixes.menu_helper import MenuHelper

if TYPE_CHECKING:
    from evremixes.types import DownloadMode, TrackType

configure_traceback()


class EvRemixes:
    """Evanescence Remix Downloader."""

    def __init__(self) -> None:
        self.env = DSEnv()
        self.env.add_bool("EVREMIXES_ADMIN_DOWNLOAD", attr_name="admin", required=False)

        self.config = EvRemixesConfig(admin=self.env.admin)
        self.menu_helper = MenuHelper(self.config)
        self.download_helper = DownloadHelper(self.config)

    @handle_keyboard_interrupt()
    def run_evremixes(self):
        """Configure options and download remixes."""
        track_type, exts, dest, admin = self.menu_helper.prompt_user_for_selections()
        self.set_download_mode(track_type)

        track_info = self.download_helper.download_album_and_track_info()

        if admin:
            self.download_helper.download_to_onedrive(track_info, exts)
        else:
            self.download_helper.download_selections(track_info, exts, dest)

    def set_download_mode(self, track_type: TrackType) -> None:
        """Set the download mode based on the track type selection."""
        mode_map: dict[TrackType, DownloadMode] = {
            "Regular Tracks": "regular",
            "Instrumentals": "instrumental",
            "Both": "both",
        }
        self.config.download_mode = mode_map[track_type]


def main() -> None:
    """Run the Evanescence Remix Downloader."""
    evremixes = EvRemixes()
    evremixes.run_evremixes()


if __name__ == "__main__":
    main()
