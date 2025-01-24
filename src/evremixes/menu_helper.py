#!/usr/bin/env python3

from __future__ import annotations

import platform
from pathlib import Path
from typing import TYPE_CHECKING

import inquirer

from dsutil.paths import DSPaths

from evremixes.config import DownloadConfig
from evremixes.types import Format, Location, TrackType

if TYPE_CHECKING:
    from evremixes.config import EvRemixesConfig


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
        choices = list(TrackType)
        return self._get_selection("Choose track type", choices)

    def _prompt_format(self) -> Format:
        choices = list(Format)
        if platform.system() == "Darwin":
            choices.reverse()

        format_map = {f.menu_name: f for f in choices}
        selected = self._get_selection("Choose format", list(format_map.keys()))

        return format_map[selected]

    def _prompt_location(self) -> Path:
        choices = (
            [Location.DOWNLOADS, Location.MUSIC]
            if platform.system() == "Darwin"
            else [Location.MUSIC, Location.DOWNLOADS]
        )
        choices.append(Location.CUSTOM)
        if self.admin_mode:
            choices.insert(2, Location.ONEDRIVE)

        location = self._get_selection("Choose download location", choices)

        match location:
            case Location.DOWNLOADS:
                return self.paths.downloads_dir
            case Location.MUSIC:
                return self.paths.music_dir
            case Location.ONEDRIVE:
                return self.paths.get_onedrive_path()
            case Location.CUSTOM:
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
