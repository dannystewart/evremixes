#!/bin/bash

# Identify architecture and OS
ARCH=$(uname -m)
OS=$(uname)

# Compile binary
if [ "$OS" == "Darwin" ]; then
    if [ "$ARCH" == "x86_64" ]; then
        pyinstaller --onefile ../evremixes.py --clean --distpath=../dist/x86
        chmod +x ../dist/x86/evremixes
    elif [ "$ARCH" == "arm64" ]; then
        pyinstaller --onefile ../evremixes.py --clean --distpath=../dist/arm
        chmod +x ../dist/arm/evremixes
    else
        echo "Error: Unsupported architecture."
        exit 1
    fi
elif [ "$OS" == "Linux" ]; then
    pyinstaller --onefile ../evremixes.py --clean --distpath=../dist/linux
    chmod +x ../dist/linux/evremixes
else
    echo "Error: Unsupported operating system."
    exit 1
fi
