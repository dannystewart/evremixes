from __future__ import annotations

from .download_helper import DownloadHelper
from .menu_helper import MenuHelper

from dsutil.env import DSEnv
from dsutil.paths import DSPaths
from dsutil.shell import handle_keyboard_interrupt
from dsutil.text import color as colorize


def colored_alert(message: str, color: str = "yellow") -> str:
    """Return a stylized alert message."""
    exclamation = f"[{colorize('!', color)}]"
    return f"{exclamation} {colorize(message, color)}"


class EvRemixes:
    """Evanescence Remix Downloader."""

    def __init__(self) -> None:
        self.env = DSEnv()
        self.paths = DSPaths("evremixes")

        self.initialize_env_vars()
        self.instrumentals = bool(self.env.evremixes_get_instrumentals)
        self.admin = bool(self.env.evremixes_admin_download)
        self.show_env_warnings()

        self.downloads_folder = self.paths.downloads_dir
        self.music_folder = self.paths.music_dir
        self.onedrive_subfolder = "Music/Danny Stewart/Evanescence Remixes"
        self.onedrive_folder = self.paths.get_onedrive_path(self.onedrive_subfolder)

        self.menu_helper = MenuHelper(
            self.downloads_folder,
            self.music_folder,
            self.onedrive_folder,
            self.instrumentals,
            self.admin,
        )
        self.download_helper = DownloadHelper(self.onedrive_folder)
        self.run_evremixes()

    @handle_keyboard_interrupt()
    def run_evremixes(self):
        """Configure options and download remixes."""
        file_extensions, output_folder, get_both_formats = self.menu_helper.get_user_selections()
        track_info = self.download_helper.download_track_info()

        if self.admin or get_both_formats:
            self.download_helper.download_both_formats_to_onedrive(track_info, file_extensions)
        else:
            self.download_helper.download_selected_tracks(
                track_info, file_extensions, output_folder
            )

    def initialize_env_vars(self) -> None:
        """Add and initialize environment variables for admin mode and instrumental downloads.

        NOTE: Admin mode is not going to be helpful for you unless you happen to want all my remixes
        and instrumentals downloaded to exactly the same place in your OneDrive folder as I do. But
        hey, if you do, this is the flag for you, so knock yourself out.

        Environment Variables:
            - `EVREMIXES_ADMIN_DOWNLOAD=1` configures the script to download as admin.
            - `EVREMIXES_GET_INSTRUMENTALS=1` configures the script to download instrumentals.
        """
        self.env.add_var(
            "EVREMIXES_ADMIN_DOWNLOAD",
            required=False,
            default="0",
            var_type=int,
            description="Enable admin download mode (both formats to OneDrive)",
        )
        self.env.add_var(
            "EVREMIXES_GET_INSTRUMENTALS",
            required=False,
            default="0",
            var_type=int,
            description="Enable instrumental downloads only",
        )

    def show_env_warnings(self) -> None:
        """Note currently set environment variables before running the script."""
        if self.admin:
            onedrive_reminder = colored_alert(
                "Admin download (regular and instrumentals to OneDrive in all formats).",
                "magenta",
            )
            print(f"\n{onedrive_reminder}")

        if self.instrumentals:
            instrumental_reminder = colored_alert(
                "Instrumentals environment variable is set, so only instrumentals will\n"
                "    be downloaded! Set EVREMIXES_GET_INSTRUMENTALS=0 to get the full songs.",
                "yellow",
            )
            print(f"\n{instrumental_reminder}")

        if self.admin or self.instrumentals:
            print()


def main() -> None:
    """Run the Evanescence Remix Downloader."""
    EvRemixes()


if __name__ == "__main__":
    main()
