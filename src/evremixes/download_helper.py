#!/usr/bin/env python3

from __future__ import annotations

import contextlib
import json
import os
import platform
import string
import subprocess
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

import requests
from halo import Halo
from PIL import Image
from termcolor import colored

from dsutil.text import print_colored

from evremixes.metadata_helper import MetadataHelper
from evremixes.types import AlbumInfo, TrackMetadata

if TYPE_CHECKING:
    from evremixes.audio_data import FileFormat
    from evremixes.config import EvRemixesConfig


class DownloadHelper:
    """Helper class for downloading tracks."""

    def __init__(self, config: EvRemixesConfig) -> None:
        self.metadata = MetadataHelper()
        self.config = config

    @property
    def supported_formats(self) -> dict[FileFormat, str]:
        """Map file extensions to their display names."""
        return {"flac": "FLAC", "m4a": "ALAC (Apple Lossless)"}

    def get_format_display_name(self, extension: FileFormat) -> str:
        """Get the user-friendly name for a file format."""
        return self.supported_formats[extension]

    def get_display_path(self, path: Path) -> str:
        """Convert a path to a user-friendly display format with ~ for home directory."""
        try:
            return f"~/{path.relative_to(Path.home())}"
        except ValueError:
            return str(path)

    def download_album_and_track_info(self) -> AlbumInfo:
        """Download the JSON file with track details.

        Raises:
            SystemExit: If the download fails.
        """
        try:
            response = requests.get(self.config.TRACKLIST_URL, timeout=10)
        except requests.RequestException as e:
            raise SystemExit(e) from e

        track_data = json.loads(response.content)
        track_data["tracks"] = sorted(
            track_data["tracks"], key=lambda track: track.get("track_number", 0)
        )
        return AlbumInfo(
            album_name=track_data["metadata"]["album_name"],
            album_artist=track_data["metadata"]["album_artist"],
            artist_name=track_data["metadata"]["artist_name"],
            genre=track_data["metadata"]["genre"],
            year=track_data["metadata"]["year"],
            cover_art_url=track_data["metadata"]["cover_art_url"],
            tracks=[TrackMetadata(**track) for track in track_data["tracks"]],
        )

    def download_cover_art(self, cover_url: str) -> bytes:
        """Download and process the album cover art.

        Raises:
            ValueError: If the download or processing fails.
        """
        try:  # Download the cover art from the URL in the metadata
            cover_response = requests.get(cover_url, timeout=10)
            cover_response.raise_for_status()

            # Resize and convert the cover art to JPEG
            image = Image.open(BytesIO(cover_response.content))
            image = image.convert("RGB")
            image = image.resize((800, 800))

            # Save the resized image as a JPEG and return the bytes
            buffered = BytesIO()
            image.save(buffered, format="JPEG", quality=95, optimize=True)
            return buffered.getvalue()

        except requests.RequestException as e:
            msg = f"Failed to download cover art: {e}"
            raise ValueError(msg) from e
        except OSError as e:
            msg = f"Failed to process cover art: {e}"
            raise ValueError(msg) from e

    def download_tracks(
        self, album_info: AlbumInfo, output_folder: Path, file_extension: str
    ) -> None:
        """Download each track from the provided URL and save it to the output folder.

        Args:
            album_info: Loaded track details.
            output_folder: The path to the output folder.
            file_extension: The file extension to download.
        """
        # Create the output folder if it doesn't exist
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        # Remove any existing files with the specified file extension
        self.remove_previous_downloads(output_folder)

        # Display the output folder path with ~ for the user's home directory
        display_folder = self.get_display_path(output_folder)

        # Determine the file format based on the file extension
        file_format = "Apple Lossless" if file_extension == "m4a" else "FLAC"
        print_colored(f"Downloading in {file_format} to {display_folder}...\n", "cyan")

        # Get the metadata and cover art
        cover_data = self.download_cover_art(album_info.cover_art_url)
        total_tracks = len(album_info.tracks)

        # Display a spinner while downloading each track
        spinner = Halo(spinner="dots")

        # Download each track and apply metadata
        for index, track in enumerate(album_info.tracks, start=1):
            track_number = str(track.track_number).zfill(2)
            track_name = track.track_name

            # Choose URL and name based on download mode
            if self.config.download_mode == "instrumental":
                file_url = track.inst_url.rsplit(".", 1)[0] + f".{file_extension}"
                if not track_name.endswith(" (Instrumental)"):
                    track_name += " (Instrumental)"
            else:
                file_url = track.file_url.rsplit(".", 1)[0] + f".{file_extension}"

            # Name the output file with the track number and name
            output_path = output_folder / f"{track_number} - {track_name}.{file_extension}"

            # Display the track name and download progress
            spinner.text = colored(f"Downloading {track_name}... ({index}/{total_tracks})", "cyan")
            spinner.start()

            try:
                response = requests.get(file_url, stream=True, timeout=30)
                response.raise_for_status()
                output_path.write_bytes(response.content)

                spinner.text = colored("Applying metadata...", "cyan")

                # Apply metadata to the downloaded track
                success = self.metadata.apply_metadata(track, album_info, output_path, cover_data)
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

    def download_to_onedrive(self, album_info: AlbumInfo, file_extensions: list[str]) -> None:
        """Download both formats, and both regular and instrumentals if selected."""
        for file_extension in file_extensions:
            subfolder_name = "ALAC" if file_extension == "m4a" else "FLAC"

            # Download regular tracks
            output_folder = Path(self.config.onedrive_folder) / subfolder_name
            print()
            self.download_tracks(album_info, output_folder, file_extension)

            # Download instrumental tracks
            instrumental_output_folder = (
                Path(self.config.onedrive_folder) / f"Instrumentals {subfolder_name}"
            )
            print()
            self.download_tracks(album_info, instrumental_output_folder, file_extension)

        self.open_folder_in_os(self.config.onedrive_folder)

    def download_selections(
        self, album_info: AlbumInfo, file_extensions: list[str], output_folder: str | Path
    ) -> None:
        """Download the user's chosen selection to the output folder."""
        album_name = album_info.album_name
        valid_chars = f"-_.() {string.ascii_letters}{string.digits}"
        safe_album_name = "".join(c for c in album_name if c in valid_chars)

        if self.config.download_mode == "both":  # Two passes for regular and instrumental
            # Regular tracks
            self.config.download_mode = "regular"
            output_folder = Path(output_folder) / safe_album_name
            self.download_tracks(album_info, output_folder, file_extensions[0])
            print()

            # Instrumental tracks
            self.config.download_mode = "instrumental"
            output_folder = Path(output_folder) / safe_album_name / "Instrumentals"
            self.download_tracks(album_info, output_folder, file_extensions[0])

            # Restore original mode
            self.config.download_mode = "both"
        else:  # Single pass for regular or instrumental only
            output_folder = Path(output_folder) / safe_album_name
            self.download_tracks(album_info, output_folder, file_extensions[0])

        self.open_folder_in_os(output_folder)

    def remove_previous_downloads(self, output_folder: str | Path) -> None:
        """Remove any existing files with the specified file extension in the output folder."""
        output_folder = Path(output_folder)
        file_extensions = (".flac", ".m4a")

        for file_path in output_folder.glob("*"):
            if file_path.suffix.lower() in file_extensions:
                try:
                    file_path.unlink()
                except Exception as e:
                    print_colored(f"Failed to delete {file_path}. Reason: {e}", "red")

    def open_folder_in_os(self, output_folder: str | Path) -> None:
        """Open the output folder in the OS file browser."""
        with contextlib.suppress(Exception):
            output_folder = Path(output_folder).resolve()
            os_type = platform.system()

            if os_type == "Windows":
                subprocess.run(["explorer", str(output_folder)], check=False)
            elif os_type == "Darwin":
                subprocess.run(["open", str(output_folder)], check=False)
            elif os_type == "Linux" and "DISPLAY" in os.environ:
                subprocess.run(["xdg-open", str(output_folder)], check=False)
