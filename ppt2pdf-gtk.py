#!/usr/bin/env python3

import os
import glob
import subprocess
import threading
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk

CSS = """
/* Custom CSS for a clean, modern aesthetic */
window {
    background-color: @theme_bg_color;
}
.main-container {
    padding: 30px;
}
.heading {
    font-size: 24px;
    font-weight: bold;
    color: @theme_fg_color;
}
.subheading {
    font-size: 14px;
    color: alpha(@theme_fg_color, 0.7);
    margin-bottom: 20px;
}
.action-button {
    padding: 10px 15px;
    font-weight: bold;
    border-radius: 8px;
}
.folder-box {
    padding: 15px;
    border-radius: 8px;
    border: 1px solid alpha(@theme_fg_color, 0.15);
    background-color: alpha(@theme_fg_color, 0.05);
}
.progress-bar {
    min-height: 12px;
    border-radius: 6px;
    margin-top: 10px;
}
.status-label {
    font-size: 13px;
    color: alpha(@theme_fg_color, 0.6);
    margin-top: 10px;
}
"""

class PPT2PDFWindow(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_title("PPT to PDF Converter")
        # Larger default size for a spacious look
        self.set_default_size(680, 400)
        self.set_position(Gtk.WindowPosition.CENTER)

        # Apply custom CSS
        self.apply_css()

        # Try to enforce dark theme preference for a sleek look (if user wants)
        settings = Gtk.Settings.get_default()
        if settings:
            settings.set_property("gtk-application-prefer-dark-theme", True)

        self.setup_headerbar()

        self.input_dir = ""
        self.output_dir = ""

        # Main Layout Box
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        vbox.get_style_context().add_class("main-container")
        self.add(vbox)

        # Header Titles
        title_label = Gtk.Label(label="Batch Converter")
        title_label.set_halign(Gtk.Align.CENTER)
        title_label.get_style_context().add_class("heading")
        vbox.pack_start(title_label, False, False, 5)

        sub_label = Gtk.Label(label="Turn your robust PowerPoint presentations into pristine PDFs effortlessly.")
        sub_label.set_halign(Gtk.Align.CENTER)
        sub_label.set_line_wrap(True)
        sub_label.get_style_context().add_class("subheading")
        vbox.pack_start(sub_label, False, False, 5)

        # Content Box with a modern card-like appearance
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content_box.get_style_context().add_class("folder-box")
        content_box.set_margin_top(15)
        content_box.set_margin_bottom(20)
        vbox.pack_start(content_box, False, False, 0)

        # Input Row
        in_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        
        in_icon = Gtk.Image.new_from_icon_name("folder-open-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        in_icon.set_margin_start(10)
        in_box.pack_start(in_icon, False, False, 0)
        
        in_lbl = Gtk.Label(label="Input Folder (PPT/PPTX):")
        in_lbl.set_halign(Gtk.Align.START)
        in_box.pack_start(in_lbl, False, False, 0)

        self.in_btn = Gtk.Button(label="Select Folder")
        self.in_btn.connect("clicked", self.on_choose_input)
        self.in_btn.set_hexpand(True)
        self.in_btn.set_halign(Gtk.Align.END)
        self.in_btn.get_style_context().add_class("action-button")
        in_box.pack_start(self.in_btn, True, True, 0)

        content_box.pack_start(in_box, False, False, 0)

        # Output Row
        out_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        
        out_icon = Gtk.Image.new_from_icon_name("document-save-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        out_icon.set_margin_start(10)
        out_box.pack_start(out_icon, False, False, 0)

        out_lbl = Gtk.Label(label="Output Folder (Optional):")
        out_lbl.set_halign(Gtk.Align.START)
        out_box.pack_start(out_lbl, False, False, 0)

        self.out_btn = Gtk.Button(label="Default (Same as Input)")
        self.out_btn.connect("clicked", self.on_choose_output)
        self.out_btn.set_hexpand(True)
        self.out_btn.set_halign(Gtk.Align.END)
        self.out_btn.get_style_context().add_class("action-button")
        out_box.pack_start(self.out_btn, True, True, 0)

        content_box.pack_start(out_box, False, False, 0)

        # Bottom Area
        bottom_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.pack_end(bottom_box, False, False, 0)

        # Convert Button (BIG)
        self.convert_btn = Gtk.Button()
        # Create a box for the button content (Icon + Text)
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_box.set_halign(Gtk.Align.CENTER)
        
        btn_icon = Gtk.Image.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.BUTTON)
        btn_box.pack_start(btn_icon, False, False, 0)
        
        btn_lbl = Gtk.Label()
        btn_lbl.set_markup("<b>Convert to PDF</b>")
        btn_box.pack_start(btn_lbl, False, False, 0)
        
        self.convert_btn.add(btn_box)
        
        self.convert_btn.connect("clicked", self.on_convert_clicked)
        self.convert_btn.get_style_context().add_class("suggested-action")
        self.convert_btn.get_style_context().add_class("action-button")
        self.convert_btn.set_size_request(-1, 50)
        bottom_box.pack_end(self.convert_btn, False, False, 0)

        # Progress and Status
        self.status_label = Gtk.Label(label="Ready to convert.")
        self.status_label.set_halign(Gtk.Align.CENTER)
        self.status_label.get_style_context().add_class("status-label")
        bottom_box.pack_start(self.status_label, False, False, 0)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.get_style_context().add_class("progress-bar")
        bottom_box.pack_start(self.progress_bar, False, False, 0)

        if not self.check_libreoffice():
            self.show_error_dialog("LibreOffice not found! It is required to run the conversion.")
            self.convert_btn.set_sensitive(False)
            self.status_label.set_text("Error: LibreOffice missing.")

    def apply_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS.encode())
        screen = Gdk.Screen.get_default()
        context = Gtk.StyleContext()
        context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def setup_headerbar(self):
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("PPT2PDF")
        header.set_subtitle("Converter Tool")
        
        # Add a nice app icon symbol to header bar
        icon = Gtk.Image.new_from_icon_name("application-pdf-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        header.pack_start(icon)

        self.set_titlebar(header)

    def get_libreoffice_command(self):
        in_flatpak = os.path.exists("/.flatpak-info")
        if in_flatpak:
            return ["flatpak-spawn", "--host", "libreoffice"]
        return ["libreoffice"]

    def check_libreoffice(self):
        try:
            cmd = self.get_libreoffice_command() + ["--version"]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except FileNotFoundError:
            return False

    def shorten_path(self, path):
        # Shorten path for display
        home = os.path.expanduser("~")
        if path.startswith(home):
            return "~" + path[len(home):]
        if len(path) > 40:
            return "..." + path[-37:]
        return path

    def show_error_dialog(self, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Error"
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def show_info_dialog(self, title, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def on_choose_input(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Please choose an input folder",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            "Select", Gtk.ResponseType.OK
        )
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.input_dir = dialog.get_filename()
            self.in_btn.set_label(self.shorten_path(self.input_dir))
            
            # Default output to input
            if not self.output_dir:
                self.output_dir = self.input_dir
                self.out_btn.set_label("Default: " + self.shorten_path(self.output_dir))
                
        dialog.destroy()

    def on_choose_output(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Please choose an output folder",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            "Select", Gtk.ResponseType.OK
        )
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.output_dir = dialog.get_filename()
            self.out_btn.set_label(self.shorten_path(self.output_dir))
            
        dialog.destroy()

    def on_convert_clicked(self, widget):
        if not self.input_dir:
            self.show_error_dialog("Please select an input folder first.")
            return

        if not os.path.exists(self.input_dir):
            self.show_error_dialog("Input directory does not exist.")
            return
            
        out_dir = self.output_dir if self.output_dir else self.input_dir
        if not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir)
            except Exception as e:
                self.show_error_dialog(f"Could not create output directory:\n{e}")
                return

        # Find files
        extensions = ('*.ppt', '*.pptx')
        files_to_convert = []
        for ext in extensions:
            files_to_convert.extend(glob.glob(os.path.join(self.input_dir, ext)))
        
        if not files_to_convert:
            self.show_info_dialog("Info", "No PPT or PPTX files found in the input folder.")
            return

        # Disable buttons and start thread
        self.convert_btn.set_sensitive(False)
        self.in_btn.set_sensitive(False)
        self.out_btn.set_sensitive(False)
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("0%")
        self.status_label.set_text(f"Starting conversion for {len(files_to_convert)} files...")
        
        thread = threading.Thread(target=self.run_conversion_task, args=(files_to_convert, out_dir))
        thread.daemon = True
        thread.start()

    def run_conversion_task(self, files_to_convert, output_dir):
        total_files = len(files_to_convert)
        success_count = 0
        error_count = 0

        for idx, file_path in enumerate(files_to_convert):
            filename = os.path.basename(file_path)
            
            # Update UI safely
            GLib.idle_add(self.update_status, f"Processing: {filename}...")
            
            try:
                # Run LibreOffice headless conversion
                cmd = self.get_libreoffice_command() + [
                    "--headless", "--convert-to", "pdf", file_path, "--outdir", output_dir
                ]
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                if process.returncode == 0:
                    success_count += 1
                else:
                    error_count += 1
                    print(f"Error converting {filename}: {process.stderr}")
                    
            except Exception as e:
                error_count += 1
                print(f"Exception converting {filename}: {e}")
            
            # Update progress
            progress = (idx + 1) / total_files
            GLib.idle_add(self.update_progress, progress, f"{int(progress * 100)}% ({idx+1}/{total_files})")

        # Finish up
        GLib.idle_add(self.finish_conversion, success_count, error_count)

    def update_status(self, text):
        self.status_label.set_text(text)
        return False  # Return False to remove from idle loop

    def update_progress(self, fraction, text):
        self.progress_bar.set_fraction(fraction)
        self.progress_bar.set_text(text)
        return False

    def finish_conversion(self, success_count, error_count):
        self.convert_btn.set_sensitive(True)
        self.in_btn.set_sensitive(True)
        self.out_btn.set_sensitive(True)
        
        if error_count > 0:
            status = f"Completed: {success_count} successful, {error_count} failed."
            self.status_label.set_text(status)
            self.show_error_dialog(f"Finished with some errors.\n\n{status}")
        else:
            status = f"Successfully converted all {success_count} presentations!"
            self.status_label.set_text(status)
            self.show_info_dialog("Success", status)
        
        return False

if __name__ == "__main__":
    app = PPT2PDFWindow()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()
