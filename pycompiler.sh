#!/bin/bash

# Identify architecture
ARCH=$(uname -m)

# Compile binary
if [ "$ARCH" == "x86_64" ]; then
    pyinstaller --onefile evremixes.py --clean --distpath=./dist/x86
    chmod +x ./dist/x86/evremixes
elif [ "$ARCH" == "arm64" ]; then
    pyinstaller --onefile evremixes.py --clean --distpath=./dist/arm
    chmod +x ./dist/arm/evremixes
else
    echo -e "${RED}Error:${NC} Unsupported architecture."
    exit 1
fi
