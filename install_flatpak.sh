#!/bin/bash

# Script to build and install the PPT2PDF Flatpak application locally

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}  Building and Installing PPT2PDF Flatpak ${NC}"
echo -e "${BLUE}==========================================${NC}"

# Check if flatpak and flatpak-builder are installed
if ! command -v flatpak-builder &> /dev/null; then
    echo "flatpak-builder is not installed. Installing it now (requires sudo)..."
    sudo apt-get update && sudo apt-get install -y flatpak-builder
fi

echo "Ensuring flathub repository is added..."
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

echo "Installing required GNOME SDK and Platform (version 45)..."
flatpak install --user --noninteractive flathub org.gnome.Platform//45 org.gnome.Sdk//45

echo "Building and installing the Flatpak application..."
flatpak-builder --user --install --force-clean build-dir com.github.hamzaihsan.PPT2PDF.yml

echo -e "\n${GREEN}Successfully built and installed the Flatpak!${NC}"
echo -e "You should now be able to find 'PPT to PDF' in your application menu."
echo -e "Alternatively, you can run it from the terminal using:"
echo -e "  flatpak run com.github.hamzaihsan.PPT2PDF"
echo -e "${BLUE}==========================================${NC}"
