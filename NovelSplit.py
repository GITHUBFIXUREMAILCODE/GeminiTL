import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import requests
import re
import os

class TextSplitterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Text File Splitter")
        self.root.geometry("600x600")

        # Variables
        self.input_file = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.start_index = tk.IntVar(value=1)
        self.mode = tk.StringVar(value="chapter")
        self.novel_no = tk.StringVar()
        self.login_key = tk.StringVar()
        self.chapter_names = []

        self.create_widgets()

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

        # Mode selection
        mode_frame = ttk.Frame(settings_frame)
        mode_frame.pack(fill="x", pady=5)
        ttk.Radiobutton(mode_frame, text="Chapter Mode (XXX화)", value="chapter",
                       variable=self.mode, command=self.toggle_scraper_frame).pack(side="left", padx=5)
        ttk.Radiobutton(mode_frame, text="Chapter Mode (XXX. ...)", value="title",
                       variable=self.mode, command=self.toggle_scraper_frame).pack(side="left", padx=5)
        ttk.Radiobutton(mode_frame, text="Novelpia Scraper Mode", value="scraper",
                       variable=self.mode, command=self.toggle_scraper_frame).pack(side="left", padx=5)

        # Scraper settings frame
        self.scraper_frame = ttk.LabelFrame(self.root, text="Novelpia Scraper Settings", padding=10)

        ttk.Label(self.scraper_frame, text="Novel Number:").pack(fill="x", pady=2)
        ttk.Entry(self.scraper_frame, textvariable=self.novel_no).pack(fill="x", pady=2)

        ttk.Label(self.scraper_frame, text="Login Key:").pack(fill="x", pady=2)
        ttk.Entry(self.scraper_frame, textvariable=self.login_key, show="*").pack(fill="x", pady=2)

        ttk.Button(self.scraper_frame, text="Fetch Chapter Names",
                  command=self.fetch_chapter_names).pack(pady=5)

        # Process button
        ttk.Button(self.root, text="Process File", command=self.process_file).pack(pady=10)

        # Status text
        self.status_text = tk.Text(self.root, height=8, width=60)
        self.status_text.pack(padx=10, pady=5)

    def toggle_scraper_frame(self):
        if self.mode.get() == "scraper":
            self.scraper_frame.pack(fill="x", padx=10, pady=5)
        else:
            self.scraper_frame.pack_forget()

    def fetch_chapter_names(self):
        try:
            novel_no = self.novel_no.get()
            login_key = self.login_key.get()

            if not novel_no or not login_key:
                messagebox.showerror("Error", "Please enter both Novel Number and Login Key")
                return

            self.chapter_names = []
            page = 0
            previous_chapters = None

            while True:
                self.log_status(f"Fetching page {page}...")
                chapters = self.fetch_chapters_page(novel_no, page, login_key)

                if not chapters or chapters == previous_chapters:
                    break

                previous_chapters = chapters
                self.chapter_names.extend(chapters)
                page += 1

            self.log_status(f"Successfully fetched {len(self.chapter_names)} chapter names")
            messagebox.showinfo("Success", f"Fetched {len(self.chapter_names)} chapter names")

        except Exception as e:
            self.log_status(f"Error fetching chapters: {str(e)}")
            messagebox.showerror("Error", f"Failed to fetch chapters: {str(e)}")

    def fetch_chapters_page(self, novel_no, page, login_key):
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

    def process_file(self):
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

                if self.mode.get() == "chapter":
                    if line[0].isdigit() and line.strip().endswith("화"):
                        is_new_section = True
                elif self.mode.get() == "title":
                    if line.split(". ")[0].isdigit():
                        is_new_section = True
                elif self.mode.get() == "scraper":
                    if self.chapter_names and current_chapter_index < len(self.chapter_names):
                        if line.strip() == self.chapter_names[current_chapter_index]:
                            is_new_section = True
                            current_chapter_index += 1

                if is_new_section:
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

            # Write the last section
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