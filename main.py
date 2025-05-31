
"""
Main entry point for the GeminiAPITranslator GUI application.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path if it's not already there
src_path = Path(__file__).parent / "src"
if src_path.exists() and str(src_path.resolve()) not in sys.path:
    sys.path.insert(0, str(src_path.resolve()))

# Now we can import from the src package
import tkinter as tk
from gui.app import TranslationApp

def main():
    # Ensure we're in the correct working directory (project root)
    # This is important for relative paths used in the application
    os.chdir(Path(__file__).parent)
    
    # Create and run the application
    root = tk.Tk()
    root.title("Gemini API Translator")
    app = TranslationApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
    

