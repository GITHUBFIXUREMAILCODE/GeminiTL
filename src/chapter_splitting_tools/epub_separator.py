"""
EPUB Separator module for the novel translation tool.

This module provides functionality for:
- Extracting text and images from EPUB files
- Splitting large chapters into smaller parts
- Preserving image placeholders in the extracted text
"""

import os
import zipfile
from lxml import etree
from lxml import html
import argparse
from pathlib import Path

class EPUBSeparator:
    """
    Handles extraction and separation of EPUB content.
    
    This class provides functionality for:
    - Extracting text and images from EPUB files
    - Splitting large chapters into smaller parts
    - Preserving image placeholders in the extracted text
    """
    
    # XML namespaces used by EPUB
    namespaces = {
        "u": "urn:oasis:names:tc:opendocument:xmlns:container",
        "opf": "http://www.idpf.org/2007/opf",
        "dc": "http://purl.org/dc/elements/1.1/",
        "xhtml": "http://www.w3.org/1999/xhtml"
    }

    def __init__(self, log_function=None, max_byte_limit=20000):
        """
        Initialize the EPUBSeparator.
        
        Args:
            log_function: Optional function to use for logging (defaults to print)
            max_byte_limit: Maximum size per extracted text file in bytes
        """
        self.log_function = log_function or print
        self.max_byte_limit = max_byte_limit

    def get_opf_path(self, epub_path):
        """Finds the content.opf path inside the EPUB."""
        with zipfile.ZipFile(epub_path, "r") as z:
            container_xml = z.read("META-INF/container.xml")
            container_tree = etree.fromstring(container_xml)
            rootfile_elem = container_tree.xpath("/u:container/u:rootfiles/u:rootfile",
                                                namespaces=self.namespaces)[0]
            return rootfile_elem.get("full-path")

    def extract_images(self, epub_path, opf_path, manifest_items, images_output_dir):
        """Extracts all images from the EPUB and saves them locally."""
        os.makedirs(images_output_dir, exist_ok=True)
        image_map = {}

        with zipfile.ZipFile(epub_path, "r") as z:
            root_dir = os.path.dirname(opf_path)
            for item in manifest_items:
                if item["media_type"].startswith("image"):
                    in_zip_path = os.path.join(root_dir, item["href"]).replace("\\", "/")
                    basename = os.path.basename(item["href"])
                    try:
                        image_data = z.read(in_zip_path)
                    except KeyError:
                        self.log_function(f"[WARNING] Could not find image: {in_zip_path}")
                        continue
                    local_image_path = os.path.join(images_output_dir, basename)
                    with open(local_image_path, "wb") as f:
                        f.write(image_data)
                    image_map[basename] = local_image_path
                    self.log_function(f"[DEBUG] Extracted image: {basename}")

        return image_map

    def extract_text_with_placeholders(self, elem):
        """
        Extracts text from an XHTML/HTML element, preserving minimal block spacing
        (paragraphs, line breaks) and replacing inline images with placeholders.
        """
        parts = []

        # 1) Grab any text from the element itself (before child elements)
        if elem.text and elem.text.strip():
            parts.append(elem.text.strip())

        # 2) Process each child node in order
        for child in elem:
            # If it's a comment or not an actual element, skip it, but keep trailing text
            if not hasattr(child, "tag") or not isinstance(child.tag, str):
                if child.tail and child.tail.strip():
                    parts.append(child.tail.strip())
                continue

            localname = etree.QName(child).localname.lower()

            if localname == "br":
                # Insert a single newline
                parts.append("\n")
            elif localname in ["p", "div"]:
                # Treat as block-level: insert two newlines, then recurse
                parts.append("\n\n" + self.extract_text_with_placeholders(child))
            elif localname == "img":
                # Inline image placeholder
                src = child.get("src")
                if src:
                    basename = os.path.basename(src)
                    parts.append(f'<<<IMAGE_START>>><image src="{basename}" alt="Embedded Image"/><<<IMAGE_END>>>')
            elif localname == "svg":
                # SVG may contain <image> elements
                svg_imgs = child.xpath(".//*[local-name()='image']")
                for simg in svg_imgs:
                    href = simg.get("{http://www.w3.org/1999/xlink}href") or simg.get("href")
                    if href:
                        basename = os.path.basename(href)
                        parts.append(f'<image src="{basename}" alt="Embedded SVG Image"/>')
            else:
                # For other elements, recurse normally
                parts.append(self.extract_text_with_placeholders(child))

            # 3) Append any tail text (after the child tag)
            if child.tail and child.tail.strip():
                parts.append(child.tail.strip())

        # 4) Join everything with a space—this ensures pieces remain separated
        #    but also preserves the newlines we inserted above.
        return " ".join(parts)

    def split_text_by_bytes(self, text, max_bytes):
        """Splits extracted text into smaller parts if it exceeds max_bytes."""
        parts = []
        current_text = ""
        paragraphs = text.split("\n\n")
        for paragraph in paragraphs:
            candidate = f"{current_text}\n\n{paragraph.strip()}" if current_text else paragraph.strip()
            if len(candidate.encode("utf-8")) > max_bytes:
                if current_text.strip():
                    parts.append(current_text.strip())
                current_text = paragraph.strip()
            else:
                current_text = candidate
        if current_text.strip():
            parts.append(current_text.strip())
        return parts

    def extract_chapters(self, epub_path, opf_path, manifest_items, spine_ids, image_map,
                        output_dir, max_bytes=None):
        """Extracts XHTML/HTML chapters and inserts image placeholders in document order."""
        if max_bytes is None:
            max_bytes = self.max_byte_limit
            
        os.makedirs(output_dir, exist_ok=True)

        # Map spine IDs to manifest items
        id_to_item = {item["id"]: item for item in manifest_items}
        spine_order = [id_to_item[idref] for idref in spine_ids if idref in id_to_item]

        self.log_function("\n[DEBUG] EPUB Spine Reading Order:")
        for item in spine_order:
            self.log_function(f"  -> {item['href']}")

        with zipfile.ZipFile(epub_path, "r") as z:
            root_dir = os.path.dirname(opf_path)
            for i, item in enumerate(spine_order, start=1):
                in_zip_path = os.path.join(root_dir, item["href"]).replace("\\", "/")
                self.log_function(f"\n[DEBUG] Processing: {item['href']}")

                try:
                    doc_data = z.read(in_zip_path)
                except KeyError:
                    self.log_function(f"[WARNING] Missing XHTML file: {in_zip_path}")
                    continue

                try:
                    # Option 2: use lxml.html.fromstring for HTML-like content
                    doc_tree = html.fromstring(doc_data)
                except Exception as e:
                    self.log_function(f"[ERROR] Could not parse {in_zip_path}: {e}")
                    continue

                # Since we're parsing as HTML, look for a <body> without namespace
                body_elem = doc_tree.find(".//body")
                if body_elem is not None:
                    extracted_text = self.extract_text_with_placeholders(body_elem).strip()
                else:
                    extracted_text = ""
                    
                TITLE_DELIMITER_START = "<<<TITLE_START>>>"
                TITLE_DELIMITER_END = "<<<TITLE_END>>>"
                if extracted_text.strip():
                    lines = extracted_text.splitlines()
                    for idx, line in enumerate(lines):
                        if line.strip():  # Find first non-empty line
                            lines[idx] = f"{TITLE_DELIMITER_START}{line.strip()}{TITLE_DELIMITER_END}"
                            break
                    extracted_text = "\n".join(lines)


                # Use a robust check to see if there are any <img> or <svg> anywhere
                images_found = doc_tree.xpath("//*[local-name()='img'] | //*[local-name()='svg']")# If no text was extracted, but raw XHTML has an embedded <image> in SVG, check manually
                if not extracted_text:
                    try:
                        raw_tree = etree.fromstring(doc_data)
                        svg_images = raw_tree.xpath(
                            "//*[local-name()='svg']//*[local-name()='image']"
                        )
                        image_tags = []
                        for im in svg_images:
                            src = (im.get("src") or
                                im.get("{http://www.w3.org/1999/xlink}href") or
                                im.get("href"))
                            if src:
                                basename = os.path.basename(src)
                                image_tags.append(f'<image src="{basename}" alt="Embedded SVG Image"/>')
                        extracted_text = "\n".join(image_tags) if image_tags else "[IMAGE ONLY CHAPTER]"
                    except Exception as e:
                        self.log_function(f"[ERROR] SVG fallback parse failed: {e}")
                        extracted_text = "[IMAGE ONLY CHAPTER]"



                if not extracted_text:
                    self.log_function(f"[DEBUG] Skipping empty chapter: {item['href']}")
                    continue

                byte_size = len(extracted_text.encode("utf-8"))
                self.log_function(f"[DEBUG] Chapter {i} extracted, size: {byte_size} bytes")

                # If chapter text is too large, split into multiple parts
                if byte_size > max_bytes:
                    parts = self.split_text_by_bytes(extracted_text, max_bytes)
                    for j, part in enumerate(parts, 1):
                        part_suffix = " - image" if ("<image" in part or "[IMAGE ONLY CHAPTER]" in part) else ""
                        original_name = os.path.splitext(os.path.basename(item["href"]))[0]
                        part_filename = f"{original_name}_part{j}{part_suffix}.txt"
                        part_path = os.path.join(output_dir, part_filename)
                        with open(part_path, "w", encoding="utf-8") as out_f:
                            out_f.write(part)
                        self.log_function(f"[DEBUG] Wrote {part_filename} ({len(part.encode('utf-8'))} bytes)")
                else:
                    suffix = " - image" if ("<image" in extracted_text or "[IMAGE ONLY CHAPTER]" in extracted_text) else ""
                    # Use original href as the base name, stripping extension and normalizing
                    original_name = os.path.splitext(os.path.basename(item["href"]))[0]
                    chapter_filename = f"{original_name}{suffix}.txt"
                    file_path = os.path.join(output_dir, chapter_filename)
                    with open(file_path, "w", encoding="utf-8") as out_f:
                        out_f.write(extracted_text)
                    self.log_function(f"[DEBUG] Wrote {chapter_filename} ({byte_size} bytes)")


    def separate(self, epub_path, output_dir, max_bytes=None):
        """
        Main method to extract images and text from EPUB.
        
        Args:
            epub_path: Path to the EPUB file
            output_dir: Directory to output extracted files
            max_bytes: Optional maximum file size in bytes before splitting
        """
        if max_bytes is None:
            max_bytes = self.max_byte_limit
            
        if not os.path.exists(epub_path):
            self.log_function(f"[ERROR] File not found: {epub_path}")
            return

        os.makedirs(output_dir, exist_ok=True)

        opf_path = self.get_opf_path(epub_path)
        self.log_function("[DEBUG] Type of opf_path:", type(opf_path), "->", opf_path)

        with zipfile.ZipFile(epub_path, "r") as z:
            opf_content = z.read(opf_path)
            self.log_function("[DEBUG] Type of opf_content:", type(opf_content))
        opf_tree = etree.fromstring(opf_content)
        self.log_function("[DEBUG] Type of opf_tree:", type(opf_tree))
        self.log_function("[DEBUG] Type of opf_tree.xpath:", type(opf_tree.xpath))

        manifest_items = [
            {
                "id": elem.get("id"),
                "href": elem.get("href"),
                "media_type": elem.get("media-type"),
            }
            for elem in opf_tree.xpath("//opf:manifest/opf:item", namespaces=self.namespaces)
        ]

        spine_ids = [spine.get("idref") for spine in opf_tree.xpath("//opf:spine/opf:itemref", namespaces=self.namespaces)]

        images_output_dir = os.path.join(output_dir, "images")
        image_map = self.extract_images(epub_path, opf_path, manifest_items, images_output_dir)

        self.extract_chapters(epub_path, opf_path, manifest_items, spine_ids, image_map, output_dir, max_bytes)

def main():
    """
    Command-line entry point for EPUB separation.
    """
    parser = argparse.ArgumentParser(description="Extract EPUB images & text with placeholders.")
    parser.add_argument("epub_path", help="Path to .epub file")
    parser.add_argument("output_dir", help="Output directory for extracted files")
    parser.add_argument("--max-bytes", type=int, default=20000, help="Max file size in bytes before splitting")
    args = parser.parse_args()

    separator = EPUBSeparator(max_byte_limit=args.max_bytes)
    separator.separate(args.epub_path, args.output_dir)

if __name__ == "__main__":
    main()
