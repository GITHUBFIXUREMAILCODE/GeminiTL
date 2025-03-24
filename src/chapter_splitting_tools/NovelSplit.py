import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import requests
import re
import os

class TextSplitterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Novelpia Scraper Splitter")
        self.root.geometry("600x600")

        # Variables
        self.input_file = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.start_index = tk.IntVar(value=1)

        # Since we are only keeping Novelpia scraper mode, we no longer need a mode variable.
        # We'll always operate in "scraper" mode:
        self.novel_no = tk.StringVar()
        self.login_key = tk.StringVar()  # Will be autofilled from config
        self.chapter_names = []

        # Attempt to read config.txt from two folders up and autofill the login key
        self.load_config()

        # Build the UI
        self.create_widgets()

    def load_config(self):
        """
        Reads config.txt from two folders up (../../config.txt)
        and extracts the line starting with 'login_key=' to autofill self.login_key.
        """
        # Compute the path to config.txt two folders above this file’s directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(current_dir, "..", "..", "config.txt")

        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    for line in f:
                        # Expect lines like: login_key=YOUR_KEY_HERE
                        if line.startswith("login_key="):
                            value = line.split("=", 1)[1].strip()
                            self.login_key.set(value)
                            break
            except Exception as e:
                print(f"Error reading config file: {e}")

    def create_widgets(self):
        # Input file selection
        input_frame = ttk.LabelFrame(self.root, text="Input File", padding=10)
        input_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(input_frame, text="Selected File:").pack(side="left")
        ttk.Entry(input_frame, textvariable=self.input_file, width=50).pack(side="left", padx=5)
        ttk.Button(input_frame, text="Browse", command=self.select_input_file).pack(side="left")

        # Output directory selection
        output_frame = ttk.LabelFrame(self.root, text="Output Directory", padding=10)
        output_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(output_frame, text="Save to:").pack(side="left")
        ttk.Entry(output_frame, textvariable=self.output_dir, width=50).pack(side="left", padx=5)
        ttk.Button(output_frame, text="Browse", command=self.select_output_dir).pack(side="left")

        # Settings frame
        settings_frame = ttk.LabelFrame(self.root, text="Settings", padding=10)
        settings_frame.pack(fill="x", padx=10, pady=5)

        # Start index setting
        index_frame = ttk.Frame(settings_frame)
        index_frame.pack(fill="x", pady=5)
        ttk.Label(index_frame, text="Start Index:").pack(side="left")
        ttk.Entry(index_frame, textvariable=self.start_index, width=10).pack(side="left", padx=5)

        # Scraper settings frame
        scraper_frame = ttk.LabelFrame(self.root, text="Novelpia Scraper Settings", padding=10)
        scraper_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(scraper_frame, text="Novel Number:").pack(fill="x", pady=2)
        ttk.Entry(scraper_frame, textvariable=self.novel_no).pack(fill="x", pady=2)

        ttk.Label(scraper_frame, text="Login Key:").pack(fill="x", pady=2)
        ttk.Entry(scraper_frame, textvariable=self.login_key, show="*").pack(fill="x", pady=2)

        # Button to fetch chapter names
        ttk.Button(scraper_frame, text="Fetch Chapter Names",
                   command=self.fetch_chapter_names).pack(pady=5)

        # Process button
        ttk.Button(self.root, text="Process File", command=self.process_file).pack(pady=10)

        # Status text box
        self.status_text = tk.Text(self.root, height=8, width=60)
        self.status_text.pack(padx=10, pady=5)

    def select_input_file(self):
        filename = filedialog.askopenfilename(
            title="Select Input File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            self.input_file.set(filename)

    def select_output_dir(self):
        dirname = filedialog.askdirectory(title="Select Output Directory")
        if dirname:
            self.output_dir.set(dirname)

    def log_status(self, message):
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.root.update()

    def fetch_chapter_names(self):
        """
        Fetches the chapter names from Novelpia using the user-provided
        novel number and the login key (already read from config, if found).
        """
        try:
            novel_no = self.novel_no.get().strip()
            login_key = self.login_key.get().strip()

            if not novel_no or not login_key:
                messagebox.showerror("Error", "Please enter both Novel Number and Login Key.")
                return

            self.chapter_names = []
            page = 0
            previous_chapters = None

            while True:
                self.log_status(f"Fetching page {page}...")
                chapters = self.fetch_chapters_page(novel_no, page, login_key)

                # If no new chapters or repeated set, break out.
                if not chapters or chapters == previous_chapters:
                    break

                previous_chapters = chapters
                self.chapter_names.extend(chapters)
                page += 1

            self.log_status(f"Successfully fetched {len(self.chapter_names)} chapter names.")
            messagebox.showinfo("Success", f"Fetched {len(self.chapter_names)} chapter names.")

        except Exception as e:
            self.log_status(f"Error fetching chapters: {str(e)}")
            messagebox.showerror("Error", f"Failed to fetch chapters: {str(e)}")

    def fetch_chapters_page(self, novel_no, page, login_key):
        """
        Helper to fetch one page of chapter listings from Novelpia.
        """
        episode_list_url = "https://novelpia.com/proc/episode_list"
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        data = {"novel_no": novel_no, "sort": "DOWN", "page": page}
        cookies = {"LOGINKEY": login_key}

        response = requests.post(episode_list_url, headers=headers, data=data, cookies=cookies)
        if response.status_code != 200:
            return []

        matches = re.findall(r'id="bookmark_(\d+)"></i>(.+?)</b>', response.text)
        return [match[1].strip() for match in matches]

    def process_file(self):
        """
        Processes the input file by splitting it at the exact lines
        that match the fetched chapter names.
        """
        input_file = self.input_file.get()
        output_dir = self.output_dir.get()

        if not input_file or not output_dir:
            self.log_status("Please select both input file and output directory.")
            return

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        try:
            with open(input_file, 'r', encoding='utf-8', errors='replace') as infile:
                lines = infile.readlines()

            file_index = self.start_index.get()
            section = []
            inside_section = False
            current_chapter_index = 0

            for line in lines:
                is_new_section = False

                # The only logic we keep: if the line matches chapter_names[current_chapter_index],
                # we start a new section.
                if self.chapter_names and current_chapter_index < len(self.chapter_names):
                    if line.strip() == self.chapter_names[current_chapter_index]:
                        is_new_section = True
                        current_chapter_index += 1

                if is_new_section:
                    # Write the previous section out
                    if inside_section:
                        output_filename = os.path.join(output_dir, f"{file_index}.txt")
                        with open(output_filename, 'w', encoding='utf-8') as outfile:
                            outfile.writelines(section)
                        self.log_status(f"Section written to {output_filename}")
                        file_index += 1
                        section = []

                    section.append(line)
                    inside_section = True
                else:
                    if inside_section:
                        section.append(line)

            # Write the last section (if it exists)
            if section:
                output_filename = os.path.join(output_dir, f"{file_index}.txt")
                with open(output_filename, 'w', encoding='utf-8') as outfile:
                    outfile.writelines(section)
                self.log_status(f"Section written to {output_filename}")

            self.log_status("Processing completed successfully!")

        except Exception as e:
            self.log_status(f"An error occurred: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = TextSplitterApp(root)
    root.mainloop()
