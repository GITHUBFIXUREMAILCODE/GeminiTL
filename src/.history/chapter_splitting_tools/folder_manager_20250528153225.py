"""
Folder Manager module for the novel translation tool.

Added 2025‑05‑09:
    • When clearing Output, also empties output/proofed_ai
      and removes output/images.
    • When clearing Input, removes input/images.
"""

import tkinter as tk
from tkinter import messagebox
import os
from typing import Optional, Callable
from pathlib import Path
from send2trash import send2trash
import shutil


class FolderManager:
    """Handles folder‑management operations."""

    def __init__(self, log_function: Optional[Callable] = None):
        self.log = log_function or print

        # Get the correct project directory (where the src folder is)
        # Instead of going up two levels from this file, use the current working directory
        script_dir = Path(os.getcwd())
        self.input_dir = script_dir / "input"
        self.output_dir = script_dir / "output"

        # constant sub‑folder names
        self.proofed_ai = self.output_dir / "proofed_ai"
        self.images_name = "images"

    # ---------- internal helpers ---------- #

    def _trash_path(self, path: Path) -> None:
        try:
            send2trash(str(path))
            self.log(f"Sent to Recycle Bin: {path}")
        except Exception as e:
            self.log(f"Failed to delete {path}: {e}")

    def _clear_folder_contents(self, folder: Path, display: str) -> None:
        if not folder.exists():
            self.log(f"Warning: {display} does not exist.")
            return
        for item in folder.iterdir():
            self._trash_path(item)
        self.log(f"Cleared all contents of {display}.")

    def _remove_images_folder(self, parent: Path, context: str) -> None:
        images = parent / self.images_name
        if images.exists():
            self._trash_path(images)
            self.log(f"Removed '{self.images_name}' folder inside {context} folder.")

    # ---------- public operations ---------- #

    def clear_top_level_files(self, folder: Path, display: str) -> None:
        if not folder.exists():
            self.log(f"Warning: {display} folder does not exist.")
            return
        for item in folder.iterdir():
            if item.is_file():
                self._trash_path(item)
            else:
                self.log(f"Skipped sub‑folder: {item}")
        self.log(f"Top‑level files in {display} folder sent to Recycle Bin.")

    def clear_input(self) -> None:
        self.clear_top_level_files(self.input_dir, "Input")
        self._remove_images_folder(self.input_dir, "Input")

    def clear_output(self) -> None:
        self.clear_top_level_files(self.output_dir, "Output")
        self._clear_folder_contents(self.proofed_ai, "'proofed_ai'")
        self._remove_images_folder(self.output_dir, "Output")

    # ---------- UI ---------- #

    def show_clear_dialog(self) -> None:
        def on_selection(selection: str) -> None:
            if selection == "Cancel":
                root.destroy()
                return

            plural = "s" if selection == "Both" else ""
            if not messagebox.askyesno(
                "Confirm",
                f"Are you sure you want to clear the {selection} folder{plural}?"
            ):
                root.destroy()
                return

            if selection == "Input":
                self.clear_input()
            elif selection == "Output":
                self.clear_output()
            elif selection == "Both":
                self.clear_input()
                self.clear_output()

            messagebox.showinfo("Success", f"{selection} folder{plural} cleared.")
            root.destroy()

        root = tk.Tk()
        root.title("Clear Folders")
        root.geometry("300x200")

        tk.Label(root, text="Select a folder to clear:", font=("Arial", 14)).pack(pady=10)
        tk.Button(root, text="Input",  command=lambda: on_selection("Input")).pack(fill="x", pady=5, padx=10)
        tk.Button(root, text="Output", command=lambda: on_selection("Output")).pack(fill="x", pady=5, padx=10)
        tk.Button(root, text="Both",   command=lambda: on_selection("Both")).pack(fill="x", pady=5, padx=10)
        tk.Button(root, text="Cancel", command=lambda: on_selection("Cancel")).pack(fill="x", pady=5, padx=10)

        root.mainloop()


def main() -> None:
    FolderManager().show_clear_dialog()


if __name__ == "__main__":
    main()
