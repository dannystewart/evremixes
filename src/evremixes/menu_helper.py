from __future__ import annotations

import platform
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import inquirer
from polykit.formatters import print_color

from evremixes.types import AudioFormat, DownloadLocation, TrackVersions

if TYPE_CHECKING:
    from evremixes.config import DownloadConfig


class MenuHelper:
    """Helper class for presenting menu options to the user."""

    def __init__(self, config: DownloadConfig):
        """Initialize the MenuHelper class."""
        self.paths = config.paths
        self.admin_mode = config.is_admin

    def prompt_for_versions(self) -> TrackVersions:
        """Prompt the user to choose which versions to download."""
        choices = list(TrackVersions)
        result = self._get_selection("Choose which versions to download", choices)
        if result == TrackVersions.QUIT:
            print_color("Goodbye!", "blue")
            sys.exit(0)
        return result

    def prompt_for_format(self) -> AudioFormat:
        """Prompt the user to choose an audio format."""
        choices = list(AudioFormat)
        if platform.system() == "Darwin":
            choices.reverse()

        format_map = {f.menu_choice: f for f in choices}
        selected = self._get_selection("Choose a format", list(format_map.keys()))

        return format_map[selected]

    def prompt_for_location(self) -> Path:
        """Prompt the user to choose a download location."""
        choices = (
            [DownloadLocation.DOWNLOADS, DownloadLocation.MUSIC]
            if platform.system() == "Darwin"
            else [DownloadLocation.MUSIC, DownloadLocation.DOWNLOADS]
        )
        choices.append(DownloadLocation.CUSTOM)
        if self.admin_mode:
            choices.insert(2, DownloadLocation.ONEDRIVE)

        location = self._get_selection("Choose download location", choices)

        match location:
            case DownloadLocation.DOWNLOADS:
                return self.paths.downloads_dir
            case DownloadLocation.MUSIC:
                return self.paths.from_music("Danny Stewart")
            case DownloadLocation.ONEDRIVE:
                return self.paths.onedrive_dir
            case DownloadLocation.CUSTOM:
                return Path(inquirer.text("Enter custom path")).expanduser()

    def _get_selection[T](self, message: str, choices: list[T]) -> T:
        """Get a user selection from a list of choices.

        Raises:
            SystemExit: If the user cancels the selection.
        """
        question = [inquirer.List("selection", message=message, choices=choices, carousel=True)]

        result = inquirer.prompt(question)
        if result is None:
            raise SystemExit

        return result["selection"]
