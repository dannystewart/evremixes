import json
import os
import requests
import shutil
from getch import getch
from halo import Halo
from io import BytesIO
from mutagen.mp4 import MP4, MP4Cover
from PIL import Image
from pydub import AudioSegment
from termcolor import colored

spinner = Halo(text="Initializing", spinner="dots")

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

# Ask the user for the output directory
default_output_folder = os.path.expanduser("~/Downloads")
output_base_folder = (
    input(
        colored(
            f"Enter output directory (hit Enter for {default_output_folder}): ",
            "cyan",
        )
    )
    or default_output_folder
)

# Determine the output folder based on the album name for the entire set of tracks
album_folder = metadata.get("album_name", "Unknown Album")
output_folder = os.path.join(output_base_folder, album_folder)

# Check if the folder exists and has files
if os.path.exists(output_folder) and os.listdir(output_folder):
    print(
        colored(
            "The folder already exists and contains files. Remove them? (Y/n): ",
            "yellow",
        ),
        end="",
    )
    remove_files = getch().lower()  # Get a single character and convert to lowercase

    # Replace newline with space for display purposes
    echo_char = remove_files if remove_files != "\n" else " "
    print(echo_char)  # Echo the character

    # Default to 'y' if the user just hits Enter
    if remove_files == "\n" or remove_files == "y":
        remove_files = "y"

    # Only execute the delete code if output_folder is a subdirectory of output_base_folder,
    # not output_base_folder itself
    if os.path.commonpath([output_folder, output_base_folder]) == output_base_folder and \
        output_folder != output_base_folder:

        if remove_files == "y":
            for filename in os.listdir(output_folder):
                file_path = os.path.join(output_folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f"Failed to delete {file_path}. Reason: {e}")

    else:
        print("Deletion aborted: Target folder is not a subfolder of the base directory.")

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Sort tracks by track number
track_data["tracks"] = sorted(
    track_data["tracks"], key=lambda k: k.get("track_number", 0)
)

# Loop through each track
for track in track_data["tracks"]:
    track_name = track["track_name"]
    track_number = str(track.get("track_number", "")).zfill(2)
    track_number_short = str(track.get("track_number", ""))

    # Determine the output folder based on the album name for the track
    album_folder = metadata.get("album_name", "Unknown Album")
    output_folder = os.path.join(output_base_folder, album_folder)

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    print(f"Processing track {track_number_short}, {track_name}...")

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
        audio["trkn"] = [(track.get("track_number", 0), 0)]
        audio["\xa9nam"] = track.get("track_name", "")
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

print(colored("\nAll tracks downloaded and ready!", "green"))
