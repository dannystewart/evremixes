#!/usr/bin/env python3

from __future__ import annotations

import platform
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import inquirer

from dsutil.text import print_colored

if TYPE_CHECKING:
    from evremixes.config import EvRemixesConfig
    from evremixes.types import TrackType


class MenuHelper:
    """Helper class for presenting menu options to the user."""

    def __init__(self, config: EvRemixesConfig):
        """Initialize the MenuHelper class."""
        self.downloads_folder: Path = config.downloads_folder
        self.music_folder: Path = config.music_folder
        self.onedrive_folder: Path = config.onedrive_folder
        self.enable_instrumentals: bool = config.instrumentals
        self.admin_download: bool = config.admin

    def get_user_selections(self) -> tuple[bool, list[str], Path | None, bool]:
        """Present menu options to the user to select track type, file format and download location.

        Returns:
            A tuple containing instrumental flag, file extensions, output folder, and format option.
        """
        try:
            # First get the track type selection
            track_type = self._get_track_type_selection()

            # Pass the track type to format selection
            format_choice, get_both_formats = self._get_format_selection(track_type)

            if not get_both_formats:
                file_extension = ["m4a" if format_choice == "ALAC (Apple Lossless)" else "flac"]
                output_folder = self._get_folder_selection(format_choice, get_both_formats)
            else:
                file_extension = ["m4a", "flac"]
                output_folder = None

        except (KeyboardInterrupt, SystemExit):
            print_colored("\nExiting.", "red")
            sys.exit(1)

        return track_type == "Instrumentals", file_extension, output_folder, get_both_formats

    def _get_track_type_selection(self) -> TrackType:
        """Present the user with track type options.

        Returns:
            The selected track type.
        """
        track_choices: list[Literal["Regular Tracks", "Instrumentals"]] = [
            "Regular Tracks",
            "Instrumentals",
        ]
        return self._get_inquirer_list("track_type", "Choose track type to download", track_choices)  # type: ignore

    def _get_format_selection(self, track_type: TrackType) -> tuple[str, bool]:
        """Presents the user with file format options.

        Args:
            track_type: The selected track type (regular or instrumentals)

        Returns:
            A tuple containing selected format choice and get_both_formats indicator.
        """
        # Define the file format choices
        format_choices = ["FLAC", "ALAC (Apple Lossless)"]

        # Display ALAC first on macOS to match the system's default
        if platform.system() == "Darwin":
            format_choices.reverse()

        # Add the option to download both formats directly to OneDrive
        if self.admin_download:
            onedrive_option = f"Download all {track_type.lower()} directly to OneDrive"
            format_choices.insert(0, onedrive_option)

        format_choice = self._get_inquirer_list(
            "format", "Choose file format to download", format_choices
        )
        get_both_formats = format_choice.startswith("Download all")

        return format_choice, get_both_formats

    def _get_folder_selection(self, format_choice: str, get_both_formats: bool) -> Path | None:
        """Presents the user with download location options based on their format choice.

        Args:
            format_choice: The user's selected file format.
            get_both_formats: Indicator if both formats are selected for download.

        Raises:
            SystemExit: If the user cancels the operation.

        Returns:
            The selected output folder path, or None if the user exits.
        """
        # If downloading both formats, we already know where we're saving to
        if get_both_formats:
            return None

        # Determine the subfolder name based on the format choice
        subfolder_name = "ALAC" if format_choice == "ALAC (Apple Lossless)" else "FLAC"
        folder_choices = ["Downloads folder", "Music folder", "Enter a custom path"]

        # Add the OneDrive folder option if the environment variable is set
        if self.admin_download:
            folder_choices.insert(2, "OneDrive folder")

        folder_choice = self._get_inquirer_list(
            "folder", "Choose download location", folder_choices
        )
        if folder_choice == "Downloads folder":
            return self.downloads_folder
        if folder_choice == "Music folder":
            return self.music_folder
        if folder_choice == "OneDrive folder":
            return Path(self.onedrive_folder) / subfolder_name

        # Ask the user to enter a custom folder path
        custom_folder_question = [
            inquirer.Text(
                "custom_folder",
                message="Enter the full path for your custom download location",
            )
        ]

        # Get the custom folder path from the user and exit if they cancel
        custom_folder_answer = inquirer.prompt(custom_folder_question)
        if custom_folder_answer is None:
            raise SystemExit

        return Path(custom_folder_answer["custom_folder"]).expanduser()

    def _get_inquirer_list(self, menu_options: str, message: str, choices: list[str]) -> str:
        format_question = [
            inquirer.List(menu_options, message=message, choices=choices, carousel=True)
        ]
        format_answer = inquirer.prompt(format_question)
        if format_answer is None:
            raise SystemExit
        return format_answer[menu_options]
