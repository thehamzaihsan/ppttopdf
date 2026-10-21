#!/bin/bash

# Setup script for the PPT to PDF Converter Python Environment

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}  Setting up Python Virtual Environment   ${NC}"
echo -e "${BLUE}==========================================${NC}"

echo "Installing Python virtual-environment support (requires sudo)..."
sudo apt-get update
sudo apt-get install -y python3-venv

echo -e "\n${GREEN}System dependencies installed successfully.${NC}"

echo "Creating Python virtual environment (.venv)..."
python3 -m venv .venv

echo "Activating virtual environment and installing pip requirements..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo -e "\n${GREEN}Environment setup complete!${NC}"
echo -e "You can now run the application with:"
echo "  source .venv/bin/activate"
echo "  python ppt2pdf-gtk.py"
echo -e "${BLUE}==========================================${NC}"
