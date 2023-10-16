import os
import argparse
import tempfile
import subprocess
import pyperclip
from azure.storage.blob import BlobServiceClient
from pydub import AudioSegment
from halo import Halo
from termcolor import colored
from dotenv import load_dotenv

# Initialize and load environment variables
spinner = Halo(text="Initializing", spinner="dots")
load_dotenv()

# Variables
allowed_folders = [
    "bm",
    "dw",
    "ev",
    "games",
    "kp",
    "marina",
    "misc",
    "old",
    "original",
    "random",
    "scores",
    "st",
]

# Initialize the Blob Service Client
connection_string = os.environ.get("AZURE_CONNECTION_STRING")
blob_service_client = BlobServiceClient.from_connection_string(connection_string)
container_name = "music"
container_client = blob_service_client.get_container_client(container_name)


# Validate folder
def validate_folder(folder):
    if folder not in allowed_folders:
        raise ValueError(
            f"Folder must be one of the following: {', '.join(allowed_folders)}"
        )


# Convert audio file
def convert_audio(input_file, output_format):
    input_format = os.path.splitext(input_file)[1][1:]
    audio = AudioSegment.from_file(input_file, format=input_format)
    with tempfile.NamedTemporaryFile(
        suffix=f".{output_format}", delete=False
    ) as temp_file:
        audio.export(temp_file.name, format=output_format)
        return temp_file.name


# Upload to Azure
def upload_to_azure(container_name, blob_name, temp_output_file):
    blob_client = container_client.get_blob_client(blob_name)
    with open(temp_output_file, "rb") as data:
        try:
            blob_client.upload_blob(data, overwrite=True)
        except Exception as e:
            raise Exception(f"Error occurred while uploading to Azure: {e}")


# Purge CDN Cache
def purge_cdn_cache(subfolder, blob_name):
    relative_path = f"/{subfolder}/{blob_name}"
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
            relative_path,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if process.returncode != 0:
        raise Exception(
            f"Failed to purge Azure CDN cache. Error: {process.stderr.decode('utf-8')}"
        )


# Repopulate CDN
def repopulate_cdn(blob_client, blob_name):
    try:
        blob_data = blob_client.download_blob()
    except Exception as e:
        raise Exception(f"Failed to download blob {blob_name}. Error: {str(e)}")

    with tempfile.TemporaryDirectory() as tmpdirname:
        temp_file_path = f"{tmpdirname}/temp_{os.path.basename(blob_name)}"
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(blob_data.readall())


# Main function
def main(upload_path, input_file):
    subfolder, blob_name = upload_path.split("/", 1)
    validate_folder(subfolder)

    # Determine input and output formats
    input_format = os.path.splitext(input_file)[1][1:]
    output_format = os.path.splitext(blob_name)[1][1:]
    conversion_spinner = Halo(
        text=colored(
            f"Converting from {input_format.upper()} to {output_format.upper()}...",
            "cyan",
        ),
        spinner="dots",
    ).start()
    temp_output_file = convert_audio(input_file, output_format)
    conversion_spinner.succeed(colored("Conversion complete!", "green"))

    upload_spinner = Halo(
        text=colored("Uploading to Azure...", "cyan"), spinner="dots"
    ).start()
    try:
        upload_to_azure(container_name, f"{subfolder}/{blob_name}", temp_output_file)
        upload_spinner.succeed(colored("Upload complete!", "green"))
    except Exception as e:
        upload_spinner.fail(f"Failed to upload to Azure: {e}")
        return

    purge_spinner = Halo(
        text=colored(
            f"Purging CDN for {blob_name} (this may take a few minutes)...",
            "cyan",
        ),
        spinner="dots",
    ).start()
    try:
        purge_cdn_cache(subfolder, blob_name)
        purge_spinner.succeed(colored("CDN cache purged!", "green"))
    except Exception as e:
        purge_spinner.fail(f"Failed to purge CDN: {e}")

    repopulate_spinner = Halo(
        text=colored("Repopulating CDN...", "cyan"),
        spinner="dots",
    ).start()
    try:
        repopulate_cdn(
            blob_service_client.get_blob_client(
                container=container_name, blob=f"{subfolder}/{blob_name}"
            ),
            blob_name,
        )
        repopulate_spinner.succeed(colored("CDN repopulated!", "green"))
    except Exception as e:
        repopulate_spinner.fail(f"Failed to repopulate CDN: {e}")

    os.remove(temp_output_file)

    final_url = f"https://files.dannystewart.com/music/{upload_path}"
    print(colored("✔ All operations complete!", "green"))
    pyperclip.copy(final_url)
    print("\nURL copied to clipboard:")
    print(colored(f"{final_url}", "blue"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Upload and convert audio file to Azure Blob Storage."
    )
    parser.add_argument(
        "upload_path",
        type=str,
        help="Azure Blob upload path. Format: <container>/<filename>",
    )
    parser.add_argument("input_file", type=str, help="Local input audio file")

    args = parser.parse_args()

    main(args.upload_path, args.input_file)
