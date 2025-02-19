import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from collections import defaultdict

class ProperNounChecker:
    def __init__(self, root):
        self.root = root
        self.root.title("Proper Noun Checker")
        self.root.geometry("600x500")

        # found_noun -> set_of_files
        self.noun_dict = defaultdict(set)
        self.text_files = []

        # GUI Elements
        self.select_button = tk.Button(root, text="Select Folder", command=self.select_folder)
        self.select_button.pack(pady=10)

        # Scrollable frame for listing found nouns
        self.scroll_frame = tk.Frame(root)
        self.scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(self.scroll_frame)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.scrollbar = tk.Scrollbar(self.scroll_frame, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Create an inner frame to hold all rows of (found_noun, replacement_entry)
        self.inner_frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        self.inner_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Button to apply replacements
        self.replace_button = tk.Button(root, text="Replace Nouns", command=self.replace_nouns, state=tk.DISABLED)
        self.replace_button.pack(pady=10)

        # Button for next batch
        self.next_batch_button = tk.Button(root, text="Next Batch", command=self.select_folder, state=tk.DISABLED)
        self.next_batch_button.pack(pady=5)

        # Data structure to store entry widgets for each found noun
        self.noun_entries = {}  # { found_noun: tk.Entry widget }

        # You can adjust or clear this to allow more words
        self.known_words = {"The", "And", "Is", "Of", "To", "For", "With", "On",
                            "At", "By", "An", "In", "It", "He", "She", "This"}

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            print(f"[INFO] Selected folder: {folder}")
            # Clear data
            self.noun_dict.clear()
            self.noun_entries.clear()
            for widget in self.inner_frame.winfo_children():
                widget.destroy()
            self.replace_button.config(state=tk.DISABLED)
            self.next_batch_button.config(state=tk.DISABLED)

            # Gather text files
            self.text_files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".txt")]
            print(f"[INFO] Found text files: {self.text_files}")

            # Process files to find potential proper nouns
            self.process_files()

    def process_files(self):
        for file in self.text_files:
            print(f"[INFO] Scanning file: {file}")
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()

                # Split on whitespace/punctuation to get tokens
                tokens = re.findall(r"\\S+", content)
                
                # Debug: show all tokens from the file
                print(f"[INFO] Tokens in {file}:\n{tokens}")

                # We'll define 'proper noun' as: 
                # 1) First letter uppercase 
                # 2) Not all letters uppercase (to skip acronyms)
                # 3) Not in known words
                # 4) Has at least 2 characters (so 'A' alone doesn't match)
                found_nouns = set()
                for t in tokens:
                    if len(t) > 1 and t[0].isupper() and not t.isupper():
                        if t not in self.known_words:
                            found_nouns.add(t)

                # Associate found nouns with file
                for noun in found_nouns:
                    self.noun_dict[noun].add(file)

            print(f\"[INFO] Found {len(found_nouns)} potential nouns in {file}: {found_nouns}\")

        # Build the table for each found noun
        row = 0
        all_nouns = sorted(self.noun_dict.keys())
        print(f\"[INFO] Total distinct nouns found across all files: {all_nouns}\")
        
        for noun in all_nouns:
            lbl = tk.Label(self.inner_frame, text=noun)
            lbl.grid(row=row, column=0, padx=5, pady=5, sticky=\"w\")

            entry = tk.Entry(self.inner_frame, width=20)
            entry.insert(0, noun)  # default to same noun
            entry.grid(row=row, column=1, padx=5, pady=5, sticky=\"w\")
            self.noun_entries[noun] = entry
            row += 1

        if self.noun_dict:
            self.replace_button.config(state=tk.NORMAL)

    def replace_nouns(self):
        replacement_map = {}
        for old_noun, entry_widget in self.noun_entries.items():
            new_noun = entry_widget.get().strip()
            if new_noun == "":
                replacement_map[old_noun] = None
            else:
                replacement_map[old_noun] = new_noun

        print(f\"[INFO] Replacement map: {replacement_map}\")

        for old_noun, files in self.noun_dict.items():
            new_noun = replacement_map[old_noun]
            if new_noun is None:
                print(f\"[INFO] Skipping replacement for '{old_noun}' (blank)\")
                continue
            for file in files:
                print(f\"[INFO] Replacing '{old_noun}' with '{new_noun}' in {file}\")
                with open(file, \"r\", encoding=\"utf-8\") as f:
                    content = f.read()
                # Replace old_noun with new_noun (case-sensitive + word boundaries)
                content = re.sub(rf\"\\b{re.escape(old_noun)}\\b\", new_noun, content)
                with open(file, \"w\", encoding=\"utf-8\") as f:
                    f.write(content)

        messagebox.showinfo(\"Success\", \"Replacing Complete\")
        print(\"[INFO] Replacing Complete\")
        self.next_batch_button.config(state=tk.NORMAL)
        self.replace_button.config(state=tk.DISABLED)


if __name__ == \"__main__\":
    root = tk.Tk()
    app = ProperNounChecker(root)
    root.mainloop()
