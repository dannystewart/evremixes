from __future__ import annotations

from dsutil import configure_traceback
from dsutil.env import DSEnv
from dsutil.shell import handle_keyboard_interrupt

from evremixes.config import EvRemixesConfig
from evremixes.download_helper import DownloadHelper
from evremixes.menu_helper import MenuHelper

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
        inst, exts, dest, get_both = self.menu_helper.get_user_selections()
        self.config.instrumentals = inst
        track_info = self.download_helper.download_album_and_track_info()

        if self.config.admin or get_both:
            self.download_helper.download_both_formats_to_onedrive(track_info, exts)
        else:
            self.download_helper.download_selected_tracks(track_info, exts, dest)


def main() -> None:
    """Run the Evanescence Remix Downloader."""
    evremixes = EvRemixes()
    evremixes.run_evremixes()


if __name__ == "__main__":
    main()
