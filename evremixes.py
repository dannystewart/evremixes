#!/usr/bin/env python3
# pylint: disable=global-statement

import contextlib
import json
import os
import platform
import string
import subprocess
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
# Add EVREMIXES_ENABLE_ONEDRIVE=1 to your environment variables to enable
ENABLE_ONEDRIVE = os.getenv("EVREMIXES_ENABLE_ONEDRIVE") == "1"
ONEDRIVE_PATH = "~/Library/CloudStorage/OneDrive-Personal/Music/Danny Stewart/Evanescence Remixes"
ONEDRIVE_FOLDER = os.path.expanduser(ONEDRIVE_PATH)

# Enable downloading instrumentals (add EVREMIXES_GET_INSTRUMENTALS=1 to your environment variables to enable)
ENABLE_INSTRUMENTALS = os.getenv("EVREMIXES_GET_INSTRUMENTALS") == "1"


def print_color(text, color_name):
    """Prints a string in a specific color."""
    print(colored(text, color_name))


def get_track_details():
    """
    Download the JSON file with track details.

    Returns:
        dict: The loaded track details.
    """
    try:
        response = requests.get(TRACKLIST_URL, timeout=10)
    except requests.RequestException as e:
        raise SystemExit(e) from e

    track_data = json.loads(response.content)
    track_data["tracks"] = sorted(track_data["tracks"], key=lambda track: track.get("track_number", 0))
    return track_data


def download_cover_art(metadata):
    """
    Download and process the album cover art.

    Args:
        metadata (dict): Metadata for the album containing cover_art_url.

    Returns:
        bytes: The processed cover art, resized and encoded as JPEG.
    """
    cover_response = requests.get(metadata.get("cover_art_url", ""), timeout=10)
    cover_data_original = cover_response.content

    image = Image.open(BytesIO(cover_data_original))
    image = image.convert("RGB")
    image = image.resize((800, 800))

    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    return buffered.getvalue()


def get_user_choices():
    """
    Present menu options to the user to select the file format and download location.

    Returns:
        tuple: A tuple containing the selected file extensions, output folder, and download_both_formats indicator.
    """
    format_choice, download_both_formats = _get_format_choice()

    if not download_both_formats:
        file_extension = ["m4a" if format_choice == "ALAC (Apple Lossless)" else "flac"]
        output_folder = _get_folder_choice(format_choice, download_both_formats)
    else:
        file_extension = ["m4a", "flac"]
        output_folder = None

    return file_extension, output_folder, download_both_formats


def _get_format_choice():
    """
    Presents the user with file format options.

    Returns:
        tuple: A tuple containing the selected format choice and a boolean indicating if both formats should be downloaded.
    """
    format_choices = ["FLAC", "ALAC (Apple Lossless)"]
    if platform.system() == "Darwin":
        format_choices.reverse()

    if ENABLE_ONEDRIVE:
        format_choices.insert(0, "Download all directly to OneDrive")

    if ENABLE_INSTRUMENTALS:
        format_choices = ["Instrumentals in " + choice for choice in format_choices]

    format_question = [
        inquirer.List(
            "format",
            message="Choose file format to download",
            choices=format_choices,
            carousel=True,
        ),
    ]
    format_answer = inquirer.prompt(format_question)
    if format_answer is None:
        raise SystemExit

    format_choice = format_answer["format"]
    download_both_formats = format_choice == "Download all directly to OneDrive"

    return format_choice, download_both_formats


def _get_folder_choice(format_choice, download_both_formats):
    """
    Presents the user with download location options based on their format choice.

    Args:
        format_choice (str): The user's selected file format.
        download_both_formats (bool): Indicator if both formats are selected for download.

    Returns:
        str: The selected output folder path.
    """
    if download_both_formats:
        return None

    subfolder_name = "ALAC" if format_choice == "ALAC (Apple Lossless)" else "FLAC"
    folder_choices = ["Downloads folder", "Music folder", "Enter a custom path"]

    if ENABLE_ONEDRIVE:
        folder_choices.insert(2, "OneDrive folder")

    folder_question = [
        inquirer.List(
            "folder",
            message="Choose download location",
            choices=folder_choices,
            carousel=True,
        ),
    ]
    folder_answer = inquirer.prompt(folder_question)
    if folder_answer is None:
        raise SystemExit

    folder_choice = folder_answer["folder"]

    if folder_choice == "Downloads folder":
        return DOWNLOADS_FOLDER
    if folder_choice == "Music folder":
        return MUSIC_FOLDER
    if folder_choice == "OneDrive folder":
        return os.path.join(ONEDRIVE_FOLDER, subfolder_name)

    custom_folder_question = [
        inquirer.Text(
            "custom_folder",
            message="Enter the full path for your custom download location",
        )
    ]
    custom_folder_answer = inquirer.prompt(custom_folder_question)
    if custom_folder_answer is None:
        raise SystemExit

    return os.path.expanduser(custom_folder_answer["custom_folder"])


def clear_existing_files(output_folder):
    """
    Clear existing files with the specified file extension in the output folder.

    Args:
        output_folder (str): The path to the output folder.
    """
    file_extensions = ("flac", "m4a")
    for filename in os.listdir(output_folder):
        if filename.endswith(file_extensions):
            file_path = os.path.join(output_folder, filename)
            try:
                os.remove(file_path)
            except Exception as e:
                print_color(f"Failed to delete {file_path}. Reason: {e}", "red")


def add_metadata_to_track(track, metadata, output_file_path, cover_data):
    """
    Add metadata and cover art to the downloaded track file.

    Args:
        track (dict): Track details.
        metadata (dict): Metadata for the album.
        output_file_path (str): The path of the downloaded track file.
        cover_data (bytes): The cover art, resized and encoded as JPEG.

    Returns:
        bool: True if metadata was added successfully, False otherwise.
    """
    try:
        audio_format = output_file_path.rsplit(".", 1)[1].lower()
        track_number = str(track.get("track_number", 0)).zfill(2)

        if audio_format == "m4a":
            _add_metadata_for_alac(track, metadata, output_file_path, cover_data, track_number)
        elif audio_format == "flac":
            _add_metadata_for_flac(track, metadata, output_file_path, cover_data, track_number)
        return True

    except Exception:
        return False


def _add_metadata_for_alac(track, metadata, output_file_path, cover_data, track_number):
    """Handle metadata addition for ALAC."""
    track_name = (
        track.get("track_name", "") + " (Instrumental)"
        if ENABLE_INSTRUMENTALS
        else track.get("track_name", "")
    )

    audio = MP4(output_file_path)
    audio["trkn"] = [(int(track_number), 0)]
    audio["\xa9nam"] = track_name
    audio["\xa9ART"] = metadata.get("artist_name", "")
    audio["\xa9alb"] = metadata.get("album_name", "")
    audio["\xa9day"] = str(metadata.get("year", ""))
    audio["\xa9gen"] = metadata.get("genre", "")
    audio["covr"] = [MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)]

    if "album_artist" in metadata:
        audio["aART"] = metadata.get("album_artist", "")
    if "comments" in track:
        audio["\xa9cmt"] = track["comments"]

    audio.save()


def _add_metadata_for_flac(track, metadata, output_file_path, cover_data, track_number):
    """Handle metadata addition for FLAC."""
    audio = FLAC(output_file_path)
    audio["tracknumber"] = track_number
    audio["title"] = track.get("track_name", "")
    audio["artist"] = metadata.get("artist_name", "")
    audio["album"] = metadata.get("album_name", "")
    audio["date"] = str(metadata.get("year", ""))
    audio["genre"] = metadata.get("genre", "")

    if "album_artist" in metadata:
        audio["albumartist"] = metadata.get("album_artist", "")
    if "comments" in track:
        audio["description"] = track["comments"]

    pic = Picture()
    pic.data = cover_data
    pic.type = 3
    pic.mime = "image/jpeg"
    pic.width = 800
    pic.height = 800
    audio.add_picture(pic)

    audio.save()


def download_tracks(track_data, output_folder, file_extension):
    """
    Download each track from the provided URL and save it to the output folder.

    Args:
        track_data (dict): Loaded track details.
        output_folder (str): The path to the output folder.
        file_extension (str): The file extension to download.
    """
    os.makedirs(output_folder, exist_ok=True)
    clear_existing_files(output_folder)
    home_dir = os.path.expanduser("~")
    display_folder = output_folder.replace(home_dir, "~")
    display_folder = os.path.normpath(display_folder)

    file_format = "Apple Lossless" if file_extension == "m4a" else "FLAC"
    print_color(f"Downloading in {file_format} to {display_folder}...\n", "cyan")

    metadata = track_data["metadata"]
    cover_data = download_cover_art(metadata)
    total_tracks = len(track_data["tracks"])

    spinner = Halo(spinner="dots")

    for index, track in enumerate(track_data["tracks"], start=1):
        track_number = str(track.get("track_number", index)).zfill(2)
        if ENABLE_INSTRUMENTALS:
            file_url = track["inst_url"].rsplit(".", 1)[0] + f".{file_extension}"
            track_name = track["track_name"] + " (Instrumental)"
        else:
            file_url = track["file_url"].rsplit(".", 1)[0] + f".{file_extension}"
            track_name = track["track_name"]

        output_file_path = os.path.join(output_folder, f"{track_number} - {track_name}.{file_extension}")

        spinner.text = colored(f"Downloading {track_name}... ({index}/{total_tracks})", "cyan")
        spinner.start()

        try:
            response = requests.get(file_url, stream=True, timeout=30)
            response.raise_for_status()
            with open(output_file_path, "wb") as f:
                f.write(response.content)

            spinner.text = colored("Applying metadata...", "cyan")

            success = add_metadata_to_track(track, metadata, output_file_path, cover_data)
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


def open_folder(output_folder):
    """
    Open the output folder in the OS file explorer.

    Args:
        output_folder (str): The path to the output folder.
    """
    with contextlib.suppress(Exception):
        os_type = platform.system()
        abspath = os.path.abspath(output_folder)
        if os_type == "Windows":
            subprocess.run(["explorer", abspath], check=False)
        elif os_type == "Darwin":
            subprocess.run(["open", abspath], check=False)
        elif os_type == "Linux" and "DISPLAY" in os.environ:
            subprocess.run(["xdg-open", abspath], check=False)


def main():
    """Main function."""
    global ENABLE_ONEDRIVE

    # OneDrive is for a very specific use case, so only enable it on macOS
    os_type = platform.system()
    if os_type != "Darwin" and ENABLE_ONEDRIVE:
        print_color("OneDrive is only supported on macOS.", "red")
        ENABLE_ONEDRIVE = False

    if ENABLE_INSTRUMENTALS:
        inst_str = (
            "\n[!] Instrumentals environment variable is set, so only instrumentals will"
            "\n    be downloaded! Unset EVREMIXES_GET_INSTRUMENTALS to get the full songs.\n"
        )
        print_color(inst_str, "yellow")

    file_extensions, base_output_folder, download_both_formats = get_user_choices()
    track_data = get_track_details()

    album_name = track_data["metadata"].get("album_name", "Unknown Album")
    valid_chars = f"-_.() {string.ascii_letters}{string.digits}"
    safe_album_name = "".join(c for c in album_name if c in valid_chars)

    if download_both_formats:
        for file_extension in file_extensions:
            subfolder_name = "ALAC" if file_extension == "m4a" else "FLAC"
            output_folder = os.path.join(ONEDRIVE_FOLDER, subfolder_name)
            print()
            download_tracks(track_data, output_folder, file_extension)
        open_folder(ONEDRIVE_FOLDER)
    else:
        if base_output_folder is not None:
            output_folder = os.path.join(base_output_folder, safe_album_name)
        else:
            output_folder = ONEDRIVE_FOLDER
        download_tracks(track_data, output_folder, file_extensions[0])
        open_folder(output_folder)


if __name__ == "__main__":
    main()
