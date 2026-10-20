# <img src="com.github.hamzaihsan.PPT2PDF.svg" width="48" height="48" align="absmiddle"> PPT to PDF Converter

A modern, fast batch converter that transforms PowerPoint presentations (`.ppt`, `.pptx`) into high-quality, text-based PDF files.

Powered by **LibreOffice Headless**, output PDFs retain exact text formatting and remain fully selectable — not flattened image exports.

---

## 🚀 Features

- **Batch Processing** — Convert entire folders with a single click.
- **GTK4 GUI** — A clean, responsive interface built on GTK 4 that integrates natively on any Linux desktop.
- **Universal Desktop Support** — Works on GNOME, KDE Plasma, CachyOS (KDE & GNOME), XFCE, Cinnamon, and more.
  - On GNOME or inside Flatpak: enhanced with **libadwaita** (Adwaita look, dark mode, colour scheme support).
  - On KDE / CachyOS KDE / others: falls back to plain GTK4 and **respects your system theme** (Breeze-GTK4, Arc, etc.) — no alien colours.
- **Portal-aware file picker** — Uses `Gtk.FileDialog` which opens the native file picker (KDE's or GNOME's) automatically depending on your DE, even on Wayland.
- **Flatpak Support** — Containerised install keeps your host clean; connects to LibreOffice on the host via `flatpak-spawn`.
- **Background Processing** — Conversions run in a background thread; UI stays responsive with a live progress bar.
- **No Lost Formatting** — True text-based PDF output via the LibreOffice rendering engine.

---

## 🖥️ Interfaces

| Interface | File | Description |
|---|---|---|
| **GTK4 GUI** | `ppt2pdf-gtk.py` | Flagship desktop GUI — works on all DEs |
| **Bash CLI** | `ppt2pdf` | Lightweight terminal converter |

---

## 📦 Installation & Setup

### Option 1: Flatpak (Recommended)

Gives you a native application icon, Flatpak sandboxing, and a consistent look regardless of distro.

> **Note:** LibreOffice must be installed on your host system — the Flatpak calls it via `flatpak-spawn`.

```bash
# Clone the repo (or navigate into the directory)
cd ppttopdf

# Build and install locally (auto-detects your package manager)
./install_flatpak.sh
```

Once installed it will appear in your app launcher as **"PPT to PDF"**. You can also run it via:

```bash
flatpak run com.github.hamzaihsan.PPT2PDF
```

---

### Option 2: Python venv (Developers / Standalone)

```bash
cd ppttopdf

# Set up the virtual environment (installs PyGObject etc.)
./setup_venv.sh

# Activate it
source .venv/bin/activate

# Launch the GTK4 app
python3 ppt2pdf-gtk.py
```

> **libadwaita is optional.** If it's not installed on your system the app will start normally using plain GTK4 and your system theme.

---

### Option 3: Bash CLI (Fast & Simple)

```bash
chmod +x ppt2pdf
./ppt2pdf /path/to/your/presentations
```

---

## 🔧 Prerequisites

| Requirement | Notes |
|---|---|
| **LibreOffice** | The conversion backend. Install via your package manager. |
| **GTK 4.10+** | Included in any modern GNOME/KDE desktop. |
| **PyGObject ≥ 3.46** | Python GTK bindings — see `requirements.txt`. |
| **libadwaita 1.x** | *Optional.* Enhances UI on GNOME; gracefully skipped on KDE/other DEs. |

**Installing LibreOffice:**

| Distro | Command |
|---|---|
| Arch / CachyOS | `sudo pacman -S libreoffice-fresh` |
| Fedora | `sudo dnf install libreoffice` |
| Ubuntu / Debian | `sudo apt install libreoffice` |
| openSUSE | `sudo zypper install libreoffice` |

---

## 🖼️ Icon

A custom scalable SVG icon (`com.github.hamzaihsan.PPT2PDF.svg`) is bundled for a crisp display in app launchers.

---

## 📝 License

Open source — free for personal and professional use.
