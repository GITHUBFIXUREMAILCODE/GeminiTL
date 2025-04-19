"""
Folder Manager module for the novel translation tool.

This module provides functionality for:
- Managing input and output directories
- Clearing folder contents
- Providing a GUI interface for folder operations
"""

import tkinter as tk
from tkinter import messagebox
import os
from typing import Optional, Callable
from pathlib import Path
from send2trash import send2trash

class FolderManager:
    """
    Handles folder management operations.
    
    This class provides functionality for:
    - Managing input and output directories
    - Clearing folder contents
    - Providing a GUI interface for folder operations
    """
    
    def __init__(self, log_function: Optional[Callable] = None):
        """
        Initialize the FolderManager.
        
        Args:
            log_function: Optional function to use for logging (defaults to print)
        """
        self.log_function = log_function or print
        
        # Move up TWO levels to reach the main directory where ControlScript.py is located
        script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Correct paths (input/ and output/ are in the main directory)
        self.input_dir = os.path.join(script_dir, "input")
        self.output_dir = os.path.join(script_dir, "output")

    def clear_directory(self, folder_path: str, folder_display_name: str) -> None:
        """
        Sends all top-level files in the specified folder to the Recycle Bin.

        Args:
            folder_path: Path to the folder to clear
            folder_display_name: Display name for the folder (used in messages)
        """
        if not os.path.exists(folder_path):
            self.log_function(f"Warning: {folder_display_name} folder does not exist.")
            return

        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isfile(item_path):
                try:
                    send2trash(item_path)
                    self.log_function(f"Sent to Recycle Bin: {item_path}")
                except Exception as e:
                    self.log_function(f"Failed to delete {item_path}: {e}")
            else:
                self.log_function(f"Skipped subfolder: {item_path}")

        self.log_function(f"Top-level files in {folder_display_name} folder sent to Recycle Bin.")


    def show_clear_dialog(self) -> None:
        """
        Creates a popup to select Input, Output, or Both folders for clearing,
        followed by a single confirmation.
        """
        def on_selection(selection: str) -> None:
            # Confirm the operation
            if selection == "Cancel":
                root.destroy()
                return

            confirm = messagebox.askyesno(
                "Confirm",
                f"Are you sure you want to clear the {selection} folder{'s' if selection == 'Both' else ''}?"
            )

            if confirm:
                if selection == "Input":
                    self.clear_directory(self.input_dir, "Input")
                elif selection == "Output":
                    self.clear_directory(self.output_dir, "Output")
                elif selection == "Both":
                    self.clear_directory(self.input_dir, "Input")
                    self.clear_directory(self.output_dir, "Output")

                messagebox.showinfo("Success", f"{selection} folder{'s' if selection == 'Both' else ''} cleared.")
            
            root.destroy()

        # Create the popup for folder selection
        root = tk.Tk()
        root.title("Clear Folders")
        root.geometry("300x200")

        tk.Label(root, text="Select a folder to clear:", font=("Arial", 14)).pack(pady=10)

        # Add buttons for Input, Output, Both, and Cancel
        tk.Button(root, text="Input", command=lambda: on_selection("Input")).pack(fill="x", pady=5, padx=10)
        tk.Button(root, text="Output", command=lambda: on_selection("Output")).pack(fill="x", pady=5, padx=10)
        tk.Button(root, text="Both", command=lambda: on_selection("Both")).pack(fill="x", pady=5, padx=10)
        tk.Button(root, text="Cancel", command=lambda: on_selection("Cancel")).pack(fill="x", pady=5, padx=10)

        root.mainloop()

def main() -> None:
    """Entry point for the application."""
    manager = FolderManager()
    manager.show_clear_dialog()

if __name__ == "__main__":
    main()
