"""
Output Combiner module for the novel translation tool.

This module provides functionality for:
- Combining multiple text files into a single output
- Creating EPUB files from combined text
- Managing file organization and output formats
"""

import os
import re
import tkinter as tk
from tkinter import messagebox, filedialog
from typing import List, Optional, Callable, Any
from pathlib import Path
from .epuboutputcreator import EPUBOutputCreator

class OutputCombiner:
    """
    Handles combining and outputting text files.
    
    This class provides functionality for:
    - Combining multiple text files into a single output
    - Creating EPUB files from combined text
    - Managing file organization and output formats
    """
    
    def __init__(self, log_function: Optional[Callable] = None):
        """
        Initialize the OutputCombiner.
        
        Args:
            log_function: Optional function to use for logging (defaults to print)
        """
        self.log_function = log_function or print
        self.epub_creator = EPUBOutputCreator(log_function)

    @staticmethod
    def natural_sort_key(key: str) -> List[Any]:
        """
        Helper function to generate a key for natural sorting (e.g., 1, 2, 10 instead of 1, 10, 2).
        
        Args:
            key: The string to generate a sort key for
            
        Returns:
            List of parts for natural sorting
        """
        return [int(c) if c.isdigit() else c.lower() for c in re.split('([0-9]+)', key)]

    def concatenate_files(self, folder_name: str, output_file: str, break_text: str = "\n---\n", 
                         save_as_epub: bool = False) -> None:
        """
        Concatenates text files in a folder into a single output file or creates an EPUB.

        Args:
            folder_name: Path to the folder containing text files
            output_file: Path to save the output file
            break_text: Text to insert between concatenated files
            save_as_epub: Whether to save the output as an EPUB file
        """
        # Check if the folder exists
        if not os.path.exists(folder_name):
            messagebox.showerror("Error", f"Folder '{folder_name}' does not exist.")
            return

        # Get all .txt files in the folder
        txt_files = [f for f in os.listdir(folder_name) if f.endswith('.txt')]
        if not txt_files:
            messagebox.showerror("Error", "No .txt files found.")
            return

        # Sort files using natural sorting
        txt_files = sorted(txt_files, key=self.natural_sort_key)

        concatenated_content = ""
        found_non_empty_file = False  # Track if any file has content
        for idx, file_name in enumerate(txt_files):
            file_path = os.path.join(folder_name, file_name)
            try:
                with open(file_path, 'r', encoding='utf-8') as infile:
                    content = infile.read().strip()  # Remove leading/trailing whitespace
                    if content:  # Only process non-empty files
                        found_non_empty_file = True
                        concatenated_content += content
                        if idx < len(txt_files) - 1:  # Add break_text unless it's the last file
                            concatenated_content += break_text
            except UnicodeDecodeError:
                messagebox.showerror("Error", f"Failed to read file: {file_name}. Ensure it is UTF-8 encoded.")
                return

        if not found_non_empty_file:
            messagebox.showerror("Error", "No non-empty files found. Output file will be empty.")
            return

        if save_as_epub:
            # Save as EPUB
            epub_output_dir = os.path.dirname(output_file)
            epub_name = os.path.basename(output_file).replace(".txt", ".epub")  # Ensure EPUB extension
            if os.path.exists(os.path.join(epub_output_dir, epub_name)):
                overwrite = messagebox.askyesno("Overwrite Confirmation", f"{epub_name} already exists. Overwrite?")
                if not overwrite:
                    return
            # Ask the user to select an image directory
            image_dir = filedialog.askdirectory(title="Select Image Directory for EPUB")
            if not image_dir:  # If no folder is selected, provide a default or cancel the operation
                messagebox.showerror("Error", "No image directory selected. EPUB creation canceled.")
                return

            self.epub_creator.create_epub(folder_name, os.path.join(epub_output_dir, epub_name), image_dir=image_dir)
            messagebox.showinfo("Success", f"File saved as EPUB: {epub_name}")
        else:
            # Save as TXT
            if os.path.exists(output_file):
                overwrite = messagebox.askyesno("Overwrite Confirmation", f"{output_file} already exists. Overwrite?")
                if not overwrite:
                    return
            try:
                # Write output in UTF-8 format
                with open(output_file, 'w', encoding='utf-8') as outfile:
                    outfile.write(concatenated_content)
                messagebox.showinfo("Success", f"File saved as TXT: {output_file}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {e}")

    def show_save_dialog(self, folder_name: str, break_text: str = "\n---\n") -> None:
        """
        Launches a GUI to save concatenated text as TXT or EPUB.
        
        Args:
            folder_name: Path to the folder containing text files
            break_text: Text to insert between concatenated files
        """
        # Create a Tkinter window
        root = tk.Tk()
        root.title("Save As")

        def save_as_txt():
            output_file_txt = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt")],
                title="Save as TXT"
            )
            if output_file_txt:
                self.concatenate_files(folder_name, output_file_txt, break_text, save_as_epub=False)
            root.destroy()

        def save_as_epub():
            output_file_epub = filedialog.asksaveasfilename(
                defaultextension=".epub",
                filetypes=[("EPUB Files", "*.epub")],
                title="Save as EPUB"
            )
            if output_file_epub:
                self.concatenate_files(folder_name, output_file_epub, break_text, save_as_epub=True)
            root.destroy()

        # Create buttons for saving as TXT or EPUB
        tk.Button(root, text="Save as TXT", command=save_as_txt).pack(pady=10)
        tk.Button(root, text="Save as EPUB", command=save_as_epub).pack(pady=10)

        # Run the Tkinter event loop
        root.mainloop()

def main() -> None:
    """Entry point for the application."""
    folder_name = "output"  # Replace with the path to the folder containing .txt files
    break_text = "\n---\n"
    combiner = OutputCombiner()
    combiner.show_save_dialog(folder_name, break_text)

if __name__ == "__main__":
    main()
