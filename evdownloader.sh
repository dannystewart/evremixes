#!/bin/bash

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

output_folder="$HOME/Downloads/Evanescence Remixes"
kill_switch=0

# Cleanup function to remove temp files
cleanup() {
    kill_switch=1
    if [ -d "$output_folder" ]; then
        find "$output_folder" -name "*.m4a.temp" -type f -exec rm -f {} +
        if [ "$(find "$output_folder" -maxdepth 0 -empty 2>/dev/null)" ]; then
            rmdir "$output_folder"
        fi
    fi
}

# New trap function to only set kill_switch for SIGINT
ctrl_c() {
    kill_switch=1
    echo ""
    echo -e "${RED}Script aborted. Exiting.${NC}"
    exit 1
}

# Trap to call cleanup function on EXIT, SIGTERM
trap cleanup EXIT SIGTERM

# Separate Trap to call ctrl_c function on SIGINT
trap ctrl_c SIGINT

# Check for jq dependency
if ! command -v jq >/dev/null 2>&1; then
    echo -e "${YELLOW}jq is not installed.${NC}"

    # Check if Homebrew is installed
    if command -v brew >/dev/null 2>&1; then
        echo -e "${GREEN}Homebrew is installed. Attempting to install jq.${NC}"
        brew install jq
    else
        echo -e "${RED}Error: Homebrew is not installed, and jq could not be automatically installed. Please install jq manually before running this script.${NC}"
        exit 1
    fi
fi

# Welcome message
echo -e "${GREEN}Downloading Evanescence Remixes to your Downloads folder...${NC}"

# Fetch JSON and store it in a variable, sorting tracks by track_number
json_data=$(curl -s "https://git.dannystewart.com/danny/evremixes/raw/branch/main/evtracks.json" | jq '(.tracks |= sort_by(.track_number))')

# Create output folder if it doesn't exist, and handle old files if it does
if [ -d "$output_folder" ]; then
    echo -ne "${YELLOW}Folder exists; removing old files to avoid conflicts... ${NC}"
    find "$output_folder" \( -name "*.m4a" -o -name "*.m4a.temp" \) -type f -exec rm -f {} +
    echo -e "${YELLOW}done!${NC}"
else
    mkdir -p "$output_folder"
fi

echo ""

# Loop over each track in the JSON array
length=$(echo "$json_data" | jq '.tracks | length')
for i in $(seq 0 $(($length - 1))); do

    if [ $kill_switch -eq 1 ]; then
        echo -e "${RED}Script aborted. Exiting.${NC}"
        exit 1
    fi

    track_name=$(echo "$json_data" | jq -r ".tracks[$i].track_name")
    file_url=$(echo "$json_data" | jq -r ".tracks[$i].file_url")
    track_number=$(echo "$json_data" | jq -r ".tracks[$i].track_number")

    # Create new .m4a URL
    m4a_url=${file_url/%.flac/.m4a}

    # Generate final and temporary file names
    formatted_track_number=$(printf "%02d" "$track_number")
    temp_filename="$output_folder/$formatted_track_number - $track_name.m4a.temp"
    final_filename="$output_folder/$formatted_track_number - $track_name.m4a"

    # Download .m4a file to temporary filename
    echo -n "Downloading $track_name... "
    if curl --fail-early -s "$m4a_url" -o "$temp_filename"; then
        if [ -f "$temp_filename" ]; then
            mv "$temp_filename" "$final_filename"
            echo -e "${GREEN}done!${NC}"
        else
            echo -e "${YELLOW}File not found. Skipping.${NC}"
        fi
    else
        echo -e "${RED}Download failed. Skipping.${NC}"
    fi
done

echo ""
echo -e "${GREEN}All tracks downloaded!${NC}"
