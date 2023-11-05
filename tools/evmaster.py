#!/usr/bin/env python3

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import traceback
from io import BytesIO

import pyperclip
import requests
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from halo import Halo
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4, MP4Cover
from PIL import Image
from pydub import AudioSegment
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import PythonTracebackLexer
from termcolor import colored


def colorized_traceback_hook(type, value, tb):
    tbtext = "".join(traceback.format_exception(type, value, tb))
    colored_traceback = highlight(tbtext, PythonTracebackLexer(), TerminalFormatter())
    print(colored_traceback)


sys.excepthook = colorized_traceback_hook

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
container_client = blob_service_client.get_container_client("music")

# Initialize metadata
album_metadata = None
track_data = None
cover_data = None


# Download and prepare metadata
def fetch_metadata():
    # Download and load the JSON file with track metadata
    spinner.start(colored("Downloading track metadata...", "cyan"))
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

    return metadata, track_data, cover_data


# Function to convert audio from WAV to FLAC
def convert_audio_to_flac(input_file, output_dir):
    wav_audio = AudioSegment.from_file(input_file, format="wav")
    flac_file_name = os.path.basename(input_file).replace(".wav", ".flac")
    flac_file_path = os.path.join(output_dir, flac_file_name)
    wav_audio.export(flac_file_path, format="flac")
    return flac_file_path


# Function to convert audio from WAV to M4A (ALAC)
def convert_audio_to_m4a(input_file, output_dir):
    wav_audio = AudioSegment.from_file(input_file, format="wav")
    m4a_file_name = os.path.basename(input_file).replace(".wav", ".m4a")
    m4a_file_path = os.path.join(output_dir, m4a_file_name)
    wav_audio.export(m4a_file_path, format="ipod", codec="alac")
    return m4a_file_path


# Function to add metadata to a FLAC file
def add_metadata_to_flac(flac_file_path, album_metadata, track_metadata):
    audio = FLAC(flac_file_path)

    audio["title"] = track_metadata.get("track_name", "")
    audio["tracknumber"] = str(track_metadata.get("track_number", ""))
    audio["album"] = album_metadata.get("album_name", "")
    audio["albumartist"] = album_metadata.get("album_artist", "")
    audio["artist"] = album_metadata.get("artist_name", "")
    audio["genre"] = album_metadata.get("genre", "")
    audio["date"] = str(album_metadata.get("year", ""))

    img = Picture()
    img.data = cover_data
    img.type = 3
    img.mime = "image/jpeg"
    img.desc = "Cover (front)"
    audio.add_picture(img)

    audio.save()
    return flac_file_path


# Function to add metadata to a M4A file
def add_metadata_to_m4a(m4a_file_path, album_metadata, track_metadata):
    audio = MP4(m4a_file_path)

    audio["\xa9nam"] = track_metadata.get("track_name", "")
    audio["trkn"] = [(track_metadata.get("track_number", 0), 0)]
    audio["\xa9ART"] = album_metadata.get("artist_name", "")
    audio["aART"] = album_metadata.get("album_artist", "")
    audio["\xa9alb"] = album_metadata.get("album_name", "")
    audio["\xa9gen"] = album_metadata.get("genre", "")
    audio["\xa9day"] = str(album_metadata.get("year", ""))
    audio["covr"] = [MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)]

    audio.save()
    return m4a_file_path


# Function to handle all FLAC processing
def handle_flac(input_file, temp_dir, album_metadata, track_metadata, blob_name):
    spinner.start(colored("Converting to FLAC...", "cyan"))
    flac_file_path = convert_audio_to_flac(input_file, temp_dir)
    spinner.start(colored("Adding metadata to FLAC...", "cyan"))
    add_metadata_to_flac(flac_file_path, album_metadata, track_metadata)
    spinner.start(colored("Uploading FLAC...", "cyan"))
    upload_to_azure(f"ev/{blob_name}.flac", flac_file_path)
    spinner.succeed(colored("FLAC tagged and uploaded!", "green"))


# Function to handle all M4A processing
def handle_m4a(input_file, temp_dir, album_metadata, track_metadata, blob_name):
    spinner.start(colored("Converting to M4A...", "cyan"))
    m4a_file_path = convert_audio_to_m4a(input_file, temp_dir)
    spinner.start(colored("Adding metadata to M4A...", "cyan"))
    add_metadata_to_m4a(m4a_file_path, album_metadata, track_metadata)
    spinner.start(colored("Uploading M4A...", "cyan"))
    upload_to_azure(f"ev/{blob_name}.m4a", m4a_file_path)
    spinner.succeed(colored("M4A tagged and uploaded!", "green"))


# Upload to Azure
def upload_to_azure(blob_name, temp_output_file):
    blob_client = container_client.get_blob_client(blob_name)
    with open(temp_output_file, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)


# Purge CDN Cache
def purge_cdn_cache():
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
            "/ev",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if process.returncode != 0:
        raise Exception(f"Failed to purge Azure CDN cache. Error: {process.stderr.decode('utf-8')}")


# Main function
def main(filename, input_file):
    global album_metadata, track_metadata, cover_data
    album_metadata, track_data, cover_data = fetch_metadata()
    flac_file_path = None
    m4a_file_path = None

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Extract the base filename without extension for use in Azure paths
            base_name, ext = os.path.splitext(filename)
            if not ext:
                filename = f"{base_name}.flac"
            blob_name = os.path.splitext(filename)[0]
            spinner.start(colored("Starting processing of audio files...", "cyan"))

            # Get and verify the track metadata
            spinner.start(colored("Matching track metadata...", "cyan"))
            track_metadata = None
            for track in track_data.get("tracks", []):
                json_filename = os.path.basename(track["file_url"])
                if filename.lower() == json_filename.lower():
                    track_metadata = track
                    break
            if not track_metadata:
                spinner.fail(colored("Error: No matching track found in the JSON metadata.", "red"))
                return
            track_matched = track_metadata.get("track_name", "")
            spinner.succeed(colored(f"Track matched: {track_matched}", "green"))

            # Get album-level metadata and find matching track
            album_metadata = track_data.get("metadata", {})
            track_metadata = None
            for track in track_data.get("tracks", []):
                json_filename = os.path.basename(track["file_url"])
                if filename.lower() == json_filename.lower():
                    track_metadata = track
                    break

            # Process and upload the files
            handle_flac(input_file, temp_dir, album_metadata, track_metadata, blob_name)
            handle_m4a(input_file, temp_dir, album_metadata, track_metadata, blob_name)

        except Exception as e:
            spinner.fail(colored(f"An error occurred: {str(e)}", "red"))
            if os.path.exists(flac_file_path):
                os.remove(flac_file_path)
            if os.path.exists(m4a_file_path):
                os.remove(m4a_file_path)

        spinner.start(colored("Purging CDN cache (takes a while, Ctrl-C to skip)...", "cyan"))

        try:
            purge_cdn_cache()
            spinner.succeed(colored("CDN cache purged!", "green"))
        except KeyboardInterrupt:
            spinner.warn(colored("CDN purge skipped.", "yellow"))
        except Exception as e:
            spinner.fail(f"Failed to purge CDN: {e}")

        spinner.succeed(colored("All done!", "green"))

    url_path = "https://files.dannystewart.com/music/ev/"
    final_url_flac = f"{url_path}{blob_name}.flac"
    final_url_m4a = f"{url_path}{blob_name}.m4a"
    pyperclip.copy(final_url_flac)

    print("\nURLs of uploaded files:")
    print(colored(f"{final_url_flac}", "blue"), end="")
    print("  <- copied to clipboard")
    print(colored(f"{final_url_m4a}", "blue"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload and convert audio file to Azure Blob Storage.")
    parser.add_argument(
        "input_file",
        type=str,
        help="Local input audio file",
    )
    parser.add_argument(
        "filename",
        type=str,
        nargs="?",
        default=None,
        help="Filename for upload",
    )

    args = parser.parse_args()

    _, ext = os.path.splitext(args.input_file)
    if ext.lower() not in [".wav", ".aif", ".aiff"]:
        print("Invalid file type. Please provide a WAV or AIFF file.")
        sys.exit(1)

    if args.filename is None:
        base_name = os.path.basename(args.input_file)
        base_name = os.path.splitext(base_name)[0]
        base_name = re.sub(r"\s*\d+\.\d+\.\d+_\d+.*", "", base_name)
        base_name = base_name.replace(" ", "-")
        args.filename = base_name
        print(colored(f"No filename given, uploading as {args.filename}.flac", "cyan"))

    try:
        main(args.filename, args.input_file)
    except KeyboardInterrupt:
        print(colored("\nAborting.", "red"))
        sys.exit(0)
