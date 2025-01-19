#!/usr/bin/env python3

from __future__ import annotations

import platform
from pathlib import Path
from typing import TYPE_CHECKING

import inquirer

from dsutil.paths import DSPaths

from evremixes.config import DownloadConfig

if TYPE_CHECKING:
    from pathlib import Path

    from evremixes.config import EvRemixesConfig
    from evremixes.types import FormatChoice, LocationChoice, TrackType


class MenuHelper:
    """Helper class for presenting menu options to the user."""

    def __init__(self, config: EvRemixesConfig):
        """Initialize the MenuHelper class."""
        self.paths = DSPaths("evremixes")
        self.admin_mode: bool = config.admin

    def get_selections(self) -> DownloadConfig:
        """Get all user selections in sequence."""
        track_type = self._prompt_track_type()
        format_choice = self._prompt_format()
        location = self._prompt_location()

        return DownloadConfig(track_type, format_choice, location)

    def _prompt_track_type(self) -> TrackType:
        choices: list[TrackType] = ["Regular Tracks", "Instrumentals", "Both"]
        return self._get_selection("Choose track type", choices)

    def _prompt_format(self) -> FormatChoice:
        choices: list[FormatChoice] = ["FLAC", "ALAC (Apple Lossless)"]
        if platform.system() == "Darwin":
            choices.reverse()
        return self._get_selection("Choose format", choices)

    def _prompt_location(self) -> Path:
        choices: list[LocationChoice] = ["Downloads folder", "Music folder", "Custom path"]
        if self.admin_mode:
            choices.insert(2, "OneDrive folder")

        location = self._get_selection("Choose download location", choices)

        match location:
            case "Downloads folder":
                return self.paths.downloads_dir
            case "Music folder":
                return self.paths.music_dir
            case "OneDrive folder":
                return self.paths.get_onedrive_path()
            case "Custom path":
                return inquirer.text("Enter custom path").expanduser()

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
