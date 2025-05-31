# gui/__init__.py
"""
GUI entrypoint for the Gemini novel translation tool.
"""

from .app import TranslationApp
import tkinter as tk

def main():
    root = tk.Tk()
    app = TranslationApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
