#!/bin/bash
# shellcheck disable=SC2086

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

output_folder="$HOME/Downloads/Evanescence Remixes"
kill_switch=0

# Spinner function
spin() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    tput civis # Hide cursor
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    tput cnorm # Restore cursor
    printf "    \b\b\b\b"
}

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

# Welcome message
echo ""
echo -e "${GREEN}Saving Evanescence Remixes to ~/Downloads...${NC}"

# Fetch JSON and store it in a variable, sorting tracks by track_number
json_data=$(curl -s "https://git.dannystewart.com/danny/evremixes/raw/branch/main/evtracks.json" | python3 -c "import sys, json; data=json.load(sys.stdin); data['tracks'] = sorted(data['tracks'], key=lambda x: x['track_number']); print(json.dumps(data))")

# Create output folder if it doesn't exist, and handle old files if it does
if [ -d "$output_folder" ]; then
    find "$output_folder" \( -name "*.m4a" -o -name "*.m4a.temp" \) -type f -exec rm -f {} +
    echo -e "${YELLOW}Folder already exists; older files removed.${NC}"
else
    mkdir -p "$output_folder"
fi

echo ""

# Loop over each track in the JSON array
length=$(echo "$json_data" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['tracks']))")
for i in $(seq 0 $(($length - 1))); do

    if [ $kill_switch -eq 1 ]; then
        echo -e "${RED}Script aborted. Exiting.${NC}"
        exit 1
    fi

    export INDEX=$i
    track_name=$(echo "$json_data" | python3 -c "import sys, json, os; data=json.load(sys.stdin); i=int(os.environ['INDEX']); print(data['tracks'][i]['track_name'])")
    file_url=$(echo "$json_data" | python3 -c "import sys, json, os; data=json.load(sys.stdin); i=int(os.environ['INDEX']); print(data['tracks'][i]['file_url'])")
    track_number=$(echo "$json_data" | python3 -c "import sys, json, os; data=json.load(sys.stdin); i=int(os.environ['INDEX']); print(data['tracks'][i]['track_number'])")

    # Create new .m4a URL
    m4a_url=${file_url/%.flac/.m4a}

    # Generate final and temporary file names
    formatted_track_number=$(printf "%02d" "$track_number")
    temp_filename="$output_folder/$formatted_track_number - $track_name.m4a.temp"
    final_filename="$output_folder/$formatted_track_number - $track_name.m4a"

    # Initialize retry counter
    retry_count=0
    max_retries=5

    # Use curl to download the file
    echo -n "[$((i + 1))/$length] Downloading ${track_name}..."

    # Download loop with retry logic
    while [ $retry_count -lt $max_retries ]; do
        if [ $kill_switch -eq 1 ]; then
            echo -e "${RED}Script aborted. Exiting.${NC}"
            exit 1
        fi

        curl --fail-early -s "$m4a_url" -o "$temp_filename" &
        CURL_PID=$!
        spin $CURL_PID
        wait $CURL_PID
        CURL_EXIT_STATUS=$?

        if [ $CURL_EXIT_STATUS -eq 0 ]; then
            break
        fi

        # Increment retry counter if the download failed
        ((retry_count++))

        # Introduce a slight delay between attempts
        sleep 1
    done

    # Overwrite the line depending on success or failure
    if [ $CURL_EXIT_STATUS -ne 0 ]; then
        echo -e "\r${RED}Download failed for ${track_name}${NC}            " # Extra spaces to clear the spinner
    else
        mv "$temp_filename" "$final_filename"
        echo -e "\r${GREEN}✔ ${track_name}${NC}                            " # Extra spaces to clear the spinner
    fi
done

echo ""
echo -e "${GREEN}All tracks downloaded! Enjoy!${NC}"

# Open in Finder if we can
if [ "$(command -v open)" ]; then
    open "$output_folder"
fi
