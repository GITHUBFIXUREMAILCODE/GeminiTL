import tkinter as tk
from tkinter import messagebox
import os

# Get the directory of the script
script_directory = os.path.dirname(os.path.abspath(__file__))

# Define folder paths
input_folder = os.path.join(script_directory, "input")
output_folder = os.path.join(script_directory, "output")

def clear_folders():
    """
    Creates a popup to select Input, Output, or Both folders for clearing,
    followed by a single confirmation.
    """
    def on_selection(selection):
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
                clear_directory(input_folder, "Input")
            elif selection == "Output":
                clear_directory(output_folder, "Output")
            elif selection == "Both":
                clear_directory(input_folder, "Input")
                clear_directory(output_folder, "Output")

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

def clear_directory(folder_path, folder_display_name):
    """
    Clears all files in the specified folder.
    """
    if not os.path.exists(folder_path):
        print(f"Warning: {folder_display_name} folder does not exist.")
        return

    for file in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file)
        if os.path.isfile(file_path):
            os.remove(file_path)
    print(f"All contents of the {folder_display_name} folder cleared.")

if __name__ == "__main__":
    clear_folders()
