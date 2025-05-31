import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox

def extract_img_tags(html):
    return list(re.finditer(r'<img[^>]+>', html, flags=re.IGNORECASE))

def replace_imgs_by_position(original_html, new_html):
    original_matches = extract_img_tags(original_html)
    new_matches = extract_img_tags(new_html)

    min_count = min(len(original_matches), len(new_matches))
    if min_count == 0:
        return original_html  # No replacements to make

    result = []
    last_index = 0

    for i in range(min_count):
        orig = original_matches[i]
        start, end = orig.span()
        result.append(original_html[last_index:start])
        result.append(new_matches[i].group(0))
        last_index = end

    # Add the remaining part of original HTML
    result.append(original_html[last_index:])
    return ''.join(result)

def main():
    root = tk.Tk()
    root.withdraw()

    # Select Original HTML
    original_path = filedialog.askopenfilename(
        title="Select Original HTML file (to modify)",
        filetypes=[("HTML Files", "*.html"), ("All Files", "*.*")]
    )
    if not original_path:
        messagebox.showinfo("Cancelled", "No HTML file selected.")
        return

    # Select New HTML with replacement <img> tags
    new_path = filedialog.askopenfilename(
        title="Select HTML/Text file with new <img> tags (same structure)",
        filetypes=[("HTML Files", "*.html"), ("Text Files", "*.txt"), ("All Files", "*.*")]
    )
    if not new_path:
        messagebox.showinfo("Cancelled", "No second HTML/text file selected.")
        return

    with open(original_path, "r", encoding="utf-8") as f:
        original_html = f.read()

    with open(new_path, "r", encoding="utf-8") as f:
        new_html = f.read()

    # Do the replacements
    updated_html = replace_imgs_by_position(original_html, new_html)

    output_path = os.path.join(os.path.dirname(original_path), "output_replaced.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(updated_html)

    messagebox.showinfo("Done", f"<img> tags replaced by position.\nSaved as: {output_path}")

if __name__ == "__main__":
    main()
