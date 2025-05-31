
"""
Main entry point for the GeminiAPITranslator GUI application.
"""

import tkinter as tk
from gui.app import TranslationApp

def main():
    root = tk.Tk()
    app = TranslationApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
    
