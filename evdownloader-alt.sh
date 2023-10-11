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

# Trap to call cleanup function on EXIT, SIGTERM
trap cleanup EXIT SIGTERM

# Welcome message
echo -e "${BLUE}Welcome to Danny's Evanescence remix downloader!${NC}"
echo -e "${BLUE}Files will be saved under \"Evanescence Remixes\" in your Downloads folder.${NC}"
echo ""

# Fetch JSON and save it to a temporary file
temp_file=$(mktemp)
curl -s "https://git.dannystewart.com/danny/evremixes/raw/branch/main/evtracks.json" > "$temp_file"

# Create output folder if it doesn't exist
if [ -d "$output_folder" ]; then
    echo -e "${YELLOW}Folder already exists; removing any old files to avoid potential conflicts.${NC}"
    find "$output_folder" \( -name "*.m4a" -o -name "*.m4a.temp" \) -type f -exec rm -f {} +
else
    mkdir -p "$output_folder"
fi

# Parse the JSON in Bash (this assumes a specific formatting of the JSON)
while read -r line; do
    key=$(echo "$line" | awk -F: '{print $1}' | sed 's/["{}, ]//g')
    value=$(echo "$line" | awk -F: '{gsub(/^ *"|",? *$/, "", $2); print $2}')

    case "$key" in
        "track_name")
            track_name=$value
            ;;
        "track_number")
            track_number=$value
            ;;
        "file_url")
            file_url=$value
            ;;
    esac

    if [[ -n $track_name && -n $track_number && -n $file_url ]]; then
        if [ $kill_switch -eq 1 ]; then
            echo -e "${RED}Script aborted. Exiting.${NC}"
            exit 1
        fi

        echo "Debug: Original File URL is $file_url"

        # Create new .m4a URL
        m4a_url=${file_url/%.flac/.m4a}

        # Generate final and temporary file names
        track_number=$(echo "$track_number" | sed 's/,$//')
        formatted_track_number=$(printf "%02d" "$track_number")
        temp_filename="$output_folder/$formatted_track_number - $track_name.m4a.temp"
        final_filename="$output_folder/$formatted_track_number - $track_name.m4a"

        # Download .m4a file to temporary filename
        echo -n "Downloading $track_name... "
        echo "Debug: Downloading from $m4a_url"

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

        # Reset variables for the next iteration
        unset track_name track_number file_url
    fi
done < "$temp_file"

# Remove the temporary JSON file
rm -f "$temp_file"

echo ""
echo -e "${GREEN}All tracks downloaded!${NC}"
