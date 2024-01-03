#!/usr/bin/env python3
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


def get_track_details():
    """
    Download the JSON file with track details.

    Returns:
        dict: The loaded track details.
    """
    try:
        response = requests.get(
            "https://git.dannystewart.com/danny/evremixes/raw/branch/main/evtracks.json",
            timeout=10,
        )
    except requests.RequestException as e:
        raise SystemExit(e) from e

    track_data = json.loads(response.content)
    track_data["tracks"] = sorted(
        track_data["tracks"], key=lambda track: track.get("track_number", 0)
    )
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
    cover_data = buffered.getvalue()

    return cover_data


def get_user_choices():
    """
    Present menu options to the user to select the file format and download location.

    Returns:
        tuple: A tuple containing the selected file extension and output folder.
    """
    format_choices = (
        ["ALAC (Apple Lossless)", "FLAC"]
        if platform.system() == "Darwin"
        else ["FLAC", "ALAC (Apple Lossless)"]
    )
    format_question = [
        inquirer.List(
            "format",
            message="Choose file format to download",
            choices=format_choices,
        ),
    ]
    format_answer = inquirer.prompt(format_question)
    format_choice = format_answer["format"]
    file_extension = "m4a" if format_choice == "ALAC (Apple Lossless)" else "flac"

    default_downloads_folder = os.path.expanduser("~/Downloads")
    default_music_folder = os.path.expanduser("~/Music")

    folder_question = [
        inquirer.List(
            "folder",
            message="Choose download location",
            choices=["Downloads folder", "Music folder", "Enter a custom path"],
        ),
    ]
    folder_answer = inquirer.prompt(folder_question)
    folder_choice = folder_answer["folder"]
    if folder_choice == "Downloads folder":
        output_folder = default_downloads_folder
    elif folder_choice == "Music folder":
        output_folder = default_music_folder
    else:
        custom_folder_question = [
            inquirer.Text(
                "custom_folder",
                message="Enter the full path for your custom download location",
            )
        ]
        custom_folder_answer = inquirer.prompt(custom_folder_question)
        output_folder = custom_folder_answer["custom_folder"]

    return file_extension, output_folder


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
                print(colored(f"Failed to delete {file_path}. Reason: {e}", "red"))


def add_metadata_to_track(track, metadata, output_file_path, cover_data):
    """
    Add metadata and cover art to the downloaded track file.

    Args:
        track (dict): Track details.
        metadata (dict): Metadata for the album.
        output_file_path (str): The path of the downloaded track file.
        cover_data (bytes): The cover art, resized and encoded as JPEG.
    """
    try:
        audio_format = output_file_path.rsplit(".", 1)[1].lower()
        track_number = str(track.get("track_number", 0)).zfill(2)

        if audio_format == "m4a":
            audio = MP4(output_file_path)
            audio["trkn"] = [(int(track_number), 0)]
            audio["\xa9nam"] = track.get("track_name", "")
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

        elif audio_format == "flac":
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
        return True

    except Exception:
        return False


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
    print(colored(f"Downloading in {file_format} to {display_folder}...\n", "cyan"))

    metadata = track_data["metadata"]
    cover_data = download_cover_art(metadata)
    total_tracks = len(track_data["tracks"])
    spinner = Halo(spinner="dots")
    for index, track in enumerate(track_data["tracks"], start=1):
        track_number = str(track.get("track_number", index)).zfill(2)
        track_name = track["track_name"]
        file_url = track["file_url"].rsplit(".", 1)[0] + f".{file_extension}"

        output_file_path = os.path.join(
            output_folder, f"{track_number} - {track_name}.{file_extension}"
        )
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
    print(
        colored(
            f"\nAll {total_tracks} remixes downloaded in {file_format} to {display_folder}. Enjoy!",
            "green",
        )
    )


def open_folder(output_folder):
    """
    Open the output folder in the OS file explorer.

    Args:
        output_folder (str): The path to the output folder.
    """
    os_type = platform.system()
    abspath = os.path.abspath(output_folder)
    if os_type == "Windows":
        subprocess.run(["explorer", abspath])
    elif os_type in ["Darwin", "Linux"]:
        subprocess.run(["open" if os_type == "Darwin" else "xdg-open", abspath])


def main():
    """Main function."""
    file_extension, base_output_folder = get_user_choices()
    track_data = get_track_details()

    album_name = track_data["metadata"].get("album_name", "Unknown Album")
    valid_chars = f"-_.() {string.ascii_letters}{string.digits}"
    safe_album_name = "".join(c for c in album_name if c in valid_chars)
    output_folder = os.path.join(base_output_folder, safe_album_name)

    download_tracks(track_data, output_folder, file_extension)
    open_folder(output_folder)


if __name__ == "__main__":
    main()
