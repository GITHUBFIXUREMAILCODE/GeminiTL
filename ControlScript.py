"""
Control script for the novel translation tool.

This script provides a GUI interface for managing the translation workflow,
including file selection, translation execution, and outp   ut management.
"""

import os
import sys
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional, Callable, List
import threading
from datetime import datetime

# Add src directory to Python path
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if src_path not in sys.path:
    sys.path.append(src_path)
# Import from the new package structure
from translation import main as translation_main
from chapter_splitting_tools.epub_separator import EPUBSeparator
from chapter_splitting_tools.novel_splitter import TextSplitterApp
from chapter_splitting_tools.output_combiner import OutputCombiner
from chapter_splitting_tools.folder_manager import FolderManager

class ControlScriptApp:
    """
    Main application class for the control script.
    
    This class provides a GUI interface for:
    - Selecting input files and glossaries
    - Running translations
    - Managing output files
    - Handling chapter splitting and combining
    """
    
    def __init__(self, root):
        """
        Initialize the application.
        
        Args:
            root: The root Tkinter window
        """
        from threading import Event

        # Thread control flags
        self.pause_event = Event()
        self.pause_event.set()  # Unpaused by default
        self.cancel_requested = False

        self.root = root
        self.root.title("Novel Translation Tool")
        self.root.geometry("800x600")
        
        # Create main frame
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create text area with scrollbar
        self.text_frame = tk.Frame(self.main_frame)
        self.text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.text_area = tk.Text(self.text_frame, wrap=tk.WORD, height=20)
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(self.text_frame, command=self.text_area.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area.config(yscrollcommand=scrollbar.set)
        
        # Create button frame
        self.button_frame = tk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, pady=10)
        
        # Create buttons
        self.create_buttons()
        
        # Initialize state
        self.input_folder = None
        self.glossary_file = None
        self.skip_to_proofing    = tk.BooleanVar(value=False)
        self.skip_to_translation = tk.BooleanVar(value=False)

        # Checkbox to skip straight to Phase 3 (Proofing only)
        self.skip_proofing_checkbox = tk.Checkbutton(
            self.button_frame,
            text="Skip to Proofing Only (Phase 3)",
            variable=self.skip_to_proofing
        )
        self.skip_proofing_checkbox.pack(side=tk.LEFT, padx=5)

        # Checkbox to skip glossary building (Phase 1) – Start at Translation
        self.skip_translation_checkbox = tk.Checkbutton(
            self.button_frame,
            text="Skip to Translation (Phase 2)",
            variable=self.skip_to_translation
        )
        self.skip_translation_checkbox.pack(side=tk.LEFT, padx=5)


        
        # Create default folders if they don't exist
        self.create_default_folders()
        
    def create_default_folders(self):
        """Create default folders if they don't exist."""
        folders = [
            "input",
            "translation",
            os.path.join("translation", "glossary"),
            "output"
        ]
        
        for folder in folders:
            if not os.path.exists(folder):
                os.makedirs(folder)
                self.log_message(f"Created folder: {folder}")
        
    def create_buttons(self):
        """Create and configure the control buttons."""
        # Translation button
        self.translate_button = tk.Button(
            self.button_frame,
            text="Run Translation",
            command=self.run_translation
        )
        self.translate_button.pack(side=tk.LEFT, padx=5)
        
        # Split button
        self.split_button = tk.Button(
            self.button_frame,
            text="Split Chapters",
            command=self.show_splitter_dialog
        )
        self.split_button.pack(side=tk.LEFT, padx=5)
        
        # Combine button
        self.combine_button = tk.Button(
            self.button_frame,
            text="Combine Output",
            command=self.run_output_combiner
        )
        self.combine_button.pack(side=tk.LEFT, padx=5)
        
        # Clear button
        self.clear_button = tk.Button(
            self.button_frame,
            text="Clear Folders",
            command=self.clear_folders
        )
        self.clear_button.pack(side=tk.LEFT, padx=5)

        self.pause_button = tk.Button(self.button_frame, text="Pause", command=self.toggle_pause)
        self.pause_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = tk.Button(self.button_frame, text="Stop", command=self.stop_translation)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        
    def log_message(self, *args) -> None:
        """Log a message with a timestamp to the text area, or fallback to stdout."""
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        message = f"{timestamp} " + " ".join(str(arg) for arg in args)
        try:
            if self.text_area and self.text_area.winfo_exists():
                self.text_area.insert(tk.END, message + "\n")
                self.text_area.see(tk.END)
                self.text_area.update_idletasks()
            else:
                print("[LOG fallback]", message)
        except tk.TclError:
            print("[LOG exception]", message)
        
    def select_glossary_file(self) -> Optional[str]:
        """Prompt user to select a glossary file from src/translation."""
        # Get the absolute path of the directory where ControlScript.py is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        default_dir = os.path.join(script_dir, "src", "translation")
        
        file_path = filedialog.askopenfilename(
            title="Select Glossary File",
            initialdir=default_dir,
            filetypes=[("Text files", "*.txt")]
        )
        
        if file_path:
            self.glossary_file = file_path
            self.log_message(f"Selected glossary: {os.path.basename(file_path)}")
            return file_path
        return None
        
    def select_input_folder(self) -> Optional[str]:
        """Prompt user to select an input folder."""
        folder_path = filedialog.askdirectory(
            title="Select Input Folder",
            initialdir="input"
        )
        if folder_path:
            self.input_folder = folder_path
            self.log_message(f"Selected input folder: {os.path.basename(folder_path)}")
        return folder_path
        
    def move_files_to_input(self, source_folder: str) -> None:
        """Move files from source folder to input folder."""
        try:
            for filename in os.listdir(source_folder):
                source_path = os.path.join(source_folder, filename)
                dest_path = os.path.join("input", filename)
                shutil.move(source_path, dest_path)
                self.log_message(f"Moved {filename} to input folder")
        except Exception as e:
            self.log_message(f"Error moving files: {str(e)}")
            raise
            import threading

    def run_translation(self) -> None:
        """Run the translation process in a background thread to keep the GUI responsive."""
        # Disable the translation button to prevent multiple clicks
        self.translate_button.config(state=tk.DISABLED)
        self.log_message("Starting translation...")

        # Prompt for input folder if not already selected.
        input_folder = self.select_input_folder()
        if not input_folder:
            self.log_message("No input folder selected. Aborting translation.")
            self.translate_button.config(state=tk.NORMAL)
            return
        self.move_files_to_input(input_folder)


        # Prompt for glossary file selection if not already selected
        self.glossary_file = self.select_glossary_file()
        if not self.glossary_file:
            # User cancelled the selection; create a new glossary file.
            script_dir = os.path.dirname(os.path.abspath(__file__))
            new_glossary_path = os.path.join(script_dir, "src", "translation", "default_glossary.txt")
            with open(new_glossary_path, "w", encoding="utf-8") as f:
                f.write("# Default glossary file\n")
            self.glossary_file = new_glossary_path
            self.log_message("No glossary file selected. Created new glossary at", new_glossary_path)

        # Create a worker function to run the translation process.
        def worker():
            try:
                from translation.main_ph import main as translation_main
                proofing_only = self.skip_to_proofing.get()
                skip_phase1 = self.skip_to_translation.get()

                translation_main(
                    log_message=self.log_message,
                    glossary_file=self.glossary_file,
                    proofing_only=proofing_only,
                    skip_phase1=skip_phase1,
                    pause_event=self.pause_event,
                    cancel_flag=lambda: self.cancel_requested  # pass as callable
                )

            except Exception as e:
                self.log_message(f"Error during translation: {str(e)}")
            finally:
                self.root.after(0, lambda: self.translate_button.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.log_message("Translation finished or aborted."))
                self.pause_event.set()  # Ensure it's unpaused next time
                self.cancel_requested = False
                self.pause_button.config(text="Pause")            
        threading.Thread(target=worker, daemon=True).start()

    def show_splitter_dialog(self) -> None:
        """Show dialog to select between Novel Splitter and EPUB Separator."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Splitter Type")
        dialog.geometry("300x150")
        
        def run_novel_splitter():
            dialog.destroy()
            self.run_novel_splitter()
            
        def run_epub_separator():
            dialog.destroy()
            self.run_epub_separator()
            
        tk.Label(dialog, text="Select splitter type:").pack(pady=10)
        tk.Button(dialog, text="Novel Splitter", command=run_novel_splitter).pack(pady=5)
        tk.Button(dialog, text="EPUB Separator", command=run_epub_separator).pack(pady=5)
            
    def run_novel_splitter(self) -> None:
        """Run the novel splitting process."""
        try:
            self.log_message("\nStarting novel splitting...")
            splitter = TextSplitterApp(tk.Toplevel(self.root))
            self.log_message("Novel splitting completed")
            
        except Exception as e:
            self.log_message(f"Error during novel splitting: {str(e)}")
            messagebox.showerror("Error", str(e))
            
    def run_epub_separator(self) -> None:
        """Run the EPUB separation process."""
        try:
            # Select EPUB file
            epub_file = filedialog.askopenfilename(
                title="Select EPUB File",
                filetypes=[("EPUB files", "*.epub")]
            )
            if not epub_file:
                return
                
            # Get EPUB filename without extension
            epub_name = os.path.splitext(os.path.basename(epub_file))[0]
            
            # Create input subdirectory with EPUB name
            input_subdir = os.path.join("input", epub_name)
            os.makedirs(input_subdir, exist_ok=True)
            
            # Run separator directly on the selected EPUB file
            self.log_message("\nStarting EPUB separation...")
            separator = EPUBSeparator(self.log_message)
            separator.separate(epub_file, input_subdir)
            self.log_message("EPUB separation completed")
            
        except Exception as e:
            self.log_message(f"Error during EPUB separation: {str(e)}")
            messagebox.showerror("Error", str(e))
            
    def run_output_combiner(self) -> None:
        """Run the output combining process."""
        try:
            # Select input directory
            input_dir = filedialog.askdirectory(
                title="Select Input Directory",
                initialdir="output"
            )
            if not input_dir:
                return
                
            # Create combiner
            self.log_message("\nStarting output combination...")
            combiner = OutputCombiner(self.log_message)
            combiner.show_save_dialog(input_dir)
            self.log_message("Output combination completed")
            
        except Exception as e:
            self.log_message(f"Error during combination: {str(e)}")
            messagebox.showerror("Error", str(e))
            
    def clear_folders(self) -> None:
        """Use FolderManager's GUI to select and clear folders with confirmation."""
        try:
            from chapter_splitting_tools.folder_manager import FolderManager
            manager = FolderManager(self.log_message)
            manager.show_clear_dialog()
        except Exception as e:
            self.log_message(f"Error clearing folders: {str(e)}")
            messagebox.showerror("Error", str(e))
    
    def toggle_pause(self):
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.log_message("[CONTROL] Paused after current chapter.")
            self.pause_button.config(text="Resume")
        else:
            self.pause_event.set()
            self.log_message("[CONTROL] Resumed.")
            self.root.after(0, lambda: self.pause_button.config(text="Pause"))

    def stop_translation(self):
        self.cancel_requested = True
        self.pause_event.set()  # Force release if paused
        self.log_message("[CONTROL] Stop requested. Will stop after current chapter.")



def main() -> None:
    """Main entry point for the control script."""
    root = tk.Tk()
    app = ControlScriptApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()


