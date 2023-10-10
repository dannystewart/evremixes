#!/bin/bash

# Define colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Create a temporary directory
temp_dir=$(mktemp -d -t evremixes-XXXXXX)

# Check if ffmpeg is installed
if ! command -v ffmpeg &>/dev/null; then
    echo -e "${RED}Warning:${NC} ffmpeg is not installed."
    # Check if Homebrew is installed
    if command -v brew &>/dev/null; then
        echo -e "${GREEN}Homebrew is installed, attempting to install ffmpeg...${NC}"
        brew install ffmpeg
        if [ $? -ne 0 ]; then
            echo -e "${RED}Failed to install ffmpeg.${NC}"
            rm -r "${temp_dir}"
            exit 1
        fi
    else
        echo -e "${RED}Warning:${NC} Homebrew is not installed. Attempting to install it now..."
        # Install Homebrew
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        if [ $? -ne 0 ]; then
            echo -e "${RED}Failed to install Homebrew.${NC}"
            rm -r "${temp_dir}"
            exit 1
        fi

        # Add brew to PATH for this session based on architecture and OS
        case "$(uname -m)" in
        'arm64')
            # For ARM architecture
            export PATH="/opt/homebrew/bin:$PATH"
            ;;
        'x86_64')
            # For x86 architecture
            case "$(uname -s)" in
            'Linux')
                export PATH="/home/linuxbrew/.linuxbrew/bin:$PATH"
                ;;
            'Darwin')
                export PATH="/usr/local/bin:$PATH"
                ;;
            esac
            ;;
        esac

        # Now install ffmpeg
        echo -e "${GREEN}Homebrew installed successfully, attempting to install ffmpeg...${NC}"
        brew install ffmpeg
        if [ $? -ne 0 ]; then
            echo -e "${RED}Failed to install ffmpeg.${NC}"
            rm -r "${temp_dir}"
            exit 1
        fi
    fi
fi

# Determine architecture
ARCH=$(uname -m)
URL=""

if [ "$ARCH" == "x86_64" ]; then
    URL="https://git.dannystewart.com/danny/evremixes/raw/branch/main/dist/x86/evremixes"
elif [ "$ARCH" == "arm64" ]; then
    URL="https://git.dannystewart.com/danny/evremixes/raw/branch/main/dist/arm/evremixes"
else
    echo -e "${RED}Error:${NC} Unsupported architecture."
    rm -r "${temp_dir}"
    exit 1
fi

# Check if curl is installed
if ! command -v curl &>/dev/null; then
    echo -e "${RED}Error:${NC} curl is not installed. Please install it and try again."
    exit 1
fi

# Fancy download with user feedback
echo -e "${GREEN}Downloading evremixes...${NC}"
if curl -o "${temp_dir}/evremixes" -L "$URL" --progress-bar; then
    echo -n ""
else
    echo -e "${RED}Download failed.${NC}"
    rm -r "${temp_dir}"
    exit 1
fi

# Make the file executable
chmod +x "${temp_dir}/evremixes"

# Run the program
echo -e "${GREEN}Running evremixes...${NC}"
"${temp_dir}/evremixes"

# Clean up by removing the temporary directory
rm -r "${temp_dir}"
