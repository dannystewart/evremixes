#!/usr/bin/env python3

import contextlib
import json
import os
import platform
import string
import subprocess
import sys
from io import BytesIO

import inquirer
import requests
from halo import Halo
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4, MP4Cover
from PIL import Image
from termcolor import colored

# URL to the JSON file containing track details
TRACKLIST_URL = "https://gitlab.dannystewart.com/danny/evremixes/-/raw/main/evtracks.json"

# Define default folders
DOWNLOADS_FOLDER = os.path.expanduser("~/Downloads")
MUSIC_FOLDER = os.path.expanduser("~/Music")

# Enable downloading both sets to OneDrive for fancy people
# Add `EVREMIXES_ADMIN_DOWNLOAD=1` to your environment variables to enable
ADMIN_DOWNLOAD = os.getenv("EVREMIXES_ADMIN_DOWNLOAD", "0") == "1"
ONEDRIVE_PATH = "~/Library/CloudStorage/OneDrive-Personal/Music/Danny Stewart/Evanescence Remixes"
ONEDRIVE_FOLDER = os.path.expanduser(ONEDRIVE_PATH)

# Enable downloading instrumentals (add `EVREMIXES_GET_INSTRUMENTALS=1` to your environment variables to enable)
ENABLE_INSTRUMENTALS = os.getenv("EVREMIXES_GET_INSTRUMENTALS", "0") == "1"


def print_color(text: str, color_name: str) -> None:
    """Print a string in a specific color."""
    print(colored(text, color_name))


def colored_alert(message: str, color: str = "yellow") -> str:
    exclamation = f"[{colored('!', color)}]"
    return f"{exclamation} {colored(message, color)}"


def check_config_vars():
    """Check environment variables for OneDrive or instrumental download."""
    global ADMIN_DOWNLOAD

    # OneDrive download is intended for admin-only use and thus restricted to macOS
    os_type = platform.system()
    if os_type != "Darwin" and ADMIN_DOWNLOAD:
        print_color("OneDrive is only supported on macOS.", "red")
        ADMIN_DOWNLOAD = False

    elif ADMIN_DOWNLOAD:
        onedrive_reminder = colored_alert(
            "Admin download (regular and instrumentals to OneDrive in all formats).",
            "magenta",
        )
        print(f"\n{onedrive_reminder}")

    # Display a warning/reminder if the instrumental flag is set
    if ENABLE_INSTRUMENTALS:
        instrumental_reminder = colored_alert(
            "Instrumentals environment variable is set, so only instrumentals will\n"
            "    be downloaded! Set EVREMIXES_GET_INSTRUMENTALS=0 to get the full songs.",
            "yellow",
        )
        print(f"\n{instrumental_reminder}")

    if ADMIN_DOWNLOAD or ENABLE_INSTRUMENTALS:
        print()


class MenuHelper:
    """Helper class for presenting menu options to the user."""

    def get_user_selections(self) -> tuple[str, str, bool]:
        """
        Present menu options to the user to select the file format and download location.

        Returns:
            A tuple containing selected file extensions, output folder, and get_both_formats indicator.
        """
        try:
            format_choice, get_both_formats = self._get_format_selection()

            if not get_both_formats:
                file_extension = ["m4a" if format_choice == "ALAC (Apple Lossless)" else "flac"]
                output_folder = self._get_folder_selection(format_choice, get_both_formats)
            else:
                file_extension = ["m4a", "flac"]
                output_folder = None

        except (KeyboardInterrupt, SystemExit):
            print_color("\nExiting.", "red")
            sys.exit(1)

        return file_extension, output_folder, get_both_formats

    def _get_format_selection(self) -> tuple[str, bool]:
        """
        Presents the user with file format options.

        Returns:
            A tuple containing selected format choice and get_both_formats indicator.
        """
        # Define the file format choices
        format_choices = ["FLAC", "ALAC (Apple Lossless)"]

        # Display ALAC first on macOS to match the system's default
        if platform.system() == "Darwin":
            format_choices.reverse()

        # Add the option to download both formats directly to OneDrive
        prefix = "instrumentals" if ENABLE_INSTRUMENTALS else "tracks"
        if ADMIN_DOWNLOAD:
            onedrive_option = f"Download all {prefix.lower()} directly to OneDrive"
            format_choices.insert(0, onedrive_option)
        elif ENABLE_INSTRUMENTALS:
            format_choices = [f"Instrumentals in {choice}" for choice in format_choices]

        format_question = [
            inquirer.List(
                "format",
                message="Choose file format to download",
                choices=format_choices,
                carousel=True,
            ),
        ]

        # Ask the user to choose a file format and exit if they cancel
        format_answer = inquirer.prompt(format_question)
        if format_answer is None:
            raise SystemExit

        # Get the selected format choice and indicator if both formats are selected
        format_choice = format_answer["format"]
        get_both_formats = format_choice.startswith("Download all")

        return format_choice, get_both_formats

    def _get_folder_selection(self, format_choice: str, get_both_formats: bool) -> str | None:
        """
        Presents the user with download location options based on their format choice.

        Args:
            format_choice: The user's selected file format.
            get_both_formats: Indicator if both formats are selected for download.

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
        if ADMIN_DOWNLOAD:
            folder_choices.insert(2, "OneDrive folder")

        folder_question = [
            inquirer.List(
                "folder",
                message="Choose download location",
                choices=folder_choices,
                carousel=True,
            ),
        ]

        # Ask the user to choose a download location
        folder_answer = inquirer.prompt(folder_question)
        if folder_answer is None:
            raise SystemExit

        # Return the selected folder path
        folder_choice = folder_answer["folder"]
        if folder_choice == "Downloads folder":
            return DOWNLOADS_FOLDER
        if folder_choice == "Music folder":
            return MUSIC_FOLDER
        if folder_choice == "OneDrive folder":
            return os.path.join(ONEDRIVE_FOLDER, subfolder_name)

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

        return os.path.expanduser(custom_folder_answer["custom_folder"])


class DownloadHelper:
    """Helper class for downloading tracks."""

    def __init__(self):
        self.metadata = MetadataHelper()

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
        track_info: dict[str, list[dict]],
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
        print_color(f"Downloading in {file_format} to {display_folder}...\n", "cyan")

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
        print_color(
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
            output_folder = os.path.join(ONEDRIVE_FOLDER, subfolder_name)
            print()
            self.download_tracks(track_info, output_folder, file_extension, is_instrumental=False)

            # Download instrumental tracks
            instrumental_output_folder = os.path.join(
                ONEDRIVE_FOLDER, f"Instrumentals {subfolder_name}"
            )
            print()
            self.download_tracks(
                track_info, instrumental_output_folder, file_extension, is_instrumental=True
            )

        self.open_folder_in_os(ONEDRIVE_FOLDER)

    def download_selected_tracks(
        self, track_info: dict[str, list[dict]], file_extensions: list[str], base_output_folder: str
    ) -> None:
        """Download the user's chosen selection to the output folder."""
        # Ensure the album name is valid for the output folder
        album_name = track_info["metadata"].get("album_name", "Unknown Album")
        valid_chars = f"-_.() {string.ascii_letters}{string.digits}"

        if base_output_folder is not None:  # Use the selected output folder
            safe_album_name = "".join(c for c in album_name if c in valid_chars)
            output_folder = os.path.join(base_output_folder, safe_album_name)
        else:  # Otherwise, save to OneDrive
            output_folder = ONEDRIVE_FOLDER
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
                    print_color(f"Failed to delete {file_path}. Reason: {e}", "red")

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


class MetadataHelper:
    """Helper class for applying metadata to downloaded tracks."""

    def apply_metadata(
        self,
        track: dict[str, str],
        metadata: dict[str, list[dict]],
        output_path: str,
        cover_data: bytes,
    ) -> bool:
        """
        Add metadata and cover art to the downloaded track file.

        Args:
            track: Track details.
            metadata: Metadata for the album.
            output_path: The path of the downloaded track file.
            cover_data: The cover art, resized and encoded as JPEG.

        Returns:
            True if metadata was added successfully, False otherwise.
        """
        try:  # Identify the audio format and track number
            audio_format = output_path.rsplit(".", 1)[1].lower()
            track_number = str(track.get("track_number", 0)).zfill(2)
            disc_number = 2 if ENABLE_INSTRUMENTALS else 1

            # Add the Instrumental suffix if enabled
            if ENABLE_INSTRUMENTALS and not track["track_name"].endswith(" (Instrumental)"):
                track["track_name"] += " (Instrumental)"

            # Apply metadata based on the audio format
            if audio_format == "m4a":
                self._apply_alac_metadata(
                    track, metadata, output_path, cover_data, track_number, disc_number
                )
            elif audio_format == "flac":
                self._apply_flac_metadata(
                    track, metadata, output_path, cover_data, track_number, disc_number
                )
            return True
        except Exception:
            return False

    def _apply_alac_metadata(
        self,
        track: dict[str, str],
        track_metadata: dict[str, list[dict]],
        output_path: str,
        cover_data: bytes,
        track_number: str,
        disc_number: int,
    ) -> None:
        """Apply metadata for ALAC files."""
        audio = MP4(output_path)

        # Add the metadata to the track
        audio["trkn"] = [(int(track_number), 0)]
        audio["disk"] = [(disc_number, 0)]
        audio["\xa9nam"] = track.get("track_name", "")
        audio["\xa9ART"] = track_metadata.get("artist_name", "")
        audio["\xa9alb"] = track_metadata.get("album_name", "")
        audio["\xa9day"] = str(track_metadata.get("year", ""))
        audio["\xa9gen"] = track_metadata.get("genre", "")

        # Add the album artist and comments if available
        if "album_artist" in track_metadata:
            audio["aART"] = track_metadata.get("album_artist", "")
        if "comments" in track:
            audio["\xa9cmt"] = track["comments"]

        # Add the cover art to the track
        audio["covr"] = [MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)]

        audio.save()

    def _apply_flac_metadata(
        self,
        track: dict[str, str],
        track_metadata: dict[str, list[dict]],
        output_path: str,
        cover_data: bytes,
        track_number: str,
        disc_number: int,
    ) -> None:
        """Apply metadata for FLAC files."""
        audio = FLAC(output_path)

        # Add the metadata to the track
        audio["tracknumber"] = track_number
        audio["discnumber"] = str(disc_number)
        audio["title"] = track.get("track_name", "")
        audio["artist"] = track_metadata.get("artist_name", "")
        audio["album"] = track_metadata.get("album_name", "")
        audio["date"] = str(track_metadata.get("year", ""))
        audio["genre"] = track_metadata.get("genre", "")

        # Add the cover art to the track
        if "album_artist" in track_metadata:
            audio["albumartist"] = track_metadata.get("album_artist", "")
        if "comments" in track:
            audio["description"] = track["comments"]

        # Add the cover art to the track
        pic = Picture()
        pic.data = cover_data
        pic.type = 3
        pic.mime = "image/jpeg"
        pic.width = 800
        pic.height = 800
        audio.add_picture(pic)

        audio.save()


def main() -> None:
    """Configure options and download remixes."""
    menu_helper = MenuHelper()
    download_helper = DownloadHelper()
    check_config_vars()

    try:
        file_extensions, output_folder, get_both_formats = menu_helper.get_user_selections()
        track_info = download_helper.download_track_info()

        if ADMIN_DOWNLOAD or get_both_formats:
            download_helper.download_both_formats_to_onedrive(track_info, file_extensions)
        else:
            download_helper.download_selected_tracks(track_info, file_extensions, output_folder)

    except (KeyboardInterrupt, SystemExit):
        print_color("\nExiting.", "red")
        sys.exit(1)


if __name__ == "__main__":
    main()
