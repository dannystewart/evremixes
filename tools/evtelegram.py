#!/usr/bin/env python3

import argparse
import inquirer
import json
import os
import requests
import sys
import tempfile
import time
from dotenv import load_dotenv
from halo import Halo
from io import BytesIO
from mutagen.mp4 import MP4, MP4Cover
from PIL import Image
from pydub import AudioSegment
from telebot import TeleBot
from termcolor import colored

# Initialize the spinner
spinner = Halo(text="Initializing", spinner="dots")

# Parse arguments
parser = argparse.ArgumentParser(description="Upload audio tracks to Telegram channel.")
parser.add_argument("--comment", action="store_true", help="Include comments on uploads")
args = parser.parse_args()

# Get the script directory and assemble paths
script_directory = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_directory, ".env")
upload_cache_path = os.path.join(script_directory, "upload_cache.json")

# Load environment variables
load_dotenv()
load_dotenv(dotenv_path=env_path)

# Initialize Telegram Bot API
bot_token = os.environ.get("EV_TELEGRAM_BOT_TOKEN")
channel_id = os.environ.get("EV_TELEGRAM_CHANNEL_ID")

# We can't proceed if we don't have the Telegram info
if bot_token is None or channel_id is None:
    print("Error: Telegram info not found. Check environment variables.")
    sys.exit(1)

# Initialize the Telegram bot
bot = TeleBot(bot_token)


# Check to see whether anything is deletable
def has_deletable_tracks(upload_cache):
    current_time = int(time.time())
    forty_eight_hours_ago = current_time - (48 * 60 * 60)

    for key in upload_cache:
        for msg_id, timestamp in upload_cache[key]:
            if timestamp >= forty_eight_hours_ago:
                return True
    return False


# Function to remove entries older than 48 hours from the upload cache
def remove_old_entries(upload_cache):
    forty_eight_hours_ago = int(time.time()) - (48 * 60 * 60)

    for key in list(upload_cache.keys()):
        new_entries = []

        for msg_id, timestamp in upload_cache[key]:
            if timestamp >= forty_eight_hours_ago:
                new_entries.append([msg_id, timestamp])
            else:
                print(f"Removing entry with timestamp {timestamp}")

        upload_cache[key] = new_entries

        if not upload_cache[key]:
            del upload_cache[key]


# Check for local upload cache and prune old entries
try:
    with open(upload_cache_path, "r") as f:
        upload_cache = json.load(f)
except FileNotFoundError:
    upload_cache = {}

remove_old_entries(upload_cache)

with open(upload_cache_path, "w") as f:
    json.dump(upload_cache, f, indent=4)


# Include comments if argument is supplied
include_comments = True if args.comment else False


# Sort tracks based on upload history
def get_upload_order(track):
    upload_info = upload_cache.get(track["track_name"], 0)
    if isinstance(upload_info, list):
        return max(upload_info)  # Return the maximum ID if it's a list
    else:
        return upload_info  # Return the ID directly if it's an int


# Download and load the JSON file with track details
spinner.start(text=colored("Downloading track details...", "cyan"))
response = requests.get(
    "https://git.dannystewart.com/danny/evremixes/raw/branch/main/evtracks.json"
)
spinner.stop()

# Show spinner as we prep
spinner.start(text=colored("Preparing track details...", "cyan"))

# Download track and album metadata, plus cover art
track_data = json.loads(response.text)
metadata = track_data.get("metadata", {})
cover_response = requests.get(metadata.get("cover_art_url", ""))
cover_data_original = cover_response.content

# Initialize variables to store optional comments
track_comments = {}

# Convert to JPEG and resize to 800x800 using PIL
image = Image.open(BytesIO(cover_data_original))
image = image.convert("RGB")  # Convert to RGB if image is not in this mode
image = image.resize((800, 800))

# Save the image data to a BytesIO object, then to a byte array
buffered = BytesIO()
image.save(buffered, format="JPEG")
cover_data = buffered.getvalue()

spinner.stop()

# Only prompt for deletion if there are recent uploads
if has_deletable_tracks(upload_cache):
    delete_prev_versions_question = [
        inquirer.Confirm(
            "delete_prev_versions",
            message="Delete previous versions of track uploads?",
            default=True,
        ),
    ]
    delete_prev_versions_answer = inquirer.prompt(delete_prev_versions_question)["delete_prev_versions"]
else:
    delete_prev_versions_answer = False

# Sort tracks and display menu
sorted_tracks = sorted(track_data["tracks"], key=get_upload_order, reverse=True)
questions = [
    inquirer.Checkbox(
        "tracks",
        message="Select tracks to upload (Ctrl-A for all)",
        choices=[track["track_name"] for track in sorted_tracks],
    ),
]
answers = inquirer.prompt(questions)
selected_tracks = [track for track in sorted_tracks if track["track_name"] in answers["tracks"]]

# If yes, get comments for selected tracks before uploading
if include_comments:
    for track in selected_tracks:
        comment = input(f"Enter comment for {track['track_name']}: ")
        track_comments[track["track_name"]] = comment

# Sort selected tracks by start_date for the upload process
selected_tracks = sorted(selected_tracks, key=lambda x: x["start_date"])

# Create temp directory for downloads and conversions
with tempfile.TemporaryDirectory() as tmpdirname:
    output_folder = tmpdirname

    # Loop through each track
    for track in selected_tracks:
        track_name = track["track_name"]
        file_url = track["file_url"]
        original_filename = os.path.basename(file_url)
        spinner.stop()
        spinner.clear()

        # Download FLAC file
        with Halo(text=colored(f"Downloading {track_name}...", "cyan"), spinner="dots"):
            flac_file_path = f"{output_folder}/{original_filename}"
            response = requests.get(file_url)
            with open(flac_file_path, "wb") as f:
                f.write(response.content)

        # Rename file to just the song name
        renamed_flac_file_path = f"{output_folder}/{track_name}.flac"
        os.rename(flac_file_path, renamed_flac_file_path)

        # Convert FLAC to ALAC (M4A)
        with Halo(text=colored(f"Converting {track_name} to ALAC...", "cyan"), spinner="dots"):
            m4a_file_path = f"{output_folder}/{track_name}.m4a"
            audio = AudioSegment.from_file(renamed_flac_file_path, format="flac")
            audio.export(m4a_file_path, format="ipod", codec="alac")

        # Add metadata and cover art using mutagen
        with Halo(
            text=colored(f"Adding metadata and cover art to {track_name} ALAC...", "cyan"),
            spinner="dots",
        ):
            audio = MP4(m4a_file_path)
            audio["trkn"] = [(track.get("track_number", 0), 0)]
            audio["\xa9nam"] = track.get("track_name", "")
            audio["\xa9ART"] = metadata.get("artist_name", "")
            audio["\xa9alb"] = metadata.get("album_name", "")
            audio["\xa9day"] = str(metadata.get("year", ""))
            audio["\xa9gen"] = metadata.get("genre", "")
            audio["covr"] = [MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)]
            duration = int(audio.info.length)

            if "album_artist" in metadata:
                audio["aART"] = metadata.get("album_artist", "")
            if "comments" in track:
                audio["\xa9cmt"] = track["comments"]

            audio.save()

        # Before uploading a new track
        track_key = track_name
        old_message_ids = upload_cache.get(track_key, [])

        # Upload the ALAC file to Telegram
        with Halo(
            text=colored(f"Uploading {track_name} to Telegram...", "cyan"),
            spinner="dots",
        ):
            with open(m4a_file_path, "rb") as f:
                caption_text = track_comments.get(track_name, None) if include_comments else None
                message = bot.send_audio(
                    channel_id,
                    f,
                    timeout=100,
                    duration=duration,
                    title=track_name,
                    performer=metadata.get("artist_name", ""),
                    disable_notification=True,
                    caption=caption_text,
                )

        spinner.stop()

        # Confirm successful upload before proceeding
        if message:
            message_id = message.message_id
            if delete_prev_versions_answer:
                # Delete old messages
                for old_id in old_message_ids:
                    try:
                        bot.delete_message(channel_id, old_id)
                        print(
                            colored(
                                f"✔ Deleted previous {track_name} upload with ID {old_id[0]}.",
                                "green",
                            ),
                            flush=True,
                        )
                    except Exception as e:
                        print(
                            colored(
                                f"Could not delete previous {track_name} upload with ID {old_id[0]}: {e}",
                                "red",
                            )
                        )
                # Record new message ID
                current_time = int(time.time())
                upload_cache[track_key] = [(message_id, current_time)]
            else:
                # Append new message ID to the list
                if isinstance(old_message_ids, list):
                    current_time = int(time.time())
                    old_message_ids.append((message_id, current_time))
                else:
                    old_message_ids = [message_id]
                upload_cache[track_key] = old_message_ids

            print(colored(f"✔ Successfully uploaded {track_name}!", "green"), flush=True)

            # Save updated cache to file
            with open("upload_cache.json", "w") as f:
                json.dump(upload_cache, f, indent=4)

        else:
            spinner.fail(text=colored(f"Failed to upload {track_name}.", "red"))

        # Clear misbehaving spinners
        spinner.stop()
        spinner.clear()

print(colored("\nSelected tracks uploaded to Telegram!", "green"))
