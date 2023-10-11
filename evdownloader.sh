#!/bin/bash

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Cleanup function to remove temp files
cleanup() {
    find "$output_folder" -name "*.m4a.temp" -type f -exec rm -f {} +
}

# Trap to call cleanup function on EXIT, SIGINT, SIGTERM
trap cleanup EXIT SIGINT SIGTERM

# Fetch JSON and store it in a variable, sorting tracks by track_number
json_data=$(curl -s "https://git.dannystewart.com/danny/evremixes/raw/branch/main/evtracks.json" | jq '(.tracks |= sort_by(.track_number))')

# Create output folder if it doesn't exist
output_folder="$HOME/Downloads/Evanescence Remixes"
mkdir -p "$output_folder"

# If folder exists, remove any existing .m4a and .m4a.temp files
if [ -d "$output_folder" ]; then
    echo -e "${YELLOW}Folder already exists; removing old files to avoid conflicts.${NC}"
    find "$output_folder" \( -name "*.m4a" -o -name "*.m4a.temp" \) -type f -exec rm -f {} +
fi

# Loop over each track in the JSON array
length=$(echo "$json_data" | jq '.tracks | length')
for i in $(seq 0 $(($length - 1))); do
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
    curl -s "$m4a_url" -o "$temp_filename"

    # Move temporary file to final filename
    mv "$temp_filename" "$final_filename"
    echo -e "${GREEN}done!${NC}"
done

echo ""
echo -e "${GREEN}All tracks downloaded!${NC}"
