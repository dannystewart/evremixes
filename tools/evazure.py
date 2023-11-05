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
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv()
load_dotenv(dotenv_path=env_path)
connection_string = os.getenv("AZURE_CONNECTION_STRING")
if not connection_string:
    print(colored("Error: AZURE_CONNECTION_STRING not found. Check environment variables.", "red"))
    sys.exit(1)
container_client = BlobServiceClient.from_connection_string(connection_string).get_container_client("music")


# Retrieve and prepare metadata
def fetch_metadata():
    spinner.start(colored("Downloading track metadata...", "cyan"))
    response = requests.get("https://git.dannystewart.com/danny/evremixes/raw/branch/main/evtracks.json")
    track_data = json.loads(response.text)
    cover_data = (
        Image.open(BytesIO(requests.get(track_data.get("metadata", {}).get("cover_art_url", "")).content))
        .convert("RGB")
        .resize((800, 800))
    )
    buffered = BytesIO()
    cover_data.save(buffered, format="JPEG")
    return track_data.get("metadata", {}), track_data, buffered.getvalue()


# Identify track based on downloaded metadata
def get_track_metadata(filename, track_data):
    for track in track_data.get("tracks", []):
        json_filename, _ = os.path.splitext(os.path.basename(track["file_url"]))
        if filename == json_filename:
            return track
    return None


# Handle audio conversion
def convert_audio(input_file, file_format):
    global temp_dir
    wav_audio = AudioSegment.from_file(input_file, format="wav")
    audio_file_path = os.path.join(temp_dir, os.path.basename(input_file).replace(".wav", f".{file_format}"))
    if file_format == "flac":
        wav_audio.export(audio_file_path, format="flac")
    elif file_format == "m4a":
        wav_audio.export(audio_file_path, format="ipod", codec="alac")
    return audio_file_path


# Add metadata to files
def add_metadata(audio_file_path, album_metadata, track_metadata):
    file_format = os.path.splitext(audio_file_path)[1][1:].lower()
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
def process_and_upload(input_file, album_metadata, track_metadata, blob_name, file_format):
    global temp_dir
    spinner.start(colored(f"Converting to {file_format.upper()} and adding metadata...", "cyan"))
    add_metadata(convert_audio(input_file, file_format), album_metadata, track_metadata)
    spinner.start(colored(f"Uploading {file_format.upper()} to Azure...", "cyan"))
    blob_client = container_client.get_blob_client(f"ev/{blob_name}.{file_format}")
    with open(convert_audio(input_file, file_format), "rb") as data:
        blob_client.upload_blob(data, overwrite=True)
    spinner.succeed(colored(f"{file_format.upper()} tagged and uploaded!", "green"))


# Purge Azure CDN cache
def purge_cdn_cache():
    process = subprocess.run(
        "az cdn endpoint purge --resource-group dsfiles --name dsfiles --profile-name dsfiles --content-paths /ev",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.returncode != 0:
        raise Exception(f"Failed to purge Azure CDN cache. Error: {process.stderr.decode('utf-8')}")


# Main function
def main(filename, input_file):
    global album_metadata, track_metadata, cover_data, temp_dir
    album_metadata, track_data, cover_data = fetch_metadata()
    try:
        blob_name, _ = os.path.splitext(filename)
        spinner.start(colored("Starting processing of audio files...", "cyan"))
        spinner.start(colored("Matching track metadata...", "cyan"))
        track_metadata = get_track_metadata(filename, track_data)
        if not track_metadata:
            spinner.fail(colored("Error: No matching track found in the JSON metadata.", "red"))
            return
        track_matched = track_metadata.get("track_name", "")
        album_metadata = track_data.get("metadata", {})
        spinner.succeed(colored(f"Track matched: {track_matched}", "green"))
        process_and_upload(input_file, album_metadata, track_metadata, blob_name, "flac")
        process_and_upload(input_file, album_metadata, track_metadata, blob_name, "m4a")
    except Exception as e:
        spinner.fail(colored(f"An error occurred: {str(e)}", "red"))
    try:
        spinner.start(colored("Purging CDN cache (takes a while, Ctrl-C to skip)...", "cyan"))
        purge_cdn_cache()
        spinner.succeed(colored("CDN cache purged!", "green"))
    except KeyboardInterrupt:
        spinner.warn(colored("CDN purge skipped.", "yellow"))
    except Exception as e:
        spinner.fail(f"Failed to purge CDN: {e}")
    spinner.succeed(colored("All done!", "green"))

    flac_url = f"https://files.dannystewart.com/music/ev/{blob_name}.flac"
    m4a_url = f"https://files.dannystewart.com/music/ev/{blob_name}.m4a"
    pyperclip.copy(flac_url)
    print("\nURLs of uploaded files:")
    print(colored(flac_url, "blue"), " <- copied to clipboard")
    print(colored(m4a_url, "blue"))


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
        args.filename = re.sub(
            r"\s*\d+\.\d+\.\d+_\d+.*", "", os.path.splitext(os.path.basename(args.input_file))[0]
        ).replace(" ", "-")
        print(colored(f"No filename given, uploading as {args.filename}.flac", "cyan"))
    try:
        main(args.filename, args.input_file)
    except KeyboardInterrupt:
        print(colored("\nAborting.", "red"))
        sys.exit(0)
