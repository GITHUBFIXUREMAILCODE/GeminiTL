import os
import zipfile
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup  # Import BeautifulSoup for HTML parsing
from pathlib import Path
import shutil
from tkinter import Tk, filedialog


def select_epub_file():
    """Open a file dialog to select the EPUB file."""
    root = Tk()
    root.withdraw()  # Hide the main tkinter window
    epub_file = filedialog.askopenfilename(
        title="Select an EPUB file",
        filetypes=[("EPUB files", "*.epub")]
    )
    if not epub_file:
        raise FileNotFoundError("No EPUB file selected.")
    return epub_file


def extract_epub(epub_path, extract_to):
    """Extracts the EPUB file to a directory."""
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print(f"EPUB extracted to {extract_to}")


def locate_content_opf(epub_dir):
    """Locates the content.opf file using container.xml."""
    container_path = os.path.join(epub_dir, "META-INF", "container.xml")
    if not os.path.exists(container_path):
        raise FileNotFoundError("container.xml not found in META-INF.")

    # Parse container.xml
    tree = ET.parse(container_path)
    root = tree.getroot()
    namespace = {'ns': 'urn:oasis:names:tc:opendocument:xmlns:container'}
    rootfile = root.find("ns:rootfiles/ns:rootfile", namespace)

    if rootfile is not None:
        opf_path = rootfile.attrib['full-path']
        return os.path.join(epub_dir, opf_path)
    else:
        raise FileNotFoundError("content.opf path not found in container.xml.")


def parse_content_opf(opf_path):
    """Parses the content.opf file to extract the chapter information."""
    tree = ET.parse(opf_path)
    root = tree.getroot()
    namespace = {'ns': 'http://www.idpf.org/2007/opf'}

    # Extract manifest (mapping of ids to hrefs)
    manifest = {}
    for item in root.find('ns:manifest', namespace):
        manifest[item.attrib['id']] = item.attrib['href']

    # Extract spine (order of chapters)
    spine = []
    for itemref in root.find('ns:spine', namespace):
        spine.append(itemref.attrib['idref'])

    base_path = os.path.dirname(opf_path)
    return manifest, spine, base_path


def export_chapters(epub_dir, output_dir, manifest, spine, base_path):
    """Extracts and saves individual chapters as formatted plain text files."""
    os.makedirs(output_dir, exist_ok=True)
    
    for i, idref in enumerate(spine):
        chapter_file = manifest[idref]
        chapter_path = os.path.join(base_path, chapter_file)

        if os.path.exists(chapter_path):
            with open(chapter_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Use BeautifulSoup to parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Convert <br> to newline so line breaks aren't lost
            for br in soup.find_all("br"):
                br.replace_with("\n")
            
            # Gather paragraphs from the HTML
            paragraphs = soup.find_all("p")
            formatted_paragraphs = []
            
            for para in paragraphs:
                text = para.get_text().strip()
                if text:
                    # Indent each paragraph by 4 spaces (adjust as desired)
                    text = "    " + text  
                    formatted_paragraphs.append(text)

            # Join paragraphs with a blank line in between
            plain_text = "\n\n".join(formatted_paragraphs)

            # Write to .txt file
            chapter_output_path = os.path.join(output_dir, f"chapter_{i + 1}.txt")
            with open(chapter_output_path, 'w', encoding='utf-8') as f:
                f.write(plain_text)
            print(f"Exported plain text of {chapter_file} to {chapter_output_path}")
        else:
            print(f"Warning: {chapter_file} not found.")


def split_epub(output_dir):
    """Main function to split EPUB into chapters."""
    epub_path = select_epub_file()
    extract_dir = os.path.join(output_dir, "extracted")
    chapters_dir = os.path.join(output_dir, "chapters")

    # Step 1: Extract EPUB
    extract_epub(epub_path, extract_dir)

    # Step 2: Locate and parse content.opf
    opf_path = locate_content_opf(extract_dir)
    manifest, spine, base_path = parse_content_opf(opf_path)

    # Step 3: Export chapters
    export_chapters(extract_dir, chapters_dir, manifest, spine, base_path)

    # Cleanup extracted files
    shutil.rmtree(extract_dir)
    print(f"Chapters exported to {chapters_dir}")


# Example Usage
if __name__ == "__main__":
    output_folder = "input"
    split_epub(output_folder)
