import json
import os
import requests
import inquirer
import tempfile
from halo import Halo
from io import BytesIO
from mutagen.flac import FLAC
from mutagen.mp4 import MP4, MP4Cover
from PIL import Image
from pydub import AudioSegment
from termcolor import colored
from telebot import TeleBot
from dotenv import load_dotenv

# Initialize and load environment variables
spinner = Halo(text="Initializing", spinner="dots")
load_dotenv()

# Initialize Telegram Bot API
bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
channel_id = os.environ.get('TELEGRAM_CHANNEL_ID')
bot = TeleBot(bot_token)

# Check for local upload cache
try:
    with open("upload_cache.json", "r") as f:
        upload_cache = json.load(f)
except FileNotFoundError:
    upload_cache = {}

# Sort tracks based on upload history
def get_upload_order(track):
    return upload_cache.get(track["track_name"], 0)

# Download and load the JSON file with track details
spinner.start(text=colored("Downloading track details...", "cyan"))
response = requests.get(
    "https://git.dannystewart.com/danny/evremixes/raw/branch/main/evtracks.json"
)
spinner.stop()

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

# Menu
sorted_tracks = sorted(track_data["tracks"], key=get_upload_order, reverse=True)

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

# Sort selected tracks by start_date for the upload process
selected_tracks = sorted(selected_tracks, key=lambda x: x['start_date'])

# Create temp directory for downloads and conversions
with tempfile.TemporaryDirectory() as tmpdirname:
    output_folder = tmpdirname

    # Loop through each track
    for track in selected_tracks:
        # Before starting a new spinner, make sure the previous one is not active
        spinner.stop()
        spinner.clear()

        track_name = track["track_name"]
        file_url = track["file_url"]
        original_filename = os.path.basename(file_url)

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
            text=colored(f"Adding metadata and cover art to {track_name} ALAC...", "cyan"), spinner="dots"
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
        old_message_id = upload_cache.get(track_key)

        # Upload the ALAC file to Telegram
        with Halo(text=colored(f"Uploading {track_name} to Telegram...", "cyan"), spinner="dots"):
            with open(m4a_file_path, "rb") as f:
                message = bot.send_audio(
                    channel_id,
                    f,
                    timeout=100,
                    duration=duration,
                    title=track_name,
                    performer=metadata.get("artist_name", ""),
                    disable_notification=True
                )

        # Stop spinner here before printing anything else
        spinner.stop()
        print("\r" + " " * 50 + "\r", end='', flush=True)

        # Confirm successful upload before proceeding
        if message:
            success_msg = "✔ Successfully uploaded"

            # Delete old message only after successfully uploading the new one
            if old_message_id:
                try:
                    bot.delete_message(channel_id, old_message_id)
                    print(colored(f"✔ Deleted previous upload with ID {old_message_id}.", "green"), flush=True)
                    success_msg += " and replaced"
                except Exception as e:
                    print(colored(f"Could not delete previous upload with ID {old_message_id}: {e}", "red"))

            print(colored(f"{success_msg} {track_name}!", "green"), flush=True)

            # Restart spinner after the print
            spinner.start()

            # Extract message_id from the returned message object
            message_id = message.message_id

            # Update local cache
            upload_cache[track_key] = message_id

            # Save updated cache to file
            with open("upload_cache.json", "w") as f:
                json.dump(upload_cache, f, indent=4)

        else:
            spinner.fail(text=colored(f"Failed to upload {track_name}.", "red"))

        # Clear misbehaving spinners
        spinner.stop()
        spinner.clear()

    # Clear misbehaving spinners
    spinner.stop()
    spinner.clear()

print(colored("\nSelected tracks uploaded to Telegram!", "green"))
