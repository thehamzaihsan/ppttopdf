# <img src="com.github.hamzaihsan.PPT2PDF.svg" width="48" height="48" align="absmiddle"> PPT2PDF

PPT2PDF is a desktop and command-line utility for converting PowerPoint
presentations (`.ppt` and `.pptx`) into PDF files with
[LibreOffice](https://www.libreoffice.org/) running in headless mode.

The converter processes the original presentation rather than taking
screenshots, so the generated PDFs keep selectable text and LibreOffice's
document rendering.

## Features

### Desktop application

- **Cross-platform Qt 6 interface** powered by PySide6 for Linux, Windows, and
  macOS.
- **Batch conversion** of every `.ppt` and `.pptx` file in a selected folder.
- **Optional recursive scanning** to include presentations in subfolders.
- **Drag and drop** of a folder or presentation onto the application window.
- **Separate output folder** selection, with the input folder used by default.
- **Live file status** for pending, converting, completed, failed, and
  cancelled files.
- **Responsive UI** while conversions run in the background.
- **Parallel conversion** with up to four LibreOffice workers for faster
  batches.
- **Cancellation** for stopping queued work while allowing active conversions
  to finish safely.
- **Progress reporting** and a one-click action to open the output folder.
- **Persistent folders** remembered between launches with `QSettings`.
- Keyboard shortcuts:
  - `Ctrl+O` — choose the input folder
  - `Ctrl+Shift+O` — choose the output folder
  - `Ctrl+Enter` — start conversion
  - `Esc` — cancel an active conversion

### Command-line utility

The `ppt2pdf` shell script provides a lightweight alternative for converting
the presentations in a single directory. It handles filenames with spaces and
prints success and failure counts when it finishes.

## Recent updates

- Reworked the desktop interface from GTK4/PyGObject to **PySide6 and Qt 6**
  for a consistent cross-platform experience.
- Added Windows and macOS LibreOffice discovery alongside Linux support.
- Added isolated LibreOffice profiles for concurrent conversions, preventing
  parallel workers from sharing the same user profile.
- Added recursive folder scanning, drag-and-drop input, persistent folder
  choices, keyboard shortcuts, cancellation, and per-file progress states.
- Updated the Python dependency to `PySide6>=6.8.0`.
- Kept local Flatpak build metadata and the application icon/desktop entry for
  Linux packaging.

## Installation

### Prerequisites

Install the following before running PPT2PDF:

| Requirement | Purpose |
|---|---|
| LibreOffice | Conversion backend |
| Python 3.10+ | Runs the desktop application |
| PySide6 6.8+ | Qt 6 Python bindings |

LibreOffice must be available on `PATH` as `libreoffice` or `soffice` on Linux.
On Windows and macOS, PPT2PDF also checks the standard LibreOffice install
locations.

Install LibreOffice using your platform's package manager or from the
[official download page](https://www.libreoffice.org/download/download-libreoffice/).

### Desktop application with a virtual environment

```bash
git clone https://github.com/thehamzaihsan/ppttopdf.git
cd ppttopdf

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python ppt2pdf-gtk.py
```

The included `setup_venv.sh` script can also automate environment setup on
Debian/Ubuntu-based systems.

### Flatpak packaging

The repository includes a Flatpak manifest and an installation helper for
Linux:

```bash
./install_flatpak.sh
flatpak run com.github.hamzaihsan.PPT2PDF
```

The helper installs the GNOME 47 SDK and platform, builds the application, and
installs it for the current user. LibreOffice is still required on the host;
the packaged application is designed to invoke the host converter through
`flatpak-spawn`.

## Usage

### Desktop application

1. Launch `python ppt2pdf-gtk.py`.
2. Choose an input folder, or drag a folder onto the window.
3. Optionally choose a different output folder.
4. Enable **Include subfolders** if needed.
5. Click **Convert to PDF**.

LibreOffice controls the final output behavior when a PDF with the same name
already exists in the output folder.

### Command line

```bash
chmod +x ppt2pdf
./ppt2pdf /path/to/presentations
```

The CLI scans only the specified directory (not subfolders) and writes the PDF
files next to their source presentations.

## Project files

| File | Description |
|---|---|
| `ppt2pdf-gtk.py` | PySide6 desktop application |
| `ppt2pdf` | Bash command-line converter |
| `requirements.txt` | Python dependencies |
| `com.github.hamzaihsan.PPT2PDF.yml` | Flatpak build manifest |
| `install_flatpak.sh` | Local Flatpak build/install helper |
| `setup_venv.sh` | Debian/Ubuntu virtual-environment setup helper |

## License

Open source — free for personal and professional use.
