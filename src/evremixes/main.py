from __future__ import annotations

from dsutil import configure_traceback
from dsutil.env import DSEnv

from evremixes.config import EvRemixesConfig
from evremixes.download_helper import DownloadHelper
from evremixes.menu_helper import MenuHelper

configure_traceback()


class EvRemixes:
    """Evanescence Remix Downloader."""

    def __init__(self) -> None:
        # Initialize environment variables
        self.env = DSEnv()
        self.env.add_bool("EVREMIXES_ADMIN", attr_name="admin", required=False)

        # Initialize config and helpers
        self.config = EvRemixesConfig(admin=self.env.admin)
        self.menu_helper = MenuHelper(self.config)
        self.download_helper = DownloadHelper(self.config)

        # Get track metadata and download config
        self.album_info = self.download_helper.metadata.download_metadata()

        # Only get menu selections if not in admin mode
        if not self.config.admin:
            self.download_config = self.menu_helper.get_selections()

    def download_tracks(self) -> None:
        """Download the tracks."""
        if self.config.admin:
            self.download_helper.download_tracks_for_admin(self.album_info)
        else:
            self.download_helper.download_tracks(self.album_info, self.download_config)


def main() -> None:
    """Run the Evanescence Remix Downloader."""
    evremixes = EvRemixes()
    evremixes.download_tracks()
