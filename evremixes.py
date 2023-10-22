#!/usr/bin/env python

import json
import os
import platform
import requests
import subprocess
import inquirer
import shutil
from halo import Halo
from io import BytesIO
from mutagen.mp4 import MP4, MP4Cover
from PIL import Image
from pydub import AudioSegment
from termcolor import colored

spinner = Halo(text="Initializing", spinner="dots")

# Determine the operating system
os_type = platform.system()

# Download and load the JSON file with track details
spinner.start(text=colored("Downloading track details...", "cyan"))
response = requests.get(
    "https://git.dannystewart.com/danny/evremixes/raw/branch/main/evtracks.json"
)

# Download track and album metadata
track_data = json.loads(response.text)
metadata = track_data.get("metadata", {})

# Download cover art
cover_response = requests.get(metadata.get("cover_art_url", ""))
cover_data_original = cover_response.content

# Convert to JPEG and resize to 800x800 using PIL
image = Image.open(BytesIO(cover_data_original))
image = image.convert("RGB")  # Convert to RGB if image is not in this mode
image = image.resize((800, 800))

# Save the image data to a BytesIO object, then to a byte array
buffered = BytesIO()
image.save(buffered, format="JPEG")
cover_data = buffered.getvalue()

spinner.succeed(text=colored("Downloaded track details.", "green"))

# Prompt user for sorting preference using inquirer
questions = [
    inquirer.List(
        "sort_order",
        message="Choose track order",
        choices=["playlist order", "chronological by start date"],
    ),
]
answers = inquirer.prompt(questions)
sorting_choice = answers["sort_order"]

# Sort tracks by track number or date based on user choice
if sorting_choice == "playlist order":
    track_data["tracks"] = sorted(track_data["tracks"], key=lambda k: k.get("track_number", 0))
elif sorting_choice == "chronological by start date":
    track_data["tracks"] = sorted(track_data["tracks"], key=lambda k: k.get("start_date", ""))

# Set the default output folder based on the operating system
if os_type == "Windows":
    default_output_folder = os.path.expanduser("~/Music")
else:
    default_output_folder = os.path.expanduser("~/Downloads")

# Figure out download location
album_name = metadata.get("album_name")
album_folder = metadata.get("album_name", "Unknown Album")
output_folder = os.path.join(default_output_folder, album_folder)
normalized_output_folder = os.path.normpath(output_folder)

# Replace home directory with tilde (~) if not on Windows
if os_type != "Windows":
    home_dir = os.path.expanduser('~')
    normalized_output_folder = normalized_output_folder.replace(home_dir, '~')

print(colored(f"Downloading {album_name} to {normalized_output_folder}...", "cyan"))

# Check and create folders
if not os.path.exists(output_folder):
    os.makedirs(output_folder)
elif os.listdir(output_folder):  # Folder exists and has files
    print(
        colored(
            "The folder already exists and contains files. Emptying folder...\n",
            "yellow",
        )
    )

    # Deletion code for existing files
    for filename in os.listdir(output_folder):
        file_path = os.path.join(output_folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")

# Create the output folder if it doesn't exist
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Loop through each track
for index, track in enumerate(track_data["tracks"]):
    track_name = track["track_name"]

    # Different numbering based on sorting choice
    if sorting_choice == "track":
        track_number = str(track.get("track_number", "")).zfill(2)
    else:
        track_number = str(index + 1).zfill(2)

    track_number_short = str(track.get("track_number", ""))
    print(
        f"Processing track {int(track_number_short) if sorting_choice == 'track' else int(track_number)}, {track_name}..."
    )

    # Download FLAC file
    with Halo(text=colored("Downloading FLAC file...", "cyan"), spinner="dots"):
        flac_file_path = f"{output_folder}/{track_name}.flac"
        response = requests.get(track["file_url"])
        with open(flac_file_path, "wb") as f:
            f.write(response.content)

    # Convert FLAC to ALAC (M4A)
    with Halo(text=colored("Converting FLAC to ALAC...", "cyan"), spinner="dots"):
        m4a_file_path = f"{output_folder}/{track_number} - {track_name}.m4a"
        audio = AudioSegment.from_file(flac_file_path, format="flac")
        audio.export(m4a_file_path, format="ipod", codec="alac")

    # Add metadata and cover art using mutagen
    with Halo(text=colored("Adding metadata and cover art...", "cyan"), spinner="dots"):
        audio = MP4(m4a_file_path)
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

    print(colored(f"Completed {track_name}!", "green"))

    # Remove the FLAC file
    os.remove(flac_file_path)

print(colored("\nAll tracks downloaded and ready! Enjoy!", "green"))

# Open the folder in the OS
if os_type == "Windows":
    subprocess.run(['explorer', os.path.abspath(output_folder)])
elif os_type == "Darwin":  # macOS
    subprocess.run(['open', os.path.abspath(output_folder)])
