import zipfile
import os
import re
import shutil
import bs4
import tkinter as tk
from tkinter import filedialog
from pathlib import Path

def remove_temp_folder(folder: Path):
    """Removes the entire folder and all its contents."""
    if folder.exists():
        shutil.rmtree(folder)

def extract_epub(epub_path: str, output_folder: Path):
    """Extracts the EPUB contents into the specified directory."""
    with zipfile.ZipFile(epub_path, 'r') as epub:
        epub.extractall(output_folder)
def get_xhtml_files(epub_folder: Path):
    """
    Returns XHTML files in spine order based on the EPUB's content.opf file.
    """
    content_opf = next(epub_folder.rglob("content.opf"), None)
    if not content_opf:
        raise FileNotFoundError("content.opf not found in EPUB.")

    with open(content_opf, "r", encoding="utf-8") as f:
        soup = bs4.BeautifulSoup(f, "lxml-xml")

    # 1. Build ID-to-href map from <manifest>
    id_href_map = {
        item['id']: item['href']
        for item in soup.find_all("item")
        if item.has_attr('id') and item.has_attr('href') and item['href'].endswith('.xhtml')
    }

    # 2. Build spine order list from <itemref>
    spine_ids = [itemref['idref'] for itemref in soup.find_all("itemref") if itemref.has_attr('idref')]

    # 3. Resolve full paths based on manifest and spine order
    opf_base = content_opf.parent
    ordered_paths = []
    for item_id in spine_ids:
        href = id_href_map.get(item_id)
        if href:
            full_path = (opf_base / href).resolve()
            if full_path.exists():
                ordered_paths.append(full_path)

    return ordered_paths

def clean_html(content: str) -> str:
    """
    Cleans up the extracted XHTML content for WordPress compatibility.
    - Parses with "lxml-xml" to avoid XML-as-HTML warnings.
    - Removes script, style, meta, link tags.
    - Converts all headings (h1..h6) to h2.
    - Returns the <body> content or entire soup if <body> not found.
    """
    soup = bs4.BeautifulSoup(content, features="lxml-xml")
    
    # Remove unwanted tags
    for tag in soup(["script", "style", "meta", "link"]):
        tag.decompose()
    
    # Convert heading tags to <h2>
    for h in soup.find_all(re.compile(r'^h[1-6]$')):
        h.name = "h2"
    
    return str(soup.body) if soup.body else str(soup)

def convert_epub_to_wordpress(epub_path: str, output_file: str):
    """
    Extracts an EPUB file and converts its content to a single HTML file
    intended for WordPress paste/import.
    """
    temp_folder = Path("temp_epub_extracted")

    # 1. Remove any existing temp folder
    remove_temp_folder(temp_folder)
    # 2. Create a clean temp folder
    temp_folder.mkdir(parents=True, exist_ok=True)

    # 3. Extract EPUB
    extract_epub(epub_path, temp_folder)

    # 4. Gather and sort all .xhtml files
    xhtml_files = get_xhtml_files(temp_folder)

    # 5. Clean and combine HTML content
    html_output = []
    for file in xhtml_files:
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
        cleaned_html = clean_html(content)
        html_output.append(cleaned_html)

    combined_html = "\n\n".join(html_output)

    # 6. Write combined HTML to output
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(combined_html)
    
    print(f"HTML output saved to {output_file}")

def select_files():
    """
    GUI routine to select an EPUB file, then an output file location,
    and execute the conversion.
    """
    root = tk.Tk()
    root.withdraw()

    # Select EPUB
    epub_file = filedialog.askopenfilename(
        title="Select EPUB File",
        filetypes=[("EPUB Files", "*.epub")]
    )
    if not epub_file:
        print("No file selected.")
        return
    
    # Choose output HTML location
    output_file = filedialog.asksaveasfilename(
        title="Save HTML Output As",
        defaultextension=".html",
        filetypes=[("HTML Files", "*.html")]
    )
    if not output_file:
        print("No output location selected.")
        return
    
    # Run the conversion
    convert_epub_to_wordpress(epub_file, output_file)

if __name__ == "__main__":
    select_files()
