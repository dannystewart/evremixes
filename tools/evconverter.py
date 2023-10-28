#!/usr/bin/env python3

import json
import os
import subprocess
import sys
import tempfile
import time
from io import BytesIO

import inquirer
import requests
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from halo import Halo
from mutagen.mp4 import MP4, MP4Cover
from PIL import Image
from pydub import AudioSegment
from termcolor import colored

# Initialize the spinner
spinner = Halo(text="Initializing", spinner="dots")

# Get the script directory and assemble the .env path
script_directory = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_directory, ".env")

# Load environment variables
load_dotenv()
load_dotenv(dotenv_path=env_path)

# Make sure we have the Azure connection string
connection_string = os.environ.get("AZURE_CONNECTION_STRING")
if connection_string is None:
    print("Error: AZURE_CONNECTION_STRING not found. Check environment variables.")
    sys.exit(1)

# Initialize the Blob Service Client
blob_service_client = BlobServiceClient.from_connection_string(connection_string)
container_name = "music"
container_client = blob_service_client.get_container_client(container_name)
uploaded_blob_names = []

# Download and load the JSON file with track details
spinner.start(text=colored("Downloading track details...", "cyan"))
response = requests.get("https://git.dannystewart.com/danny/evremixes/raw/branch/main/evtracks.json")

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

# Menu
sorted_tracks = sorted(track_data["tracks"], key=lambda x: x["track_number"])

questions = [
    inquirer.Checkbox(
        "tracks",
        message="Select tracks to upload (Ctrl-A for all)",
        choices=[track["track_name"] for track in sorted_tracks],
    ),
]

answers = inquirer.prompt(questions)
selected_tracks = [track for track in sorted_tracks if track["track_name"] in answers["tracks"]]

# Create temp directory for downloads and conversions
with tempfile.TemporaryDirectory() as tmpdirname:
    output_folder = tmpdirname

    # Loop through each track
    for track in selected_tracks:
        track_name = track["track_name"]
        file_url = track["file_url"]
        original_filename = os.path.basename(file_url)
        original_filename_without_extension = os.path.splitext(original_filename)[0]

        print(f"Processing {track_name}...")

        # Download FLAC file
        with Halo(text=colored("Downloading FLAC file...", "cyan"), spinner="dots"):
            flac_file_path = f"{output_folder}/{original_filename}"
            response = requests.get(file_url)
            with open(flac_file_path, "wb") as f:
                f.write(response.content)

        # Convert FLAC to ALAC (M4A)
        with Halo(text=colored("Converting FLAC to ALAC...", "cyan"), spinner="dots"):
            m4a_file_path = f"{output_folder}/{original_filename_without_extension}.m4a"
            audio = AudioSegment.from_file(flac_file_path, format="flac")
            audio.export(m4a_file_path, format="ipod", codec="alac")

        # Add metadata and cover art using mutagen
        with Halo(text=colored("Adding metadata and cover art...", "cyan"), spinner="dots"):
            audio = MP4(m4a_file_path)
            audio["trkn"] = [(track.get("track_number", 0), 0)]
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

        print(colored(f"Processed {track_name}!", "green"))

        # Remove the FLAC file
        os.remove(flac_file_path)

        # Upload M4A file to Azure
        with Halo(text=colored("Uploading M4A to Azure...", "cyan"), spinner="dots"):
            blob_name = f"ev/{os.path.basename(m4a_file_path)}"
            blob_client = container_client.get_blob_client(blob_name)

            with open(m4a_file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)

            uploaded_blob_names.append(f"/{container_name}/{blob_name}")

        # Overwrite the previous line with "Uploaded"
        print("\033[F\033[K", end="")  # Move up one line and clear line
        print(colored(f"Uploaded {track_name}!", "green"))

print(colored("\n✔ Selected tracks converted and reuploaded to Azure!", "green"))

if uploaded_blob_names:  # Only run if there are files to purge
    # Convert list to string format suitable for command line argument
    content_paths_str = " ".join([f"'{name}'" for name in uploaded_blob_names])

    with Halo(
        text=colored("Now purging Azure CDN cache (this may take a few minutes)...", "cyan"),
        spinner="dots",
    ):
        process = subprocess.run(
            [
                "az",
                "cdn",
                "endpoint",
                "purge",
                "--resource-group",
                "dsfiles",
                "--name",
                "dsfiles",
                "--profile-name",
                "dsfiles",
                "--content-paths",
            ]
            + uploaded_blob_names,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if process.returncode == 0:
            spinner.succeed(colored("Azure CDN cache has been purged!", "green"))
        else:
            spinner.fail(
                colored(
                    f"Failed to purge Azure CDN cache. Error: {process.stderr.decode('utf-8')}",
                    "red",
                )
            )

    # Initialize wait time (in seconds)
    wait_time = 10

    # Populate CDN edge servers
    with tempfile.TemporaryDirectory() as tmpdirname:
        output_folder = tmpdirname

        with Halo(
            text=colored(f"Waiting {wait_time} seconds to populate CDN...", "cyan"),
            spinner="dots",
        ) as spinner:
            for i in range(wait_time, 0, -1):
                spinner.text = colored(f"Populating CDN in {i} seconds...", "cyan")
                time.sleep(1)
            spinner.text = colored("Populating CDN edge servers...", "cyan")

            total_tracks = len(uploaded_blob_names)
            for index, blob_name in enumerate(uploaded_blob_names, start=1):
                try:
                    blob_client = container_client.get_blob_client(
                        blob_name.replace(f"/{container_name}/", "")
                    )
                    blob_data = blob_client.download_blob()
                except Exception as e:
                    spinner.fail(
                        colored(
                            f"Failed to download blob {blob_name}. Error: {str(e)}",
                            "red",
                        )
                    )
                    continue  # Skip to the next blob_name in the loop

                # Update spinner text to include counter
                spinner.text = colored(f"Populating CDN edge servers ({index}/{total_tracks})...", "cyan")

                temp_file_path = f"{output_folder}/temp_{os.path.basename(blob_name)}"
                with open(temp_file_path, "wb") as temp_file:
                    temp_file.write(blob_data.readall())
                os.remove(temp_file_path)  # Delete the temporary file

            spinner.succeed(colored("CDN edge servers populated.", "green"))
