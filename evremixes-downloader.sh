#!/bin/bash

# Define colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Create a temporary directory
temp_dir=$(mktemp -d -t evremixes-XXXXXX)

# Check if curl is installed
if ! command -v curl &> /dev/null; then
    echo -e "${RED}Error:${NC} curl is not installed. Please install it and try again."
    exit 1
fi

# Fancy download with user feedback
echo -e "${GREEN}Downloading evremixes...${NC}"
if curl -o "${temp_dir}/evremixes" -L "https://git.dannystewart.com/danny/evremixes/raw/branch/main/dist/evremixes" --progress-bar; then
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
