#!/usr/bin/env python3
"""
PPT2PDF — GTK4 batch converter  (GNOME / KDE / CachyOS / XFCE / …)

• Requires: GTK 4.10+, PyGObject ≥ 3.46
• Optional: libadwaita 1.x  (auto-detected; used on GNOME / Flatpak)
• Backend: LibreOffice headless (host or via flatpak-spawn)
"""

import os
import glob
import subprocess
import threading

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, Gio

# ── Optional libadwaita ────────────────────────────────────────────────────────
# Present on GNOME desktops and always inside the Flatpak (GNOME SDK).
# Gracefully skipped on KDE Plasma, CachyOS KDE, XFCE, etc. so the app
# falls back to plain GTK4 widgets and respects whatever system theme is active.
try:
    gi.require_version("Adw", "1")
    from gi.repository import Adw          # noqa: F401
    HAS_ADW = True
except (ValueError, ImportError):
    HAS_ADW = False

# ── Minimal CSS ────────────────────────────────────────────────────────────────
# No colour overrides — colours come entirely from the active system theme
# (Adwaita, Breeze-GTK4, Arc, Mint-Y, …).
CSS = b"""
.ppt-main {
    padding: 20px;
}
.ppt-title {
    font-size: 22px;
    font-weight: bold;
    margin-bottom: 4px;
}
.ppt-subtitle {
    margin-bottom: 18px;
}
.ppt-convert-btn {
    padding: 10px 28px;
    font-weight: bold;
    font-size: 14px;
    border-radius: 99px;
    margin-top: 6px;
    margin-bottom: 12px;
}
.ppt-plain-frame {
    border-radius: 8px;
    margin-bottom: 14px;
}
.ppt-plain-inner {
    padding: 14px 18px;
}
"""


# ── Main window ────────────────────────────────────────────────────────────────

class PPT2PDFWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application) -> None:
        super().__init__(application=app)
        self.set_title("PPT to PDF")
        self.set_default_size(700, 440)

        self._input_dir = ""
        self._output_dir = ""

        self._apply_css()
        self._build_ui()
        self._check_libreoffice()

    # ── CSS ────────────────────────────────────────────────────────────────────

    def _apply_css(self) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # ── Header bar (GTK4 native — works on every DE)
        header = Gtk.HeaderBar()
        pdf_icon = Gtk.Image.new_from_icon_name("application-pdf-symbolic")
        header.pack_start(pdf_icon)
        self.set_titlebar(header)

        # ── Root vertical box
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.add_css_class("ppt-main")
        self.set_child(root)

        # ── Title / subtitle
        title = Gtk.Label(label="Batch PPT → PDF Converter")
        title.add_css_class("ppt-title")
        title.set_halign(Gtk.Align.CENTER)
        root.append(title)

        subtitle = Gtk.Label(
            label="Convert entire folders of PowerPoint presentations to PDF using LibreOffice."
        )
        subtitle.add_css_class("dim-label")
        subtitle.add_css_class("ppt-subtitle")
        subtitle.set_halign(Gtk.Align.CENTER)
        subtitle.set_wrap(True)
        root.append(subtitle)

        # ── Folder selection — adaptive: Adwaita rows OR plain GTK4 grid
        if HAS_ADW:
            self._build_adw_folder_rows(root)
        else:
            self._build_gtk_folder_rows(root)

        # ── Flexible spacer so controls push to the bottom
        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        root.append(spacer)

        # ── Status label
        self._status_lbl = Gtk.Label(label="Ready to convert.")
        self._status_lbl.add_css_class("dim-label")
        self._status_lbl.set_halign(Gtk.Align.CENTER)
        self._status_lbl.set_margin_bottom(6)
        root.append(self._status_lbl)

        # ── Progress bar
        self._progress = Gtk.ProgressBar()
        self._progress.set_show_text(True)
        self._progress.set_text("")
        self._progress.set_margin_bottom(10)
        root.append(self._progress)

        # ── Convert button
        self._convert_btn = Gtk.Button(label="⚡  Convert to PDF")
        self._convert_btn.add_css_class("suggested-action")
        self._convert_btn.add_css_class("ppt-convert-btn")
        self._convert_btn.set_halign(Gtk.Align.CENTER)
        self._convert_btn.connect("clicked", self._on_convert_clicked)
        root.append(self._convert_btn)

    # ── Adwaita folder rows (GNOME / Flatpak) ---------------------------------

    def _build_adw_folder_rows(self, parent: Gtk.Box) -> None:
        group = Adw.PreferencesGroup()
        group.set_margin_bottom(10)
        parent.append(group)

        # Input row
        self._in_row = Adw.ActionRow()
        self._in_row.set_title("Input Folder")
        self._in_row.set_subtitle("Folder containing .ppt / .pptx files")
        in_btn = Gtk.Button(label="Browse…")
        in_btn.add_css_class("flat")
        in_btn.set_valign(Gtk.Align.CENTER)
        in_btn.connect("clicked", self._on_choose_input)
        self._in_row.add_suffix(in_btn)
        self._in_row.set_activatable_widget(in_btn)
        group.add(self._in_row)

        # Output row
        self._out_row = Adw.ActionRow()
        self._out_row.set_title("Output Folder")
        self._out_row.set_subtitle("Leave empty to save PDFs alongside the originals")
        out_btn = Gtk.Button(label="Browse…")
        out_btn.add_css_class("flat")
        out_btn.set_valign(Gtk.Align.CENTER)
        out_btn.connect("clicked", self._on_choose_output)
        self._out_row.add_suffix(out_btn)
        self._out_row.set_activatable_widget(out_btn)
        group.add(self._out_row)

    # ── Plain GTK4 folder rows (KDE / CachyOS KDE / XFCE / …) ----------------

    def _build_gtk_folder_rows(self, parent: Gtk.Box) -> None:
        frame = Gtk.Frame()
        frame.add_css_class("ppt-plain-frame")
        frame.set_margin_bottom(14)
        parent.append(frame)

        grid = Gtk.Grid()
        grid.add_css_class("ppt-plain-inner")
        grid.set_row_spacing(12)
        grid.set_column_spacing(12)
        frame.set_child(grid)

        # Input
        in_lbl = Gtk.Label(label="Input Folder:")
        in_lbl.set_halign(Gtk.Align.START)
        self._in_path_lbl = Gtk.Label(label="(not selected)")
        self._in_path_lbl.set_halign(Gtk.Align.START)
        self._in_path_lbl.set_hexpand(True)
        self._in_path_lbl.add_css_class("dim-label")
        in_btn = Gtk.Button(label="Browse…")
        in_btn.connect("clicked", self._on_choose_input)
        grid.attach(in_lbl,          0, 0, 1, 1)
        grid.attach(self._in_path_lbl, 1, 0, 1, 1)
        grid.attach(in_btn,          2, 0, 1, 1)

        # Output
        out_lbl = Gtk.Label(label="Output Folder:")
        out_lbl.set_halign(Gtk.Align.START)
        self._out_path_lbl = Gtk.Label(label="(same as input)")
        self._out_path_lbl.set_halign(Gtk.Align.START)
        self._out_path_lbl.set_hexpand(True)
        self._out_path_lbl.add_css_class("dim-label")
        out_btn = Gtk.Button(label="Browse…")
        out_btn.connect("clicked", self._on_choose_output)
        grid.attach(out_lbl,           0, 1, 1, 1)
        grid.attach(self._out_path_lbl, 1, 1, 1, 1)
        grid.attach(out_btn,           2, 1, 1, 1)

    # ── LibreOffice ────────────────────────────────────────────────────────────

    def _get_lo_cmd(self) -> list[str]:
        """Return the LibreOffice command, using flatpak-spawn when sandboxed."""
        if os.path.exists("/.flatpak-info"):
            return ["flatpak-spawn", "--host", "libreoffice"]
        return ["libreoffice"]

    def _check_libreoffice(self) -> None:
        try:
            subprocess.run(
                self._get_lo_cmd() + ["--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        except FileNotFoundError:
            self._convert_btn.set_sensitive(False)
            self._status_lbl.set_text("⚠ LibreOffice not found — please install it.")

    # ── Path helper ────────────────────────────────────────────────────────────

    def _shorten(self, path: str) -> str:
        home = os.path.expanduser("~")
        if path.startswith(home):
            path = "~" + path[len(home):]
        return path if len(path) <= 48 else "…" + path[-45:]

    # ── Folder pickers (async, portal-aware — works on X11, Wayland, KDE, …) --

    def _on_choose_input(self, *_) -> None:
        d = Gtk.FileDialog()
        d.set_title("Select Input Folder")
        d.select_folder(self, None, self._on_input_chosen)

    def _on_input_chosen(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            gfile = dialog.select_folder_finish(result)
        except GLib.Error:
            return  # user cancelled
        self._input_dir = gfile.get_path()
        short = self._shorten(self._input_dir)
        if HAS_ADW:
            self._in_row.set_subtitle(short)
        else:
            self._in_path_lbl.set_text(short)
        # Auto-fill output if not yet chosen
        if not self._output_dir:
            self._output_dir = self._input_dir
            if HAS_ADW:
                self._out_row.set_subtitle(short + "  (same as input)")
            else:
                self._out_path_lbl.set_text(short + " (same)")

    def _on_choose_output(self, *_) -> None:
        d = Gtk.FileDialog()
        d.set_title("Select Output Folder")
        d.select_folder(self, None, self._on_output_chosen)

    def _on_output_chosen(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            gfile = dialog.select_folder_finish(result)
        except GLib.Error:
            return
        self._output_dir = gfile.get_path()
        short = self._shorten(self._output_dir)
        if HAS_ADW:
            self._out_row.set_subtitle(short)
        else:
            self._out_path_lbl.set_text(short)

    # ── Alert helper ───────────────────────────────────────────────────────────

    def _alert(self, heading: str, detail: str) -> None:
        dlg = Gtk.AlertDialog()
        dlg.set_message(heading)
        dlg.set_detail(detail)
        dlg.show(self)

    # ── Conversion ─────────────────────────────────────────────────────────────

    def _on_convert_clicked(self, *_) -> None:
        if not self._input_dir:
            self._alert("No Input Folder", "Please select an input folder first.")
            return
        if not os.path.isdir(self._input_dir):
            self._alert("Invalid Folder", "The selected input folder no longer exists.")
            return

        out_dir = self._output_dir or self._input_dir
        if not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir, exist_ok=True)
            except Exception as exc:
                self._alert("Cannot Create Output Folder", str(exc))
                return

        files: list[str] = []
        for ext in ("*.ppt", "*.pptx"):
            files.extend(glob.glob(os.path.join(self._input_dir, ext)))

        if not files:
            self._alert(
                "No Presentations Found",
                "No .ppt or .pptx files were found in the selected folder.",
            )
            return

        # Lock the UI and kick off the background thread
        self._convert_btn.set_sensitive(False)
        self._progress.set_fraction(0.0)
        self._progress.set_text("0 %")
        self._status_lbl.set_text(f"Starting conversion of {len(files)} file(s)…")

        threading.Thread(
            target=self._conversion_worker,
            args=(files, out_dir),
            daemon=True,
        ).start()

    def _conversion_worker(self, files: list[str], out_dir: str) -> None:
        total = len(files)
        ok = fail = 0

        for idx, path in enumerate(files):
            name = os.path.basename(path)
            GLib.idle_add(self._status_lbl.set_text, f"Converting: {name}")

            try:
                result = subprocess.run(
                    self._get_lo_cmd() + [
                        "--headless", "--convert-to", "pdf",
                        path, "--outdir", out_dir,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                )
                if result.returncode == 0:
                    ok += 1
                else:
                    fail += 1
                    print(f"[ppt2pdf] FAILED: {name}\n{result.stderr.strip()}")
            except Exception as exc:
                fail += 1
                print(f"[ppt2pdf] EXCEPTION: {name}: {exc}")

            frac = (idx + 1) / total
            GLib.idle_add(self._progress.set_fraction, frac)
            GLib.idle_add(self._progress.set_text, f"{int(frac * 100)} %  ({idx + 1}/{total})")

        GLib.idle_add(self._on_done, ok, fail)

    def _on_done(self, ok: int, fail: int) -> bool:
        self._convert_btn.set_sensitive(True)
        if fail:
            summary = f"{ok} succeeded, {fail} failed."
            self._status_lbl.set_text(f"⚠  Done with errors — {summary}")
            self._alert("Conversion Finished with Errors", summary)
        else:
            summary = f"All {ok} presentation(s) converted successfully!"
            self._status_lbl.set_text(f"✓  {summary}")
            self._alert("Conversion Complete", summary)
        return GLib.SOURCE_REMOVE


# ── Application entry point ────────────────────────────────────────────────────

def _on_activate(app: Gtk.Application) -> None:
    win = app.get_active_window()
    if not win:
        win = PPT2PDFWindow(app)
    win.present()


def main() -> None:
    if HAS_ADW:
        # Adw.Application initialises the Adwaita style manager so the app
        # honours the GNOME dark-mode preference and colour-scheme settings.
        app = Adw.Application(
            application_id="com.github.hamzaihsan.PPT2PDF",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
    else:
        # Plain Gtk.Application — fully respects whatever theme the DE uses
        # (Breeze-GTK4 on KDE/CachyOS, Arc, Mint-Y, …).
        app = Gtk.Application(
            application_id="com.github.hamzaihsan.PPT2PDF",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

    app.connect("activate", _on_activate)
    app.run(None)


if __name__ == "__main__":
    main()
