#!/usr/bin/env python3

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from io import BytesIO

import pyperclip
import requests
from azure.storage.blob import BlobServiceClient
from azure.storage.blob import ContentSettings
from dotenv import load_dotenv
from halo import Halo
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4, MP4Cover
from PIL import Image
from pydub import AudioSegment
from termcolor import colored

# Initialize spinner, temp dir, env vars, and Azure client
spinner = Halo(text="Initializing", spinner="dots")
temp_dir = tempfile.mkdtemp()
load_dotenv()
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
connection_string = os.getenv("AZURE_CONNECTION_STRING")
if not connection_string:
    print(colored("Error: AZURE_CONNECTION_STRING not found. Check environment variables.", "red"))
    sys.exit(1)
container_client = BlobServiceClient.from_connection_string(connection_string).get_container_client("music")


# Retrieve and prepare metadata, download cover art
def fetch_metadata():
    spinner.start(colored("Downloading track metadata...", "cyan"))

    response = requests.get("https://git.dannystewart.com/danny/evremixes/raw/branch/main/evtracks.json")
    track_data = json.loads(response.text)

    cover_art_url = track_data.get("metadata", {}).get("cover_art_url", "")
    cover_art_response = requests.get(cover_art_url)
    cover_art_bytes = BytesIO(cover_art_response.content)
    cover_image = Image.open(cover_art_bytes).convert("RGB")
    cover_data = cover_image.resize((800, 800))
    buffered = BytesIO()
    cover_data.save(buffered, format="JPEG")
    cover_buffered = buffered.getvalue()

    return track_data.get("metadata", {}), track_data, cover_buffered


# Identify track by matching upload filename against URLs in metadata
def get_track_metadata(filename, track_data):
    for track in track_data.get("tracks", []):
        json_filename, _ = os.path.splitext(os.path.basename(track["file_url"]))
        if filename == json_filename:
            return track
    return None


# Handle audio conversion
def convert_audio_file(input_file, file_format):
    global temp_dir

    # Identify the desired file format and then process accordingly
    wav_audio = AudioSegment.from_file(input_file, format="wav")
    audio_file_path = os.path.join(temp_dir, os.path.basename(input_file).replace(".wav", f".{file_format}"))

    if file_format == "flac":
        wav_audio.export(audio_file_path, format="flac")
    elif file_format == "m4a":
        wav_audio.export(audio_file_path, format="ipod", codec="alac")

    return audio_file_path


# Add metadata to files
def add_metadata_to_file(audio_file_path, album_metadata, track_metadata):
    file_format = os.path.splitext(audio_file_path)[1][1:].lower()

    # Handle FLAC-specific metadata
    if file_format == "flac":
        audio = FLAC(audio_file_path)
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

    # Handle M4A-specific metadata
    elif file_format == "m4a":
        audio = MP4(audio_file_path)
        audio["\xa9nam"] = track_metadata.get("track_name", "")
        audio["trkn"] = [(track_metadata.get("track_number", 0), 0)]
        audio["\xa9ART"] = album_metadata.get("artist_name", "")
        audio["aART"] = album_metadata.get("album_artist", "")
        audio["\xa9alb"] = album_metadata.get("album_name", "")
        audio["\xa9gen"] = album_metadata.get("genre", "")
        audio["\xa9day"] = str(album_metadata.get("year", ""))
        audio["covr"] = [MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)]

    audio.save()
    return audio_file_path


# Process and upload files
def process_and_upload_file(input_file, album_metadata, track_metadata, blob_name, file_format):
    spinner.start(colored(f"Converting to {file_format.upper()} and adding metadata...", "cyan"))

    # Convert file to specified format and add metadata
    converted_file = convert_audio_file(input_file, file_format)
    converted_file_with_metadata = add_metadata_to_file(converted_file, album_metadata, track_metadata)

    # Set content type for Azure (this makes it playable in browsers)
    content_type = "audio/mp4" if file_format.lower() == "m4a" else "audio/flac"
    content_settings = ContentSettings(content_type=content_type)

    spinner.start(colored(f"Uploading {file_format.upper()} to Azure...", "cyan"))

    # Upload file to Azure
    blob_client = container_client.get_blob_client(f"ev/{blob_name}.{file_format}")
    with open(converted_file_with_metadata, "rb") as data:
        blob_client.upload_blob(data, content_settings=content_settings, overwrite=True)

    spinner.succeed(colored(f"{file_format.upper()} tagged and uploaded!", "green"))


# Purge the Azure CDN cache
def purge_azure_cdn_cache():
    try:
        spinner.start(colored("Purging CDN cache (takes a while, Ctrl-C to skip)...", "cyan"))
        process = subprocess.run(
            "az cdn endpoint purge --resource-group dsfiles --name dsfiles --profile-name dsfiles --content-paths /ev",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if process.returncode != 0:
            raise Exception(f"Failed to purge Azure CDN cache. Error: {process.stderr.decode('utf-8')}")

        spinner.succeed(colored("CDN cache purged!", "green"))
    except KeyboardInterrupt:
        spinner.warn(colored("CDN purge skipped.", "yellow"))
    except Exception as e:
        spinner.fail(f"Failed to purge CDN: {e}")


# Main function
def main(filename, input_file):
    global album_metadata, track_metadata, cover_data, temp_dir
    album_metadata, track_data, cover_data = fetch_metadata()
    try:
        blob_name, _ = os.path.splitext(filename)

        # Try to identify the track being uploaded
        spinner.start(colored("Matching track metadata...", "cyan"))
        track_metadata = get_track_metadata(filename, track_data)
        if not track_metadata:
            spinner.fail(colored("Error: No matching track found in the JSON metadata.", "red"))
            return
        track_matched = track_metadata.get("track_name", "")
        album_metadata = track_data.get("metadata", {})
        spinner.succeed(colored(f"Track matched: {track_matched}", "green"))

        # Process and upload the FLAC version then the M4A version
        process_and_upload_file(input_file, album_metadata, track_metadata, blob_name, "flac")
        process_and_upload_file(input_file, album_metadata, track_metadata, blob_name, "m4a")

        # Purge the Azure CDN cache so the new files are available
        purge_azure_cdn_cache()
    except Exception as e:
        spinner.fail(colored(f"An error occurred: {str(e)}", "red"))

    spinner.succeed(colored("All done!", "green"))

    # Copy FLAC URL to clipboard and output both URLs
    flac_url = f"https://files.dannystewart.com/music/ev/{blob_name}.flac"
    m4a_url = f"https://files.dannystewart.com/music/ev/{blob_name}.m4a"
    pyperclip.copy(flac_url)
    print("\nURLs of uploaded files:")
    print(colored(flac_url, "blue"), " <- copied to clipboard")
    print(colored(m4a_url, "blue"))


if __name__ == "__main__":
    # Parse command line arguments
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

    # Make sure the input file is a WAV or AIFF file
    if ext.lower() not in [".wav", ".aif", ".aiff"]:
        print("Invalid file type. Please provide a WAV or AIFF file.")
        sys.exit(1)

    # If no upload filename is given, use the input filename minus the version number
    if args.filename is None:
        args.filename = re.sub(
            r"\s*\d+\.\d+\.\d+(_\d+)?", "", os.path.splitext(os.path.basename(args.input_file))[0]
        ).replace(" ", "-")
        print(colored(f"No filename given, uploading as {args.filename}.flac", "cyan"))

    # Run the main function, aborting on Ctrl-C
    try:
        main(args.filename, args.input_file)
    except KeyboardInterrupt:
        print(colored("\nAborting.", "red"))
        sys.exit(0)
