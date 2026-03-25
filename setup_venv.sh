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

echo "Installing required system dependencies (requires sudo)..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-gi gir1.2-gtk-3.0 python3-cairo libcairo2-dev

echo -e "\n${GREEN}System dependencies installed successfully.${NC}"

echo "Creating Python virtual environment (.venv)..."
# We use --system-site-packages because building PyGObject and pycairo from pip can be prone to failing without dev headers,
# and it allows leveraging the OS's native GTK3 python bindings smoothly.
python3 -m venv .venv --system-site-packages

echo "Activating virtual environment and installing pip requirements..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo -e "\n${GREEN}Environment setup complete!${NC}"
echo -e "You can now run the application with:"
echo -e "${YELLOW}  source .venv/bin/activate${NC}"
echo -e "${YELLOW}  ./ppt2pdf-gtk.py${NC}"
echo -e "${BLUE}==========================================${NC}"
