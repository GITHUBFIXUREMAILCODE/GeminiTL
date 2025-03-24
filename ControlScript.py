import tkinter as tk
from tkinter import filedialog
import subprocess
import sys
import io
import os
import shutil
import threading
import html
import datetime
import re

# Get the absolute path of src/
script_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(script_dir, "src")

# Add src/ to Python's module search path
sys.path.append(src_path)

# --- CHAPTER SPLITTING TOOLS IMPORTS ---
from src.chapter_splitting_tools.NovelSplit import TextSplitterApp
import src.chapter_splitting_tools.EpubChapterSeperator as EpubChapterSeperator
from src.chapter_splitting_tools.OutputTextCombine import concatenate_files

# --- TRANSLATION SCRIPT IMPORT ---
from src.translation.main_ph import main as run_translation
from src.translation.ocr_fail_detection import main as run_ocr_fail_detection

# Directory paths
script_directory = os.path.dirname(os.path.abspath(__file__))
input_folder = os.path.join(script_directory, "input")
output_folder = os.path.join(script_directory, "output")

# Error log path
error_log_path = os.path.join(script_directory, "error.txt")

class ControlScriptApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Control Script")
        self.root.geometry("600x500")
        self.translation_in_progress = False

        # Buttons
        tk.Button(root, text="Run Novel Splitter", 
                  command=self.run_novel_splitter).pack(fill="x", pady=5)
        tk.Button(root, text="Run EPUB Chapter Separator", 
                  command=self.run_epub_separator).pack(fill="x", pady=5)
        tk.Button(root, text="Run Output Text Combiner / EPUB Creator", 
                  command=self.run_output_combiner_or_epub).pack(fill="x", pady=5)
        tk.Button(root, text="Run Translation", 
                  command=self.run_translation_button).pack(fill="x", pady=5)
        tk.Button(root, text="Clear Folders", 
                  command=self.run_clear_folders).pack(fill="x", pady=5)

        # Log output text box
        self.log_text = tk.Text(root, height=15, width=70, state="disabled")
        self.log_text.pack(padx=10, pady=10)

    def log_message(self, message):
        """Append a message to the log text box."""
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    # -------------------------------------------------------------------------
    # 1) Novel Splitter
    # -------------------------------------------------------------------------
    def run_novel_splitter(self):
        """Launch the Novel Splitter GUI from src/chapter_splitting_tools/NovelSplit.py"""
        splitter_window = tk.Toplevel(self.root)
        TextSplitterApp(splitter_window)  # create the app in the new window
        self.log_message("Novel Splitter launched.")

    # -------------------------------------------------------------------------
    # 2) EPUB Chapter Separator
    # -------------------------------------------------------------------------
    def run_epub_separator(self):
        """
        Use EpubChapterSeperator.py to split multiple EPUB files into chapters.
        Each EPUB will be placed into its own subfolder (named after the EPUB file) under 'input'.
        """
        epub_files = filedialog.askopenfilenames(
            title="Select EPUB file(s)",
            filetypes=[("EPUB files", "*.epub")]
        )
        if not epub_files:
            self.log_message("Error: No EPUB files selected.")
            return

        for epub_file in epub_files:
            try:
                epub_name = os.path.basename(epub_file)
                output_subfolder = os.path.join(input_folder, epub_name)
                os.makedirs(output_subfolder, exist_ok=True)

                # Split into ~30,000 byte chapters
                EpubChapterSeperator.main(epub_file, output_subfolder, 30000)
                self.log_message(
                    f"EPUB Chapter Separator completed.\n"
                    f"Input: {epub_file}\n"
                    f"Output -> {output_subfolder}"
                )
            except Exception as e:
                self.log_message(f"[ERROR run_epub_separator] {epub_file} => {e}")

    # -------------------------------------------------------------------------
    # 3) Output Text Combiner / EPUB Creator
    # -------------------------------------------------------------------------
    def run_output_combiner_or_epub(self):
        """
        Combine text files in 'output' into one file OR create an EPUB,
        using 'OutputTextCombine.py' from chapter_splitting_tools.
        """
        def on_selection(selection):
            if selection == "Cancel":
                combiner_window.destroy()
                return

            if selection == "Concatenate":
                # Prompt user for a .txt file
                output_file = filedialog.asksaveasfilename(
                    title="Save Combined Output As",
                    defaultextension=".txt",
                    initialdir=script_directory,
                    initialfile="combined_output.txt"
                )
                if not output_file:
                    self.log_message("Error: No output file selected.")
                    return
                try:
                    concatenate_files(
                        folder_name=output_folder, 
                        output_file=output_file, 
                        break_text="\n---\n", 
                        save_as_epub=False
                    )
                    self.log_message(f"Combined text saved to {output_file}.")
                except Exception as e:
                    self.log_message(f"[ERROR combining] {e}")

            elif selection == "EPUB":
                # Prompt user for a .epub file
                epub_name = filedialog.asksaveasfilename(
                    title="Save EPUB As",
                    defaultextension=".epub",
                    initialdir=script_directory,
                    initialfile="generated.epub"
                )
                if not epub_name:
                    self.log_message("Error: No EPUB file selected.")
                    return
                try:
                    concatenate_files(
                        folder_name=output_folder, 
                        output_file=epub_name, 
                        break_text="\n---\n", 
                        save_as_epub=True
                    )
                    self.log_message(f"EPUB created at {epub_name}.")
                except Exception as e:
                    self.log_message(f"[ERROR creating EPUB] {e}")

            combiner_window.destroy()

        # A small popup asking user to choose "Concatenate" or "EPUB"
        combiner_window = tk.Toplevel(self.root)
        combiner_window.title("Select Operation")
        combiner_window.geometry("300x150")

        tk.Label(combiner_window, text="Choose an operation:", font=("Arial", 14)).pack(pady=10)
        tk.Button(combiner_window, text="Concatenate",
                  command=lambda: on_selection("Concatenate")).pack(fill="x", pady=5, padx=10)
        tk.Button(combiner_window, text="EPUB",
                  command=lambda: on_selection("EPUB")).pack(fill="x", pady=5, padx=10)
        tk.Button(combiner_window, text="Cancel",
                  command=lambda: on_selection("Cancel")).pack(fill="x", pady=5, padx=10)

    # -------------------------------------------------------------------------
    # 4) Run Translation (calls src/translation/main_ph.py)
    # -------------------------------------------------------------------------
    def run_translation_button(self):
        """
        1. Prompt user to select a folder within 'input/'.
           - Move ALL contents of that folder up into the main 'input/' directory.
        2. Optionally split large input files (split_large_files.py).
        3. Run the translation pipeline from main_ph.py in a thread.
        4. After translation completes, call ocr_fail_detection.py and
           check for missing chapters (logging them to error.txt).
        """
        if self.translation_in_progress:
            self.log_message("Translation is currently running. Please wait.")
            return

        # 1) Prompt user to select a subfolder of 'input/'
        selected_dir = filedialog.askdirectory(
            title="Select a folder inside 'input' to use for translation",
            initialdir=input_folder
        )
        if not selected_dir:
            self.log_message("No folder selected. Translation canceled.")
            return

        # Validate the folder is indeed inside 'input/'
        # (If the user picks something outside, we can warn or proceed differently.)
        # We'll do a simple check that selected_dir starts with the `input_folder` path
        # or is exactly that path.
        selected_dir = os.path.normpath(selected_dir)
        if not selected_dir.startswith(os.path.normpath(input_folder)):
            self.log_message("Selected folder is not inside 'input' folder. Translation canceled.")
            return

        # Move all contents from the chosen folder into 'input/'
        try:
            for item in os.listdir(selected_dir):
                src_path = os.path.join(selected_dir, item)
                dest_path = os.path.join(input_folder, item)
                shutil.move(src_path, dest_path)
            self.log_message(f"Moved contents from {selected_dir} -> {input_folder}")
        except Exception as move_err:
            self.log_message(f"[ERROR moving contents]: {move_err}")
            return

        # 2) If you have a "split_large_files.py" in chapter_splitting_tools, run it first
        splitter_script = os.path.join(script_directory, "src", "chapter_splitting_tools", "split_large_files.py")
        if os.path.exists(splitter_script):
            try:
                result = subprocess.run(
                    ["python", splitter_script, input_folder, "--max-bytes", "30000"],
                    capture_output=True, text=True
                )
                self.log_message(f"File splitting completed.\n{result.stdout}")
                if result.stderr:
                    self.log_message(f"[ERROR in splitter] {result.stderr}")
            except subprocess.CalledProcessError as e:
                self.log_message(f"Error while running split_large_files.py: {e}")
                return
        else:
            self.log_message("split_large_files.py not found. (Skipping split step.)")

        # 3) Run translation in a separate thread
        self.translation_in_progress = True

        def translation_thread():
            try:
                # Run translation
                run_translation(self.log_message)
                self.log_message(f"Translation completed. Files -> {output_folder}.")

                # Run OCR fail detection
                self.run_ocr_fail_detection()

                # After all is done, check for missing chapters
                self.check_for_missing_chapters()

            except Exception as e:
                self.log_message(f"Translation Error: {e}")
            finally:
                self.translation_in_progress = False

        threading.Thread(target=translation_thread, daemon=True).start()

    def run_ocr_fail_detection(self):
        """
        Runs ocr_fail_detection.py and captures its output in the GUI.
        """
        try:
            # Capture stdout
            output_capture = io.StringIO()
            sys.stdout = output_capture  # Redirect print() output

            run_ocr_fail_detection()  # Call main() directly

            # Restore stdout and send output to GUI
            sys.stdout = sys.__stdout__
            self.log_message(output_capture.getvalue())  # Send captured text to the GUI

        except Exception as e:
            sys.stdout = sys.__stdout__  # Restore stdout in case of an error
            self.log_message(f"OCR Fail Detection Error: {e}")

    def check_for_missing_chapters(self):
        """
        Compare input .txt chapter files with output/translated .txt files
        to see if any are missing. Log missing chapters to error.txt with
        timestamp.
        """
        try:
            # Gather expected chapters from input folder
            expected_chapters = set()
            for fname in os.listdir(input_folder):
                if fname.endswith(".txt"):
                    cnum = self.extract_chapter_number(fname)
                    if cnum is not None:
                        expected_chapters.add(cnum)

            # Gather actual chapters from output folder
            actual_chapters = set()
            for fname in os.listdir(output_folder):
                # We consider only "translated_{some_number}.txt"
                if fname.startswith("translated_") and fname.endswith(".txt"):
                    cnum = self.extract_chapter_number(fname)
                    if cnum is not None:
                        actual_chapters.add(cnum)

            # Find missing
            missing_chapters = expected_chapters - actual_chapters
            if missing_chapters:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(error_log_path, "a", encoding="utf-8") as error_log:
                    error_log.write(f"\n[{timestamp}] Missing Chapters: {sorted(missing_chapters)}\n")
                self.log_message(f"Warning: Missing Chapters detected: {sorted(missing_chapters)}")
            else:
                self.log_message("All chapters were successfully translated.")
        except Exception as e:
            self.log_message(f"Error checking for missing chapters: {e}")

    def extract_chapter_number(self, filename):
        """Extract the first number in a filename as an integer, if any."""
        match = re.search(r'(\d+)', filename)
        return int(match.group(1)) if match else None

    # -------------------------------------------------------------------------
    # 5) Clear Folders
    # -------------------------------------------------------------------------
    def run_clear_folders(self):
        """Call ClearFolders.py if it exists in chapter_splitting_tools."""
        if self.translation_in_progress:
            self.log_message("Translation is running. Cannot clear folders now.")
            return

        clear_folders_script = os.path.join(script_directory, "src", "chapter_splitting_tools", "ClearFolders.py")
        if not os.path.exists(clear_folders_script):
            self.log_message("Error: ClearFolders.py not found.")
            return

        try:
            subprocess.run(["python", clear_folders_script], check=True)
            self.log_message("Clear Folders operation completed.")
        except subprocess.CalledProcessError as e:
            self.log_message(f"Error while running ClearFolders.py: {e}")
        except Exception as e:
            self.log_message(f"Unexpected error: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ControlScriptApp(root)
    root.mainloop()
