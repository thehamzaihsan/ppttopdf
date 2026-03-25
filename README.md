# PPT to PDF Converter

A modern, fast, and robust batch converter that transforms PowerPoint presentations (`.ppt`, `.pptx`) into high-quality, text-based PDF files. 

Powered by **LibreOffice Headless**, this tool guarantees that your output PDFs retain exact text formatting and remain selectable (not flattened image-based exports).

---

## 🚀 Features
- **Batch Processing**: Convert entire folders of presentations with a single click.
- **Native GTK3 GUI**: A modern, sleek, and responsive interface designed to integrate seamlessly on Linux desktops (GNOME, KDE, Cinnamon, etc.).
- **Flatpak Support**: Easily containerize and install the application natively as a Flatpak, keeping your host system clean while dynamically executing LibreOffice processes.
- **Background Processing**: Heavy conversions happen safely in the background, keeping the UI responsive and providing a progress bar.
- **No Lost Formatting**: True text-based PDF conversion powered by the industry-standard LibreOffice rendering engine.

---

## 🛠️ Multiple Interfaces

We provide several flavors to suit your workflow:

1. **GTK3 Modern GUI (`ppt2pdf-gtk.py`)**: The flagship, modern Linux desktop graphical application.
2. **Tkinter GUI (`ppt2pdf-gui.py`)**: A lightweight Python graphical alternative built on standard modules.
3. **Bash CLI (`ppt2pdf`)**: A pure bash tool providing fast, colorful command-line conversions.

---

## 📦 Installation & Setup

### Option 1: Flatpak Installation (Recommended for Linux Desktop)
Installing via Flatpak gives you a native application icon and sandbox security.

*Note: Requires LibreOffice to be installed on your base system, as the Flatpak connects securely to it via `flatpak-spawn`. *

```bash
# Clone or navigate to the directory
cd ppttopdf

# Run our handy installation script
./install_flatpak.sh
```

Once installed, it will appear in your application menu/launcher as **"PPT to PDF"**. You can also run it via:
```bash
flatpak run com.github.hamzaihsan.PPT2PDF
```

---

### Option 2: Python Virtual Environment (For developers or standalone use)
Run the GTK Application natively by provisioning a virtual environment.

```bash
# Clone or navigate to the directory
cd ppttopdf

# Automatically install system deps and setup python environment
./setup_venv.sh

# Activate the virtual environment
source .venv/bin/activate

# Launch the visual GTK3 Application
./ppt2pdf-gtk.py
```

---

### Option 3: Bash CLI (Fast & Simple)
If you just want to run conversions from the terminal, simply run the bash script:

```bash
# Ensure it is executable
chmod +x ppt2pdf

# Provide the folder path containing your PPTs
./ppt2pdf /path/to/my_presentations
```

---

## 🖼️ Icon

This repository also includes a custom designed, SVG scalable icon (`com.github.hamzaihsan.PPT2PDF.svg`) natively packed into the Flatpak for a crisp aesthetic display.

## 🤝 Prerequisites

- **LibreOffice**: Must be installed on your host system as it serves as the underlying conversion engine.
  - Debian/Ubuntu: `sudo apt install libreoffice`

## 📝 License

This project is open source and available for personal or professional use.
