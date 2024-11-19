#!/usr/bin/env python3

from __future__ import annotations

import contextlib
import json
import os
import platform
import string
import subprocess
from io import BytesIO

import requests
from halo import Halo
from PIL import Image
from termcolor import colored

from .metadata_helper import MetadataHelper

from dsutil.text import print_colored

# URL to the JSON file containing track details
TRACKLIST_URL = "https://gitlab.dannystewart.com/danny/evremixes/raw/main/evtracks.json"


class DownloadHelper:
    """Helper class for downloading tracks."""

    def __init__(self, onedrive_folder: str) -> None:
        self.metadata = MetadataHelper()
        self.onedrive_folder = onedrive_folder

    def download_track_info(self) -> dict[str, list[dict]]:
        """Download the JSON file with track details."""
        try:
            response = requests.get(TRACKLIST_URL, timeout=10)
        except requests.RequestException as e:
            raise SystemExit(e) from e

        track_info = json.loads(response.content)
        track_info["tracks"] = sorted(
            track_info["tracks"], key=lambda track: track.get("track_number", 0)
        )
        return track_info

    def download_cover_art(self, metadata: dict[str, list[dict]]) -> bytes:
        """Download and process the album cover art."""
        # Download the cover art from the URL in the metadata
        cover_response = requests.get(metadata.get("cover_art_url", ""), timeout=10)
        cover_data_original = cover_response.content

        # Resize and convert the cover art to JPEG
        image = Image.open(BytesIO(cover_data_original))
        image = image.convert("RGB")
        image = image.resize((800, 800))

        # Save the resized image as a JPEG and return the bytes
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        return buffered.getvalue()

    def download_tracks(
        self,
        track_info: dict,
        output_folder: str,
        file_extension: str,
        is_instrumental: bool = False,
    ) -> None:
        """
        Download each track from the provided URL and save it to the output folder.

        Args:
            track_info: Loaded track details.
            output_folder: The path to the output folder.
            file_extension: The file extension to download.
            is_instrumental: Whether to download instrumental tracks.
        """
        # If there's only one track, it's a single track album
        if isinstance(track_info, list) and len(track_info) == 1:
            track_info = track_info[0]

        # Create the output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)

        # Remove any existing files with the specified file extension in the output folder
        self.remove_previous_downloads(output_folder)

        # Display the output folder path with ~ for the user's home directory
        home_dir = os.path.expanduser("~")
        display_folder = output_folder.replace(home_dir, "~")
        display_folder = os.path.normpath(display_folder)

        # Determine the file format based on the file extension
        file_format = "Apple Lossless" if file_extension == "m4a" else "FLAC"
        print_colored(f"Downloading in {file_format} to {display_folder}...\n", "cyan")

        # Get the metadata and cover art
        metadata = track_info["metadata"]
        cover_data = self.download_cover_art(metadata)
        total_tracks = len(track_info["tracks"])

        # Display a spinner while downloading each track
        spinner = Halo(spinner="dots")

        # Download each track and apply metadata
        for index, track in enumerate(track_info["tracks"], start=1):
            track_number = str(track.get("track_number", index)).zfill(2)
            original_track_name = track["track_name"]
            track_name = original_track_name

            # For instrumentals, use the instrumental URL and add the suffix
            if is_instrumental:
                file_url = track["inst_url"].rsplit(".", 1)[0] + f".{file_extension}"
                if not track_name.endswith(" (Instrumental)"):
                    track_name += " (Instrumental)"
            else:  # Otherwise, use the regular URL and track name
                file_url = track["file_url"].rsplit(".", 1)[0] + f".{file_extension}"
            # Name the output file with the track number and name
            output_path = os.path.join(
                output_folder, f"{track_number} - {track_name}.{file_extension}"
            )

            # Display the track name and download progress
            spinner.text = colored(f"Downloading {track_name}... ({index}/{total_tracks})", "cyan")
            spinner.start()

            try:  # Download the track file and save it to the output folder
                response = requests.get(file_url, stream=True, timeout=30)
                response.raise_for_status()
                with open(output_path, "wb") as f:
                    f.write(response.content)

                spinner.text = colored("Applying metadata...", "cyan")

                # Apply metadata to the downloaded track
                success = self.metadata.apply_metadata(track, metadata, output_path, cover_data)
                if not success:
                    spinner.fail(colored(f"Failed to add metadata to {track_name}.", "red"))
                    continue
                spinner.succeed(colored(f"Downloaded {track_name}", "green"))

            except requests.RequestException:
                spinner.fail(colored(f"Failed to download {track_name}.", "red"))

        spinner.stop()
        print_colored(
            f"\nAll {total_tracks} remixes downloaded in {file_format} to {display_folder}. Enjoy!",
            "green",
        )

    def download_both_formats_to_onedrive(
        self, track_info: dict[str, list[dict]], file_extensions: list[str]
    ) -> None:
        """Download both file formats and both regular and instrumental tracks directly to OneDrive."""
        # Create the output folders for each file extension
        for file_extension in file_extensions:
            subfolder_name = "ALAC" if file_extension == "m4a" else "FLAC"

            # Download regular tracks
            output_folder = os.path.join(self.onedrive_folder, subfolder_name)
            print()
            self.download_tracks(track_info, output_folder, file_extension, is_instrumental=False)

            # Download instrumental tracks
            instrumental_output_folder = os.path.join(
                self.onedrive_folder, f"Instrumentals {subfolder_name}"
            )
            print()
            self.download_tracks(
                track_info, instrumental_output_folder, file_extension, is_instrumental=True
            )

        self.open_folder_in_os(self.onedrive_folder)

    def download_selected_tracks(
        self, track_info: dict, file_extensions: list[str], base_output_folder: str
    ) -> None:
        """Download the user's chosen selection to the output folder."""
        # Ensure the album name is valid for the output folder
        album_name = track_info["metadata"].get("album_name", "Unknown Album")
        valid_chars = f"-_.() {string.ascii_letters}{string.digits}"

        if base_output_folder is not None:  # Use the selected output folder
            safe_album_name = "".join(c for c in album_name if c in valid_chars)
            output_folder = os.path.join(base_output_folder, safe_album_name)
        else:  # Otherwise, save to OneDrive
            output_folder = self.onedrive_folder
        self.download_tracks(track_info, output_folder, file_extensions[0])
        self.open_folder_in_os(output_folder)

    def remove_previous_downloads(self, output_folder: str) -> None:
        """Remove any existing files with the specified file extension in the output folder."""
        file_extensions = ("flac", "m4a")
        for filename in os.listdir(output_folder):
            if filename.endswith(file_extensions):
                file_path = os.path.join(output_folder, filename)
                try:
                    os.remove(file_path)
                except Exception as e:
                    print_colored(f"Failed to delete {file_path}. Reason: {e}", "red")

    def open_folder_in_os(self, output_folder: str) -> None:
        """Open the output folder in the OS file browser."""
        with contextlib.suppress(Exception):
            os_type = platform.system()
            abspath = os.path.abspath(output_folder)
            if os_type == "Windows":
                subprocess.run(["explorer", abspath], check=False)
            elif os_type == "Darwin":
                subprocess.run(["open", abspath], check=False)
            elif os_type == "Linux" and "DISPLAY" in os.environ:
                subprocess.run(["xdg-open", abspath], check=False)
