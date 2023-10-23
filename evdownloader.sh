#!/bin/bash
# shellcheck disable=SC1003,SC2086
# Evanescence remix downloader

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Trap functions for cleanup
cleanup() {
    KILL_SWITCH=1
    if [ -d "$OUTPUT_FOLDER" ]; then
        find "$OUTPUT_FOLDER" -name "*.m4a.temp" -type f -exec rm -f {} +
        if [ "$(find "$OUTPUT_FOLDER" -maxdepth 0 -empty 2>/dev/null)" ]; then
            rmdir "$OUTPUT_FOLDER"
        fi
    fi
}

ctrl_c() {
    KILL_SWITCH=1
    echo ""
    echo -e "${RED}Script aborted. Exiting.${NC}"
    exit 1
}

trap cleanup EXIT SIGTERM
trap ctrl_c SIGINT

# Spinner
spin() {
    local PID=$1
    local DELAY=0.1
    local SPINSTR='|/-\'
    tput civis # Hide cursor
    while [ "$(ps a | awk '{print $1}' | grep $PID)" ]; do
        local temp=${SPINSTR#?}
        printf " [%c]  " "$SPINSTR"
        local SPINSTR=$temp${SPINSTR%"$temp"}
        sleep $DELAY
        printf "\b\b\b\b\b\b"
    done
    tput cnorm # Restore cursor
    printf "    \b\b\b\b"
}

# Check OS and then perform Developer Tools check
if [ "$OS" == "Darwin" ]; then
    if ! xcode-select -p &>/dev/null; then
        echo -e "${YELLOW}Developer Tools are not installed. These are required for the script.${NC}"
        echo -e "${YELLOW}Would you like to install Developer Tools now? (y/n)${NC}"
        read -r answer
        if [ "$answer" == "y" ]; then
            xcode-select --install &>/dev/null

            # Wait until Developer Tools are installed
            echo -e "${YELLOW}Waiting for Developer Tools to install...${NC}"
            until xcode-select -p &>/dev/null; do
                sleep 5
            done

            echo -e "${GREEN}Developer Tools installed. Please rerun the script.${NC}"
            exit 1
        else
            echo -e "${YELLOW}Exiting as Developer Tools are required for this script.${NC}"
            exit 1
        fi
    fi
fi

# Check if ffmpeg is installed
if command -v ffmpeg &>/dev/null; then
    FFMPEG_INSTALLED=true
else
    # Graceful Python test before invoking Python-dependent parts
    if ! python3 -c "print('Python works!')" &>/dev/null; then
        echo -e "${YELLOW}Python did not run correctly, likely due to incomplete Developer Tools setup.${NC}"
        echo -e "${YELLOW}Please rerun the script after ensuring Developer Tools are properly installed.${NC}"
        exit 1
    fi

    echo -e "${YELLOW}Warning: ffmpeg is not installed. Using basic downloader.${NC}"
    echo -e "${YELLOW}See https://dnst.me/evhelp for more information.${NC}"
    FFMPEG_INSTALLED=false
fi

# Use the cool Python version if we have ffmpeg
if [ "$FFMPEG_INSTALLED" = true ]; then
    # Create a temporary directory
    TEMP_DIR=$(mktemp -d -t evremixes-XXXXXX)

    # Identify architecture and OS so we know what binary to use
    ARCH=$(uname -m)
    OS=$(uname)
    URL=""

    if [ "$OS" == "Darwin" ] && [ "$ARCH" == "x86_64" ]; then
        URL="https://git.dannystewart.com/danny/evremixes/raw/branch/main/dist/x86/evremixes"
    elif [ "$OS" == "Darwin" ] && [ "$ARCH" == "arm64" ]; then
        URL="https://git.dannystewart.com/danny/evremixes/raw/branch/main/dist/arm/evremixes"
    elif [ "$OS" == "Linux" ]; then
        URL="https://git.dannystewart.com/danny/evremixes/raw/branch/main/dist/linux/evremixes"
    else
        echo -e "${RED}Error:${NC} Unsupported OS or architecture."
        rm -r "${TEMP_DIR}"
        exit 1
    fi

    # Download the binary for the Python script
    echo -e "${GREEN}Downloading evremixes...${NC}"
    if curl -o "${TEMP_DIR}/evremixes" -L "$URL" --progress-bar; then
        echo -n ""
    else
        echo -e "${RED}Download failed.${NC}"
        rm -r "${TEMP_DIR}"
        exit 1
    fi

    # Make the file executable and run it
    chmod +x "${TEMP_DIR}/evremixes"
    echo -e "${GREEN}Running evremixes...${NC}"
    "${TEMP_DIR}/evremixes"

    # Clean up by removing the temporary directory
    rm -r "${TEMP_DIR}"
else # Fall back to the less cool Bash version if we don't have ffmpeg
    OUTPUT_FOLDER="$HOME/Downloads/Evanescence Remixes"
    KILL_SWITCH=0

    # Welcome message
    echo ""
    echo -e "${GREEN}Saving Evanescence Remixes to ~/Downloads...${NC}"

    # Fetch JSON and store it in a variable, sorting tracks by TRACK_NUMBER
    JSON_DATA=$(curl -s "https://git.dannystewart.com/danny/evremixes/raw/branch/main/evtracks.json" | python3 -c "import sys, json; data=json.load(sys.stdin); data['tracks'] = sorted(data['tracks'], key=lambda x: x['TRACK_NUMBER']); print(json.dumps(data))")

    # Create output folder if it doesn't exist, and handle old files if it does
    if [ -d "$OUTPUT_FOLDER" ]; then
        find "$OUTPUT_FOLDER" \( -name "*.m4a" -o -name "*.m4a.temp" \) -type f -exec rm -f {} +
        echo -e "${YELLOW}Folder already exists; older files removed.${NC}"
    else
        mkdir -p "$OUTPUT_FOLDER"
    fi

    echo ""

    # Loop over each track in the JSON array
    LENGTH=$(echo "$JSON_DATA" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['tracks']))")
    for i in $(seq 0 $(($LENGTH - 1))); do

        if [ $KILL_SWITCH -eq 1 ]; then
            echo -e "${RED}Script aborted. Exiting.${NC}"
            exit 1
        fi

        export INDEX=$i
        TRACK_NAME=$(echo "$JSON_DATA" | python3 -c "import sys, json, os; data=json.load(sys.stdin); i=int(os.environ['INDEX']); print(data['tracks'][i]['TRACK_NAME'])")
        FILE_URL=$(echo "$JSON_DATA" | python3 -c "import sys, json, os; data=json.load(sys.stdin); i=int(os.environ['INDEX']); print(data['tracks'][i]['FILE_URL'])")
        TRACK_NUMBER=$(echo "$JSON_DATA" | python3 -c "import sys, json, os; data=json.load(sys.stdin); i=int(os.environ['INDEX']); print(data['tracks'][i]['TRACK_NUMBER'])")

        # Create new .m4a URL
        M4A_URL=${FILE_URL/%.flac/.m4a}

        # Generate final and temporary file names
        FORMATTED_TRACK_NUMBER=$(printf "%02d" "$TRACK_NUMBER")
        TEMP_FILENAME="$OUTPUT_FOLDER/$FORMATTED_TRACK_NUMBER - $TRACK_NAME.m4a.temp"
        FINAL_FILENAME="$OUTPUT_FOLDER/$FORMATTED_TRACK_NUMBER - $TRACK_NAME.m4a"

        # Initialize retry counter
        RETRY_COUNT=0
        MAX_RETRIES=5

        # Use curl to download the file
        echo -n "[$((i + 1))/$LENGTH] Downloading ${TRACK_NAME}..."

        # Download loop with retry logic
        while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
            if [ $KILL_SWITCH -eq 1 ]; then
                echo -e "${RED}Script aborted. Exiting.${NC}"
                exit 1
            fi

            curl --fail-early -s "$M4A_URL" -o "$TEMP_FILENAME" &
            CURL_PID=$!
            spin $CURL_PID
            wait $CURL_PID
            CURL_EXIT_STATUS=$?

            if [ $CURL_EXIT_STATUS -eq 0 ]; then
                break
            fi

            # Increment retry counter if the download failed
            ((RETRY_COUNT++))

            # Introduce a slight DELAY between attempts
            sleep 1
        done

        # Overwrite the line depending on success or failure
        if [ $CURL_EXIT_STATUS -ne 0 ]; then
            echo -e "\r${RED}Download failed for ${TRACK_NAME}${NC}            " # Extra spaces to clear the spinner
        else
            mv "$TEMP_FILENAME" "$FINAL_FILENAME"
            echo -e "\r${GREEN}✔ ${TRACK_NAME}${NC}                            " # Extra spaces to clear the spinner
        fi
    done

    echo ""
    echo -e "${GREEN}All tracks downloaded! Enjoy!${NC}"

    # Open in Finder if we can
    if [ "$(command -v open)" ]; then
        sleep 1
        open "$OUTPUT_FOLDER"
    fi
fi
