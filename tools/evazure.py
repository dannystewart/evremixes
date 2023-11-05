#!/usr/bin/env python3

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from io import BytesIO

import inquirer
import pyperclip
import requests
from azure.storage.blob import BlobServiceClient, ContentSettings, StandardBlobTier
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


# Menu interface for selecting track metadata
def get_track_metadata_menu(track_data):
    tracks = track_data.get("tracks", [])
    questions = [
        inquirer.List(
            "track",
            message="Couldn't match filename. Please select track",
            choices=sorted([f"{track['track_name']}" for track in tracks]),
            carousel=True,
        )
    ]
    answers = inquirer.prompt(questions)
    selected_track_name = answers["track"]

    for track in tracks:
        if track["track_name"] == selected_track_name:
            return track
    return None


# Handle audio conversion
def convert_audio_file(input_file, file_format):
    global temp_dir

    # Identify the desired file format and then process accordingly
    wav_audio = AudioSegment.from_file(input_file, format="wav")
    extension = "m4a" if file_format == "alac" else file_format
    audio_file_path = os.path.join(temp_dir, os.path.basename(input_file).replace(".wav", f".{extension}"))

    if file_format == "flac":
        wav_audio.export(audio_file_path, format="flac")
    elif file_format == "alac":
        wav_audio.export(audio_file_path, format="ipod", codec="alac")

    return audio_file_path


# Add metadata to files
def add_metadata_to_file(audio_file_path, album_metadata, track_metadata):
    file_extension = os.path.splitext(audio_file_path)[1][1:].lower()
    file_format = "alac" if file_extension == "m4a" else file_extension

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

    # Handle ALAC-specific metadata
    elif file_format == "alac":
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
    file_extension = file_format
    converted_file = convert_audio_file(input_file, file_format)
    converted_file_with_metadata = add_metadata_to_file(converted_file, album_metadata, track_metadata)

    # Set content type for Azure (this makes it playable in browsers)
    content_settings_kwargs = {"content_type": "audio/flac" if file_format == "flac" else "audio/mp4"}
    if file_format == "alac":
        content_settings_kwargs["content_disposition"] = "inline"
        file_extension = "m4a"
    content_settings = ContentSettings(**content_settings_kwargs)

    spinner.start(colored(f"Uploading {file_format.upper()} to Azure...", "cyan"))

    # Upload file to Azure
    blob_client = container_client.get_blob_client(f"ev/{blob_name}.{file_extension}")
    with open(converted_file_with_metadata, "rb") as data:
        blob_client.upload_blob(
            data, content_settings=content_settings, overwrite=True, standard_blob_tier=StandardBlobTier.Hot
        )

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
def main(filename, input_file, desired_formats):
    global album_metadata, track_metadata, cover_data, temp_dir
    album_metadata, track_data, cover_data = fetch_metadata()
    try:
        blob_name, _ = os.path.splitext(filename)

        # Try to identify the track being uploaded
        spinner.start(colored("Matching track metadata...", "cyan"))
        track_metadata = get_track_metadata(filename, track_data)
        if not track_metadata:
            spinner.stop()
            track_metadata = get_track_metadata_menu(track_data)
            if not track_metadata:
                spinner.fail(colored("Error: No track was selected.", "red"))
                return
        track_matched = track_metadata.get("track_name", "")
        album_metadata = track_data.get("metadata", {})
        spinner.succeed(colored(f"Track matched: {track_matched}", "green"))

        # Process and upload the desired formats
        for format in desired_formats:
            process_and_upload_file(input_file, album_metadata, track_metadata, blob_name, format)

        # Purge the Azure CDN cache so the new files are available
        if not args.skip_purge:
            purge_azure_cdn_cache()

    except Exception as e:
        spinner.fail(colored(f"An error occurred: {str(e)}", "red"))

    spinner.succeed(colored("All done!", "green"))

    # Print URLs of uploaded files and copy one to clipboard
    uploaded_urls = {}
    clipboard_url = None
    if "flac" in desired_formats:
        flac_url = f"https://files.dannystewart.com/music/ev/{blob_name}.flac"
        uploaded_urls["flac"] = flac_url
        clipboard_url = flac_url
    if "alac" in desired_formats:
        alac_url = f"https://files.dannystewart.com/music/ev/{blob_name}.m4a"
        uploaded_urls["alac"] = alac_url
        if not clipboard_url:
            clipboard_url = alac_url

    # Only attempt to copy to clipboard if clipboard_url is not None
    if clipboard_url:
        pyperclip.copy(clipboard_url)
    else:
        print(colored("No URL was copied to clipboard.", "yellow"))

    # Print all uploaded URLs
    print("\nURLs of uploaded files:")
    for format, url in uploaded_urls.items():
        print(colored(url, "blue"), end="")
        if url == clipboard_url:
            print("  <- copied to clipboard")
        else:
            print()


if __name__ == "__main__":
    # Initialize parser and use nargs='*' to collect arguments
    parser = argparse.ArgumentParser(description="Upload and convert audio file to Azure Blob Storage.")
    parser.add_argument("args", nargs="*", help="Optional input and output file names")
    parser.add_argument("--flac-only", action="store_true", help="Only convert and upload FLAC file")
    parser.add_argument("--alac-only", action="store_true", help="Only convert and upload ALAC file")
    parser.add_argument("--skip-purge", action="store_true", help="Skip Azure CDN purge")
    parser.add_argument("--purge-only", action="store_true", help="Run CDN purge without uploading")

    args = parser.parse_args()

    # Handle the purge-only case
    if args.purge_only:
        if args.args:
            print(colored("No additional arguments are needed when using --purge-only.", "red"))
            sys.exit(1)
        purge_azure_cdn_cache()
        print(colored("CDN purge complete!", "green"))
        sys.exit(0)

    # Check for required arguments
    if not args.args:
        print(colored("Please specify an input file.", "red"))
        sys.exit(1)

    # Handle the input file and optional filename
    input_file = args.args[-1]
    filename = args.args[0] if len(args.args) > 1 else None

    # Validate input file
    if not os.path.isfile(input_file):
        print(colored(f"The specified input file does not exist: {input_file}", "red"))
        sys.exit(1)

    # Make sure the input file is a WAV or AIFF file
    _, ext = os.path.splitext(input_file)
    if ext.lower() not in [".wav", ".aif", ".aiff"]:
        print(colored("Invalid file type. Please provide a WAV or AIFF file.", "red"))
        sys.exit(1)

    # Determine desired formats based on arguments or filename
    desired_formats = []
    if filename:
        _, upload_ext = os.path.splitext(filename)
        upload_ext = upload_ext.lower()
        if upload_ext in [".m4a", ".flac"]:
            desired_format = "alac" if upload_ext == ".m4a" else "flac"
            desired_formats = [desired_format]
            filename = os.path.splitext(filename)[0]
        elif args.flac_only:
            desired_formats = ["flac"]
        elif args.alac_only:
            desired_formats = ["alac"]
        else:
            desired_formats.extend(["flac", "alac"])
    else:
        if args.flac_only:
            desired_formats = ["flac"]
        elif args.alac_only:
            desired_formats = ["alac"]
        else:
            desired_formats.extend(["flac", "alac"])

    # If no upload filename is given, derive it from the input file
    if filename is None:
        filename = re.sub(
            r"\s*\d+\.\d+\.\d+(_\d+)?", "", os.path.splitext(os.path.basename(input_file))[0]
        ).replace(" ", "-")
        print(colored(f"No filename given, uploading as {filename}.{desired_formats[0]}", "cyan"))

    # Run the main function, aborting on Ctrl-C
    try:
        main(filename, input_file, desired_formats)
    except KeyboardInterrupt:
        print(colored("\nAborting.", "red"))
        sys.exit(0)
