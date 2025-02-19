import tkinter as tk
from tkinter import filedialog
import subprocess
import os
import threading

from PH import main as run_translation
from OutputTextCombine import concatenate_files
from NovelSplit import TextSplitterApp
import EpubChapterSeperator

# Get the directory of the script
script_directory = os.path.dirname(os.path.abspath(__file__))

# Define folder paths
input_folder = os.path.join(script_directory, "input")
output_folder = os.path.join(script_directory, "output")

class ControlScriptApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Control Script")
        self.root.geometry("600x500")

        # Track whether translation is running
        self.translation_in_progress = False

        # Buttons for operations
        tk.Button(root, text="Run Novel Splitter", command=self.run_novel_splitter).pack(fill="x", pady=5)
        tk.Button(root, text="Run EPUB Chapter Separator", command=self.run_epub_separator).pack(fill="x", pady=5)
        tk.Button(root, text="Run Output Text Combiner / EPUB Creator", command=self.run_output_combiner_or_epub).pack(fill="x", pady=5)
        tk.Button(root, text="Run Translation", command=self.run_translation_button).pack(fill="x", pady=5)
        tk.Button(root, text="Clear Folders", command=self.run_clear_folders).pack(fill="x", pady=5)

        # Output log
        self.log_text = tk.Text(root, height=15, width=70, state="disabled")
        self.log_text.pack(padx=10, pady=10)

    def log_message(self, message):
        """
        Logs a message to the output log.
        """
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def run_novel_splitter(self):
        """
        Always allowed, regardless of translation state.
        """
        splitter_window = tk.Toplevel(self.root)
        app = TextSplitterApp(splitter_window)
        self.log_message("Novel Splitter launched.")

    def run_epub_separator(self):
        """
        Always allowed, regardless of translation state.
        Places output into input/[epub_file_name].
        """
        epub_file = filedialog.askopenfilename(
            title="Select an EPUB file", filetypes=[("EPUB files", "*.epub")]
        )
        if not epub_file:
            self.log_message("Error: No EPUB file selected.")
            return

        try:
            # Create a subfolder in `input` named after the EPUB file
            epub_name = os.path.basename(epub_file)
            output_subfolder = os.path.join(input_folder, epub_name)
            os.makedirs(output_subfolder, exist_ok=True)

            EpubChapterSeperator.main(epub_file, output_subfolder, 30000)
            self.log_message(f"EPUB Chapter Separator completed. Output saved to {output_subfolder}.")
        except Exception as e:
            self.log_message(f"Error: {e}")

    def run_output_combiner_or_epub(self):
        """
        Always allowed, regardless of translation state.
        """
        def on_selection(selection):
            if selection == "Cancel":
                combiner_window.destroy()
                return

            if selection == "Concatenate":
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
                    concatenate_files(output_folder, output_file, break_text="\n---\n", save_as_epub=False)
                    self.log_message(f"Output Text Combiner completed. Combined file saved to {output_file}.")
                except Exception as e:
                    self.log_message(f"Error: {e}")

            elif selection == "EPUB":
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
                    concatenate_files(output_folder, epub_name, break_text="\n---\n", save_as_epub=True)
                    self.log_message(f"EPUB Creator completed. EPUB saved to {epub_name}.")
                except Exception as e:
                    self.log_message(f"Error: {e}")

            combiner_window.destroy()

        combiner_window = tk.Toplevel(self.root)
        combiner_window.title("Select Operation")
        combiner_window.geometry("300x150")

        tk.Label(combiner_window, text="Choose an operation:", font=("Arial", 14)).pack(pady=10)

        tk.Button(combiner_window, text="Concatenate", command=lambda: on_selection("Concatenate")).pack(fill="x", pady=5, padx=10)
        tk.Button(combiner_window, text="EPUB", command=lambda: on_selection("EPUB")).pack(fill="x", pady=5, padx=10)
        tk.Button(combiner_window, text="Cancel", command=lambda: on_selection("Cancel")).pack(fill="x", pady=5, padx=10)

    def run_translation_button(self):
        """
        Runs translation in a separate thread if not already in progress.
        """
        if self.translation_in_progress:
            self.log_message("Translation is currently running. Please wait for it to finish.")
            return

        self.translation_in_progress = True

        def translation_thread():
            try:
                run_translation(input_folder, output_folder, self.log_message)
                self.log_message(f"Translation completed. Translated files saved to {output_folder}.")
            except Exception as e:
                self.log_message(f"Error: {e}")
            finally:
                self.translation_in_progress = False

        # Start the thread
        threading.Thread(target=translation_thread, daemon=True).start()

    def run_clear_folders(self):
        """
        Disallowed if translation is currently running.
        Otherwise, calls ClearFolders.py script to clear Input, Output, or Both folders.
        """
        if self.translation_in_progress:
            self.log_message("Translation is currently running. Cannot clear folders now.")
            return

        try:
            clear_folders_script = os.path.join(script_directory, "ClearFolders.py")
            if not os.path.exists(clear_folders_script):
                self.log_message("Error: ClearFolders.py script not found.")
                return

            # Run the ClearFolders.py script
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
