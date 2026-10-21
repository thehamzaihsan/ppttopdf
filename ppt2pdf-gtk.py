#!/usr/bin/env python3
"""
PPT2PDF — Cross-platform batch converter
Toolkit : PySide6 (Qt 6) — native look on Linux/KDE/GNOME/Windows/macOS
Backend : LibreOffice headless
"""

from __future__ import annotations

import concurrent.futures
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from PySide6.QtCore import (
    QSettings, QSize, Qt, QThread, QUrl, Signal
)
from PySide6.QtGui import (
    QAction, QColor, QDesktopServices, QDragEnterEvent, QDropEvent,
    QFont, QIcon, QKeySequence, QPalette, QPixmap, QShortcut
)
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QFrame,
    QGroupBox, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox,
    QProgressBar, QPushButton, QSizePolicy,
    QToolBar, QVBoxLayout, QWidget,
)


# ── LibreOffice discovery ──────────────────────────────────────────────────────

def find_libreoffice() -> list[str] | None:
    if os.path.exists("/.flatpak-info"):
        return ["flatpak-spawn", "--host", "libreoffice"]
    system = platform.system()
    if system == "Windows":
        for c in (
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ):
            if os.path.isfile(c):
                return [c]
        return None
    if system == "Darwin":
        mac = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
        return [mac] if os.path.isfile(mac) else None
    lo = shutil.which("libreoffice") or shutil.which("soffice")
    return [lo] if lo else None


LO_CMD = find_libreoffice()

# ── Persistent settings ────────────────────────────────────────────────────────

APP_ORG  = "hamzaihsan"
APP_NAME = "PPT2PDF"

def load_setting(key: str, default: str = "") -> str:
    return QSettings(APP_ORG, APP_NAME).value(key, default)

def save_setting(key: str, value: str) -> None:
    QSettings(APP_ORG, APP_NAME).setValue(key, value)

# ── File item states ───────────────────────────────────────────────────────────

STATE_PENDING    = ("⏳", "Pending",      None)
STATE_CONVERTING = ("⚙",  "Converting…",  "#E8A000")
STATE_DONE       = ("✓",  "Done",         "#27AE60")
STATE_FAILED     = ("✗",  "Failed",       "#E74C3C")
STATE_CANCELLED  = ("—",  "Cancelled",    None)

# ── Worker signal relay ────────────────────────────────────────────────────────

class WorkerSignals(QThread):
    file_started  = Signal(str)
    file_finished = Signal(str, bool)
    all_done      = Signal(int, int)
    progress      = Signal(int, int)


# ── Separator line helper ──────────────────────────────────────────────────────

def _hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    return line


# ── Main window ────────────────────────────────────────────────────────────────

class PPT2PDFWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PPT to PDF Converter")
        self.setMinimumSize(740, 580)
        self.resize(820, 640)
        self.setAcceptDrops(True)

        self._input_dir    = load_setting("input_dir")
        self._output_dir   = load_setting("output_dir")
        self._cancel_event = threading.Event()
        self._signals      = WorkerSignals()

        # Resolve the SVG icon path once, relative to this file
        here = os.path.dirname(os.path.realpath(__file__))
        self._svg_path = os.path.join(here, "com.github.hamzaihsan.PPT2PDF.svg")

        self._build_ui()
        self._connect_signals()
        self._setup_shortcuts()
        self._restore_paths()
        self._check_libreoffice()

    # ── App icon helper ────────────────────────────────────────────────────────

    def _make_icon(self, size: int) -> QIcon:
        if os.path.isfile(self._svg_path):
            return QIcon(self._svg_path)
        return QIcon()

    def _make_pixmap(self, size: int) -> QPixmap:
        icon = self._make_icon(size)
        pm = icon.pixmap(QSize(size, size))
        return pm

    # ── Accent-colour button stylesheet (uses the system palette) ──────────────

    def _accent_btn_style(self) -> str:
        pal     = QApplication.palette()
        bg      = pal.color(QPalette.ColorRole.Highlight)
        fg      = pal.color(QPalette.ColorRole.HighlightedText)
        bg_h    = bg.lighter(115)
        bg_p    = bg.darker(115)
        bg_d    = QColor(bg)
        bg_d.setAlpha(80)
        return f"""
            QPushButton {{
                background-color : {bg.name()};
                color            : {fg.name()};
                border           : none;
                border-radius    : 8px;
                padding          : 11px 32px;
                font-size        : 14px;
                font-weight      : bold;
            }}
            QPushButton:hover {{
                background-color : {bg_h.name()};
            }}
            QPushButton:pressed {{
                background-color : {bg_p.name()};
            }}
            QPushButton:disabled {{
                background-color : rgba(128,128,128,60);
                color            : rgba(128,128,128,140);
            }}
        """

    # ── Build UI ───────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:

        # ── Toolbar ────────────────────────────────────────────────────────────
        tb = QToolBar()
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        tb.setFloatable(False)
        self.addToolBar(tb)

        # Left: 22 px app logo in toolbar
        pm22 = self._make_pixmap(22)
        if not pm22.isNull():
            logo_tb = QLabel()
            logo_tb.setPixmap(pm22)
            logo_tb.setContentsMargins(6, 0, 4, 0)
            tb.addWidget(logo_tb)

        app_tb_lbl = QLabel("<b>PPT to PDF</b>")
        app_tb_lbl.setContentsMargins(0, 0, 0, 0)
        tb.addWidget(app_tb_lbl)

        stretch = QWidget()
        stretch.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(stretch)

        self._cancel_action = QAction("✕  Cancel", self)
        self._cancel_action.setVisible(False)
        self._cancel_action.triggered.connect(self._on_cancel)
        tb.addAction(self._cancel_action)

        self._open_out_action = QAction("📂  Open Output", self)
        self._open_out_action.setVisible(False)
        self._open_out_action.triggered.connect(self._on_open_output)
        tb.addAction(self._open_out_action)

        # ── Central widget ─────────────────────────────────────────────────────
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(14)
        root.setContentsMargins(20, 16, 20, 16)

        # ── App header banner (logo + title + subtitle) ────────────────────────
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.Shape.StyledPanel)
        header_frame.setFrameShadow(QFrame.Shadow.Raised)
        header_lay = QHBoxLayout(header_frame)
        header_lay.setContentsMargins(16, 14, 16, 14)
        header_lay.setSpacing(16)

        pm56 = self._make_pixmap(56)
        if not pm56.isNull():
            logo_lbl = QLabel()
            logo_lbl.setPixmap(pm56)
            logo_lbl.setFixedSize(56, 56)
            header_lay.addWidget(logo_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        title_lbl = QLabel("PPT to PDF Converter")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_lbl.setFont(title_font)
        sub_lbl = QLabel("Batch-convert PowerPoint presentations to PDF using LibreOffice.\n"
                          "Drag a folder onto the window, or use Browse below.")
        sub_lbl.setWordWrap(True)
        pal = QApplication.palette()
        dim = pal.color(QPalette.ColorRole.WindowText)
        dim.setAlpha(160)
        sub_lbl.setStyleSheet(f"color: rgba({dim.red()},{dim.green()},{dim.blue()},160);")
        title_col.addWidget(title_lbl)
        title_col.addWidget(sub_lbl)
        header_lay.addLayout(title_col, 1)

        root.addWidget(header_frame)

        # ── Folder group ───────────────────────────────────────────────────────
        folder_grp = QGroupBox("Folders")
        fg = QVBoxLayout(folder_grp)
        fg.setSpacing(10)
        fg.setContentsMargins(14, 12, 14, 12)

        # Input row
        in_row = QHBoxLayout()
        in_row.setSpacing(8)
        in_row.addWidget(QLabel("Input:"))
        self._in_lbl = QLabel("No folder selected")
        self._in_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._in_lbl.setStyleSheet("font-style: italic;")
        in_row.addWidget(self._in_lbl, 1)
        in_browse = QPushButton("Browse…")
        in_browse.setFixedWidth(90)
        in_browse.clicked.connect(self._on_browse_input)
        in_row.addWidget(in_browse)
        fg.addLayout(in_row)

        fg.addWidget(_hline())

        # Output row
        out_row = QHBoxLayout()
        out_row.setSpacing(8)
        out_row.addWidget(QLabel("Output:"))
        self._out_lbl = QLabel("Same as input folder")
        self._out_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._out_lbl.setStyleSheet("font-style: italic;")
        out_row.addWidget(self._out_lbl, 1)
        out_browse = QPushButton("Browse…")
        out_browse.setFixedWidth(90)
        out_browse.clicked.connect(self._on_browse_output)
        out_row.addWidget(out_browse)
        fg.addLayout(out_row)

        root.addWidget(folder_grp)

        # ── Options row ────────────────────────────────────────────────────────
        opts = QHBoxLayout()
        self._recursive_cb = QCheckBox("Include subfolders")
        self._recursive_cb.stateChanged.connect(self._refresh_file_list)
        opts.addWidget(self._recursive_cb)
        opts.addStretch()
        self._file_count_lbl = QLabel("")
        opts.addWidget(self._file_count_lbl)
        root.addLayout(opts)

        # ── File list ──────────────────────────────────────────────────────────
        list_grp = QGroupBox("Files to Convert")
        lg = QVBoxLayout(list_grp)
        lg.setContentsMargins(10, 10, 10, 10)
        self._file_list = QListWidget()
        self._file_list.setAlternatingRowColors(True)
        self._file_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self._file_list.setSpacing(2)
        self._file_list.setUniformItemSizes(True)
        lg.addWidget(self._file_list)
        root.addWidget(list_grp, 1)  # stretch — list fills remaining space

        # ── Progress bar (hidden until conversion starts) ──────────────────────
        self._progress = QProgressBar()
        self._progress.setTextVisible(True)
        self._progress.setFixedHeight(18)
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        # ── Status label ───────────────────────────────────────────────────────
        self._status_lbl = QLabel("Ready. Select a folder or drag one onto the window.")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setStyleSheet(
            f"color: rgba({dim.red()},{dim.green()},{dim.blue()},160); font-size: 12px;"
        )
        root.addWidget(self._status_lbl)

        # ── Convert button ─────────────────────────────────────────────────────
        self._convert_btn = QPushButton("⚡  Convert to PDF")
        self._convert_btn.setFixedHeight(46)
        self._convert_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._convert_btn.setStyleSheet(self._accent_btn_style())
        self._convert_btn.clicked.connect(self._on_convert)
        root.addWidget(self._convert_btn)

        # window icon (taskbar / dock)
        app_icon = self._make_icon(64)
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)

    # ── Signals, shortcuts, restore ────────────────────────────────────────────

    def _connect_signals(self) -> None:
        self._signals.file_started.connect(self._on_file_started)
        self._signals.file_finished.connect(self._on_file_finished)
        self._signals.all_done.connect(self._on_all_done)
        self._signals.progress.connect(self._on_progress)

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+O"),       self).activated.connect(self._on_browse_input)
        QShortcut(QKeySequence("Ctrl+Shift+O"), self).activated.connect(self._on_browse_output)
        QShortcut(QKeySequence("Ctrl+Return"),  self).activated.connect(self._on_convert)
        QShortcut(QKeySequence("Escape"),       self).activated.connect(self._on_cancel)

    def _restore_paths(self) -> None:
        if self._input_dir and os.path.isdir(self._input_dir):
            self._in_lbl.setText(self._shorten(self._input_dir))
            self._in_lbl.setStyleSheet("")
            self._refresh_file_list()
        if self._output_dir and os.path.isdir(self._output_dir):
            self._out_lbl.setText(self._shorten(self._output_dir))
            self._out_lbl.setStyleSheet("")

    # ── LibreOffice check ──────────────────────────────────────────────────────

    def _check_libreoffice(self) -> None:
        if not LO_CMD:
            self._convert_btn.setEnabled(False)
            self._status_lbl.setText("⚠ LibreOffice not found — please install it.")
            QMessageBox.critical(
                self, "LibreOffice Not Found",
                "LibreOffice was not found on this system.\n\n"
                "Install it:\n"
                "  • Arch / CachyOS: sudo pacman -S libreoffice-fresh\n"
                "  • Fedora:         sudo dnf install libreoffice\n"
                "  • Ubuntu:         sudo apt install libreoffice\n"
                "  • Windows/macOS:  https://libreoffice.org/download",
            )

    # ── Path helper ────────────────────────────────────────────────────────────

    def _shorten(self, path: str) -> str:
        home = str(Path.home())
        if path.startswith(home):
            path = "~" + path[len(home):]
        return path if len(path) <= 60 else "…" + path[-57:]

    # ── Drag & Drop ────────────────────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                self._set_input_dir(path)
                return
            parent = os.path.dirname(path)
            if os.path.isdir(parent):
                self._set_input_dir(parent)
                return

    # ── Folder pickers ─────────────────────────────────────────────────────────

    def _on_browse_input(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Select Input Folder", self._input_dir or str(Path.home())
        )
        if path:
            self._set_input_dir(path)

    def _on_browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Select Output Folder",
            self._output_dir or self._input_dir or str(Path.home())
        )
        if path:
            self._output_dir = path
            self._out_lbl.setText(self._shorten(path))
            self._out_lbl.setStyleSheet("")
            save_setting("output_dir", path)

    def _set_input_dir(self, path: str) -> None:
        self._input_dir = path
        self._in_lbl.setText(self._shorten(path))
        self._in_lbl.setStyleSheet("")
        save_setting("input_dir", path)
        if not self._output_dir:
            self._out_lbl.setText(self._shorten(path) + "  (same as input)")
            self._out_lbl.setStyleSheet("font-style: italic;")
        self._refresh_file_list()

    # ── File list ──────────────────────────────────────────────────────────────

    def _collect_files(self) -> list[str]:
        if not self._input_dir or not os.path.isdir(self._input_dir):
            return []
        pattern = "**/*" if self._recursive_cb.isChecked() else "*"
        files: list[str] = []
        for ext in ("ppt", "pptx"):
            for p in Path(self._input_dir).glob(f"{pattern}.{ext}"):
                files.append(str(p))
            for p in Path(self._input_dir).glob(f"{pattern}.{ext.upper()}"):
                files.append(str(p))
        seen: set[str] = set()
        result: list[str] = []
        for f in sorted(files):
            k = f.lower()
            if k not in seen:
                seen.add(k)
                result.append(f)
        return result

    def _refresh_file_list(self) -> None:
        self._file_list.clear()
        files = self._collect_files()
        for path in files:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, path)
            self._set_item_state(item, STATE_PENDING)
            self._file_list.addItem(item)
        n = len(files)
        self._file_count_lbl.setText(
            f"{n} file{'s' if n != 1 else ''} found" if n else "No .ppt/.pptx files found"
        )
        self._open_out_action.setVisible(False)

    def _set_item_state(
        self, item: QListWidgetItem, state: tuple
    ) -> None:
        icon_ch, label, color = state
        path = item.data(Qt.ItemDataRole.UserRole) or ""
        name = os.path.basename(path) if path else item.text().split("  ")[0]
        item.setText(f"  {icon_ch}  {name}    {label}")
        if color:
            item.setForeground(QColor(color))
        else:
            item.setForeground(QApplication.palette().color(QPalette.ColorRole.Text))

    def _find_item(self, filename: str) -> QListWidgetItem | None:
        for i in range(self._file_list.count()):
            item = self._file_list.item(i)
            path = item.data(Qt.ItemDataRole.UserRole) or ""
            if os.path.basename(path) == filename:
                return item
        return None

    # ── Conversion ─────────────────────────────────────────────────────────────

    def _on_convert(self) -> None:
        if not LO_CMD:
            return
        if not self._input_dir:
            QMessageBox.warning(self, "No Folder", "Please select an input folder first.")
            return
        files = self._collect_files()
        if not files:
            QMessageBox.information(
                self, "Nothing to Convert",
                "No .ppt or .pptx files found in the selected folder."
            )
            return
        out_dir = self._output_dir or self._input_dir
        os.makedirs(out_dir, exist_ok=True)

        self._refresh_file_list()
        self._cancel_event.clear()
        self._convert_btn.setEnabled(False)
        self._cancel_action.setVisible(True)
        self._open_out_action.setVisible(False)
        self._progress.setVisible(True)
        self._progress.setRange(0, len(files))
        self._progress.setValue(0)
        self._progress.setFormat(f"0 / {len(files)}")
        self._status_lbl.setText(f"Converting {len(files)} file(s)…")

        threading.Thread(
            target=self._worker, args=(files, out_dir), daemon=True
        ).start()

    def _worker(self, files: list[str], out_dir: str) -> None:
        total   = len(files)
        ok = fail = 0
        workers = min(4, os.cpu_count() or 2)

        def convert_one(path: str) -> tuple[str, bool]:
            name = os.path.basename(path)
            if self._cancel_event.is_set():
                return name, False
            self._signals.file_started.emit(name)
            profile = tempfile.mkdtemp(prefix="lo_ppt2pdf_")
            try:
                lo_env = (
                    f"file:///{profile}"
                    if platform.system() == "Windows"
                    else f"file://{profile}"
                )
                result = subprocess.run(
                    LO_CMD + [
                        "--headless",
                        f"-env:UserInstallation={lo_env}",
                        "--convert-to", "pdf",
                        path,
                        "--outdir", out_dir,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                )
                ok_ = result.returncode == 0
                if not ok_:
                    print(f"[ppt2pdf] FAIL: {name}\n{result.stderr.strip()}", file=sys.stderr)
                return name, ok_
            except Exception as exc:
                print(f"[ppt2pdf] ERROR: {name}: {exc}", file=sys.stderr)
                return name, False
            finally:
                shutil.rmtree(profile, ignore_errors=True)

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(convert_one, f): f for f in files}
            done = 0
            for fut in concurrent.futures.as_completed(futs):
                name, success = fut.result()
                if success:
                    ok += 1
                else:
                    fail += 1
                done += 1
                self._signals.file_finished.emit(name, success)
                self._signals.progress.emit(done, total)

        self._signals.all_done.emit(ok, fail)

    # ── Conversion signal handlers ─────────────────────────────────────────────

    def _on_file_started(self, name: str) -> None:
        item = self._find_item(name)
        if item:
            self._set_item_state(item, STATE_CONVERTING)
            self._file_list.scrollToItem(item)
        self._status_lbl.setText(f"Converting: {name}")

    def _on_file_finished(self, name: str, success: bool) -> None:
        item = self._find_item(name)
        if item:
            if self._cancel_event.is_set() and not success:
                self._set_item_state(item, STATE_CANCELLED)
            else:
                self._set_item_state(item, STATE_DONE if success else STATE_FAILED)

    def _on_progress(self, done: int, total: int) -> None:
        self._progress.setValue(done)
        self._progress.setFormat(f"{done} / {total}")

    def _on_all_done(self, ok: int, fail: int) -> None:
        self._convert_btn.setEnabled(True)
        self._cancel_action.setVisible(False)
        self._open_out_action.setVisible(True)
        self._progress.setVisible(False)

        # Mark any items still pending/converting as cancelled
        for i in range(self._file_list.count()):
            item = self._file_list.item(i)
            text = item.text()
            if STATE_PENDING[0] in text or STATE_CONVERTING[0] in text:
                self._set_item_state(item, STATE_CANCELLED)

        if self._cancel_event.is_set():
            self._status_lbl.setText(f"Cancelled. {ok} succeeded, {fail} failed.")
            return

        if fail:
            summary = f"{ok} succeeded, {fail} failed."
            self._status_lbl.setText(f"⚠  Done with errors — {summary}")
            QMessageBox.warning(self, "Finished with Errors", summary)
        else:
            summary = f"All {ok} file(s) converted successfully!"
            self._status_lbl.setText(f"✓  {summary}")
            # No blocking modal on success — status bar + toolbar button is enough

    # ── Cancel / Open output ───────────────────────────────────────────────────

    def _on_cancel(self) -> None:
        self._cancel_event.set()
        self._status_lbl.setText("Cancelling… waiting for current file(s) to finish.")

    def _on_open_output(self) -> None:
        path = self._output_dir or self._input_dir
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_ORG)
    app.setApplicationDisplayName("PPT to PDF Converter")

    win = PPT2PDFWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
