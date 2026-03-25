#!/usr/bin/env python3

import os
import glob
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

class PPT2PDFApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PPT to PDF Converter")
        self.root.geometry("600x350")
        self.root.resizable(False, False)

        # Variables
        self.input_folder_var = tk.StringVar()
        self.output_folder_var = tk.StringVar()
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Ready")
        
        # Check LibreOffice
        if not self.check_libreoffice():
            messagebox.showerror("Error", "LibreOffice not found! Please install it.")
            self.root.destroy()
            return

        self.create_widgets()

    def check_libreoffice(self):
        try:
            subprocess.run(["libreoffice", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except FileNotFoundError:
            return False

    def create_widgets(self):
        # Style
        style = ttk.Style()
        style.configure("TButton", font=("Helvetica", 10), padding=5)
        style.configure("TLabel", font=("Helvetica", 10))

        # Main Frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="PPT/PPTX to PDF Converter", font=("Helvetica", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # Input Folder
        ttk.Label(main_frame, text="Input Folder:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.input_folder_var, width=50).grid(row=1, column=1, padx=10, pady=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_input).grid(row=1, column=2, pady=5)

        # Output Folder (Optional - defaults to input folder)
        ttk.Label(main_frame, text="Output Folder:").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.output_folder_var, width=50).grid(row=2, column=1, padx=10, pady=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_output).grid(row=2, column=2, pady=5)

        # Start Button
        self.start_btn = ttk.Button(main_frame, text="Convert to PDF", style="Accent.TButton", command=self.start_conversion)
        self.start_btn.grid(row=3, column=0, columnspan=3, pady=20)

        # Progress Bar
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100, mode='determinate')
        self.progress_bar.grid(row=4, column=0, columnspan=3, fill=tk.X, pady=(10, 5))

        # Status Label
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, font=("Helvetica", 9, "italic"))
        self.status_label.grid(row=5, column=0, columnspan=3, sticky="w")

    def browse_input(self):
        folder = filedialog.askdirectory(title="Select Input Folder containing PPT/PPTX")
        if folder:
            self.input_folder_var.set(folder)
            # Auto-set output folder to input folder if empty
            if not self.output_folder_var.get():
                self.output_folder_var.set(folder)

    def browse_output(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder_var.set(folder)

    def start_conversion(self):
        input_dir = self.input_folder_var.get()
        output_dir = self.output_folder_var.get()

        if not input_dir:
            messagebox.showwarning("Warning", "Please select an Input Folder.")
            return

        if not os.path.isdir(input_dir):
            messagebox.showerror("Error", "Input directory does not exist.")
            return
            
        if not output_dir:
            output_dir = input_dir

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Find files
        extensions = ('*.ppt', '*.pptx')
        files_to_convert = []
        for ext in extensions:
            files_to_convert.extend(glob.glob(os.path.join(input_dir, ext)))
        
        if not files_to_convert:
            messagebox.showinfo("Info", "No PPT or PPTX files found in the input folder.")
            return

        # Disable buttons and start thread
        self.start_btn.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.status_var.set(f"Found {len(files_to_convert)} files. Starting conversion...")
        
        thread = threading.Thread(target=self.run_conversion_task, args=(files_to_convert, output_dir))
        thread.daemon = True
        thread.start()

    def run_conversion_task(self, files_to_convert, output_dir):
        total_files = len(files_to_convert)
        success_count = 0
        error_count = 0

        for idx, file_path in enumerate(files_to_convert):
            filename = os.path.basename(file_path)
            
            # Update UI safely
            self.root.after(0, lambda f=filename: self.status_var.set(f"Converting: {f} ..."))
            
            try:
                # Run LibreOffice headless conversion
                process = subprocess.run(
                    ["libreoffice", "--headless", "--convert-to", "pdf", file_path, "--outdir", output_dir],
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
            progress = ((idx + 1) / total_files) * 100
            self.root.after(0, lambda p=progress: self.progress_var.set(p))

        # Finish up
        if error_count > 0:
            final_status = f"Completed: {success_count} successful, {error_count} failed."
            msg_type = "warning"
            msg_title = "Finished with errors"
        else:
            final_status = f"Successfully converted all {success_count} files!"
            msg_type = "info"
            msg_title = "Success"

        self.root.after(0, lambda: self.finish_conversion(final_status, msg_title, final_status, msg_type))

    def finish_conversion(self, status_text, msg_title, msg_text, msg_type):
        self.status_var.set(status_text)
        self.start_btn.config(state=tk.NORMAL)
        if msg_type == "info":
            messagebox.showinfo(msg_title, msg_text)
        else:
            messagebox.showwarning(msg_title, msg_text)

if __name__ == "__main__":
    # Workaround to make sure LibreOffice is installed correctly on linux
    root = tk.Tk()
    
    # Try to load a ttk theme if available (clam looks better on linux)
    style = ttk.Style()
    if "clam" in style.theme_names():
        style.theme_use("clam")
        
    app = PPT2PDFApp(root)
    root.mainloop()
