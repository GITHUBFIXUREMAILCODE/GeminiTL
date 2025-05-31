
import os
import shutil
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
from datetime import datetime

# Ensure src/ is in sys.path so imports work correctly if run from GUI
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from chapter_splitting_tools.epub_separator import EPUBSeparator
from chapter_splitting_tools.novel_splitter import TextSplitterApp
from chapter_splitting_tools.output_combiner import OutputCombiner
from chapter_splitting_tools.folder_manager import FolderManager
from translation.translationManager import main as translation_main

class TranslationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Novel Translation Tool")
        self.root.geometry("1200x600")

        # Threading flags
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.cancel_requested = False

        self.input_folder = None
        self.glossary_file = None

        # GUI state
        self.skip_to_proofing = tk.BooleanVar(value=False)
        self.skip_to_translation = tk.BooleanVar(value=False)
        self.language_var = tk.StringVar(value="Japanese")

        self._build_ui()
        self._create_default_folders()

    def _build_ui(self):
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.text_frame = tk.Frame(self.main_frame)
        self.text_frame.pack(fill=tk.BOTH, expand=True)

        self.text_area = tk.Text(self.text_frame, wrap=tk.WORD, height=20)
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(self.text_frame, command=self.text_area.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area.config(yscrollcommand=scrollbar.set)

        self.button_frame = tk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, pady=10)

        # Buttons
        tk.Button(self.button_frame, text="Run Translation", command=self.run_translation).pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="Split Chapters", command=self.show_splitter_dialog).pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="Combine Output", command=self.run_output_combiner).pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="Clear Folders", command=self.clear_folders).pack(side=tk.LEFT, padx=5)
        self.pause_button = tk.Button(self.button_frame, text="Pause", command=self.toggle_pause)
        self.pause_button.pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="Stop", command=self.stop_translation).pack(side=tk.LEFT, padx=5)

        # Replace checkboxes with a dropdown for phase selection
        ttk.Label(self.button_frame, text="Start From Phase:").pack(side=tk.LEFT, padx=5)
        self.phase_var = tk.StringVar(value="Phase 1: Glossary")
        ttk.Combobox(
            self.button_frame,
            textvariable=self.phase_var,
            values=[
                "Phase 1: Glossary", 
                "Phase 2: Translation", 
                "Phase 3: Proofing",
                "Phase 3.1: Non-English Check",
                "Phase 3.2: Consistency Check",
                "Phase 3.3: Gender Proofing",
                "Phase 3.4: Final Proofing"
            ],
            state="readonly",
            width=20
        ).pack(side=tk.LEFT, padx=5)

        # Language selector
        ttk.Label(self.button_frame, text="Source Language:").pack(side=tk.LEFT, padx=5)
        ttk.Combobox(
            self.button_frame,
            textvariable=self.language_var,
            values=["Japanese", "Chinese", "Korean"],
            state="readonly",
            width=12
        ).pack(side=tk.LEFT, padx=5)

    def _create_default_folders(self):
        for folder in ["input", "output", "translation", os.path.join("translation", "glossary")]:
            os.makedirs(folder, exist_ok=True)
            self.log_message(f"[INIT] Ensured folder exists: {folder}")

    def log_message(self, *args):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        message = f"{timestamp} " + " ".join(str(arg) for arg in args)

        try:
            self.text_area.insert(tk.END, message + "\n")
            self.text_area.see(tk.END)
            self.text_area.update_idletasks()
        except Exception:
            print("[LOG]", message)

    def run_translation(self):
        self.translate_button = self.button_frame.children.get("!button")
        if self.translate_button:
            self.translate_button.config(state=tk.DISABLED)

        input_folder = self.select_input_folder()
        if not input_folder:
            self.log_message("No input folder selected. Aborting.")
            return
        self._move_files_to_input(input_folder)

        glossary_file = self.select_glossary_file()
        self.glossary_file = glossary_file

        selected_lang = self.language_var.get()

        def worker():
            try:
                selected_phase = self.phase_var.get()
                
                # Map dropdown selection to parameters
                skip_to_proofing = selected_phase.startswith("Phase 3")
                skip_to_translation = selected_phase.startswith("Phase 2") or skip_to_proofing
                
                # For sub-phases of proofing
                proofing_subphase = None
                if "3.1" in selected_phase:
                    proofing_subphase = "non_english"
                elif "3.2" in selected_phase:
                    proofing_subphase = "consistency"
                elif "3.3" in selected_phase:
                    proofing_subphase = "gender"
                elif "3.4" in selected_phase:
                    proofing_subphase = "final"
                
                translation_main(
                    log_message=self.log_message,
                    glossary_file=self.glossary_file,
                    proofing_only=skip_to_proofing,
                    skip_phase1=skip_to_translation,
                    proofing_subphase=proofing_subphase,
                    pause_event=self.pause_event,
                    cancel_flag=lambda: self.cancel_requested,
                    source_lang=selected_lang
                )
            except Exception as e:
                self.log_message("[ERROR]", e)
            finally:
                self.pause_event.set()
                self.cancel_requested = False
                self.pause_button.config(text="Pause")
                self.translate_button.config(state=tk.NORMAL)

        threading.Thread(target=worker, daemon=True).start()

    def select_input_folder(self):
        folder = filedialog.askdirectory(title="Select Input Folder", initialdir="input")
        if folder:
            self.input_folder = folder
            self.log_message(f"Selected input folder: {os.path.basename(folder)}")
        return folder

    def select_glossary_file(self):
        default_dir = os.path.join(os.path.dirname(__file__), "..", "translation")
        file_path = filedialog.askopenfilename(title="Select Glossary", initialdir=default_dir, filetypes=[("Text files", "*.txt")])
        return file_path

    def _move_files_to_input(self, src):
        for filename in os.listdir(src):
            shutil.move(os.path.join(src, filename), os.path.join("input", filename))
            self.log_message(f"Moved {filename} to input folder")

    def show_splitter_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Choose Splitter")
        dialog.geometry("300x150")

        tk.Label(dialog, text="Choose splitter type:").pack(pady=10)
        tk.Button(dialog, text="Novel Splitter", command=lambda: [dialog.destroy(), self.run_novel_splitter()]).pack(pady=5)
        tk.Button(dialog, text="EPUB Separator", command=lambda: [dialog.destroy(), self.run_epub_separator()]).pack(pady=5)

    def run_novel_splitter(self):
        self.log_message("Starting Novel Splitter")
        TextSplitterApp(tk.Toplevel(self.root))

    def run_epub_separator(self):
        epub_file = filedialog.askopenfilename(title="Select EPUB", filetypes=[("EPUB files", "*.epub")])
        if not epub_file:
            return
        epub_name = os.path.splitext(os.path.basename(epub_file))[0]
        input_subdir = os.path.join("input", epub_name)
        os.makedirs(input_subdir, exist_ok=True)

        self.log_message(f"Running EPUB Separator for {epub_name}")
        separator = EPUBSeparator(self.log_message)
        separator.separate(epub_file, input_subdir)

    def run_output_combiner(self):
        folder = filedialog.askdirectory(title="Select Output Folder", initialdir="output")
        if folder:
            combiner = OutputCombiner(self.log_message)
            combiner.show_save_dialog(folder)

    def clear_folders(self):
        manager = FolderManager(self.log_message)
        manager.show_clear_dialog()

    def toggle_pause(self):
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.pause_button.config(text="Resume")
            self.log_message("[CONTROL] Paused")
        else:
            self.pause_event.set()
            self.pause_button.config(text="Pause")
            self.log_message("[CONTROL] Resumed")

    def stop_translation(self):
        self.cancel_requested = True
        self.pause_event.set()
        self.log_message("[CONTROL] Stop requested. Will stop after current chapter.")



