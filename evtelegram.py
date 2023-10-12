import json
import os
import requests
import inquirer
import tempfile
from halo import Halo
from mutagen.flac import FLAC
from termcolor import colored
from telebot import TeleBot

spinner = Halo(text="Initializing", spinner="dots")

# Initialize Telegram Bot API
bot_token = "6656812775:AAFNU2RKWONkxQx3825EHqJqCyor8XxVAzY"
channel_id = "-1001758097505"
bot = TeleBot(bot_token)

# Download and load the JSON file with track details
spinner.start(text=colored("Downloading track details...", "cyan"))
response = requests.get(
    "https://git.dannystewart.com/danny/evremixes/raw/branch/main/evtracks.json"
)
spinner.succeed(text=colored("Downloaded track details.", "green"))

# Download track and album metadata
track_data = json.loads(response.text)
metadata = track_data.get("metadata", {})

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
selected_tracks = [
    track for track in sorted_tracks if track["track_name"] in answers["tracks"]
]

# Create temp directory for downloads and conversions
with tempfile.TemporaryDirectory() as tmpdirname:
    output_folder = tmpdirname

    # Loop through each track
    for track in selected_tracks:
        track_name = track["track_name"]
        file_url = track["file_url"]
        original_filename = os.path.basename(file_url)

        # Download FLAC file
        with Halo(text=colored(f"Downloading {track_name}...", "cyan"), spinner="dots"):
            flac_file_path = f"{output_folder}/{original_filename}"
            response = requests.get(file_url)
            with open(flac_file_path, "wb") as f:
                f.write(response.content)

        # Add metadata using mutagen
        with Halo(
            text=colored(f"Adding metadata to {track_name}...", "cyan"), spinner="dots"
        ):
            audio = FLAC(flac_file_path)
            duration = int(audio.info.length)
            audio["tracknumber"] = str(track.get("track_number", 0))
            audio["title"] = track.get("track_name", "")
            audio["artist"] = metadata.get("artist_name", "")
            audio["album"] = metadata.get("album_name", "")
            audio["date"] = str(metadata.get("year", ""))
            audio["genre"] = metadata.get("genre", "")
            audio.save()

        # Rename file to just the song name
        renamed_flac_file_path = f"{output_folder}/{track_name}.flac"
        os.rename(flac_file_path, renamed_flac_file_path)

        # Upload FLAC file to Telegram
        with Halo(
            text=colored(f"Uploading {track_name} to Telegram...", "cyan"),
            spinner="dots",
        ):
            with open(renamed_flac_file_path, "rb") as f:
                bot.send_audio(
                    channel_id,
                    f,
                    timeout=100,
                    duration=duration,
                    title=track_name,
                    performer=metadata.get("artist_name", ""),
                )

        print(colored(f"✔ Uploaded {track_name}!", "green"))

print(colored("\nAll selected tracks uploaded to Telegram!", "green"))
