#!/bin/bash

# Identify architecture and OS
ARCH=$(uname -m)
OS=$(uname)

# Compile binary
if [ "$OS" == "Darwin" ]; then
    if [ "$ARCH" == "x86_64" ]; then
        poetry run pyinstaller evremixes.x86.spec --clean --distpath=dist/x86
        chmod +x dist/x86/evremixes
    elif [ "$ARCH" == "arm64" ]; then
        poetry run pyinstaller evremixes.arm.spec --clean --distpath=dist/arm
        chmod +x dist/arm/evremixes
    else
        echo "Error: Unsupported architecture."
        exit 1
    fi
elif [ "$OS" == "Linux" ]; then
    poetry run pyinstaller evremixes.linux.spec --clean --distpath=dist/linux
    chmod +x dist/linux/evremixes
else
    echo "Error: Unsupported operating system."
    exit 1
fi
