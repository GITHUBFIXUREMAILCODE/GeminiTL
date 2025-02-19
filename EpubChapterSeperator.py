#!/usr/bin/env python3
import os
import zipfile
from lxml import etree
import argparse

# XML namespaces used by EPUB
namespaces = {
    "u": "urn:oasis:names:tc:opendocument:xmlns:container",
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "xhtml": "http://www.w3.org/1999/xhtml"
}

MAX_BYTE_LIMIT = 30000  # Maximum size per extracted text file

def get_opf_path(epub_path):
    """Finds the content.opf path inside the EPUB."""
    with zipfile.ZipFile(epub_path, "r") as z:
        container_xml = z.read("META-INF/container.xml")
        container_tree = etree.fromstring(container_xml)
        rootfile_elem = container_tree.xpath("/u:container/u:rootfiles/u:rootfile",
                                               namespaces=namespaces)[0]
        return rootfile_elem.get("full-path")

def extract_images(epub_path, opf_path, manifest_items, images_output_dir):
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
                    print(f"[WARNING] Could not find image: {in_zip_path}")
                    continue
                local_image_path = os.path.join(images_output_dir, basename)
                with open(local_image_path, "wb") as f:
                    f.write(image_data)
                image_map[basename] = local_image_path
                print(f"[DEBUG] Extracted image: {basename}")

    return image_map

def extract_text_with_placeholders(elem):
    """
    Recursively extracts text from the given element while inserting
    image placeholders at the location where <img> or SVG-based image elements occur.
    """
    parts = []
    if elem.text:
        parts.append(elem.text)
    for child in elem:
        # Check if the element is an image element using its tag name regardless of namespace.
        if etree.QName(child).localname == "img":
            src = child.get("src")
            if src:
                basename = os.path.basename(src)
                parts.append(f'<image src="{basename}" alt="Embedded Image"/>')
        # If it's an SVG element, look inside for image references.
        elif etree.QName(child).localname == "svg":
            svg_imgs = child.xpath(".//*[local-name()='image']")
            for simg in svg_imgs:
                href = simg.get("{http://www.w3.org/1999/xlink}href") or simg.get("href")
                if href:
                    basename = os.path.basename(href)
                    parts.append(f'<image src="{basename}" alt="Embedded SVG Image"/>')
        else:
            # Recurse into the child element.
            parts.append(extract_text_with_placeholders(child))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)

def split_text_by_bytes(text, max_bytes):
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

def extract_chapters(epub_path, opf_path, manifest_items, spine_ids, image_map, output_dir, max_bytes=MAX_BYTE_LIMIT):
    """Extracts XHTML chapters and inserts image placeholders in document order."""
    os.makedirs(output_dir, exist_ok=True)

    # Map spine IDs to manifest items
    id_to_item = {item["id"]: item for item in manifest_items}
    spine_order = [id_to_item[idref] for idref in spine_ids if idref in id_to_item]

    print("\n[DEBUG] EPUB Spine Reading Order:")
    for item in spine_order:
        print(f"  -> {item['href']}")

    with zipfile.ZipFile(epub_path, "r") as z:
        root_dir = os.path.dirname(opf_path)
        for i, item in enumerate(spine_order, start=1):
            in_zip_path = os.path.join(root_dir, item["href"]).replace("\\", "/")
            print(f"\n[DEBUG] Processing: {item['href']}")

            try:
                doc_data = z.read(in_zip_path)
            except KeyError:
                print(f"[WARNING] Missing XHTML file: {in_zip_path}")
                continue

            try:
                doc_tree = etree.fromstring(doc_data)
            except etree.XMLSyntaxError as e:
                print(f"[ERROR] Could not parse {in_zip_path}: {e}")
                continue

            # Try to locate the <body> element.
            body_elem = doc_tree.find(".//xhtml:body", namespaces=namespaces)
            if body_elem is not None:
                extracted_text = extract_text_with_placeholders(body_elem).strip()
            else:
                extracted_text = ""

            # Use a robust check to see if there are any image (or svg) elements anywhere in the document.
            images_found = doc_tree.xpath("//*[local-name()='img'] | //*[local-name()='svg']")
            if not extracted_text and images_found:
                extracted_text = "[IMAGE ONLY CHAPTER]"

            # Only skip the chapter if there is no text and no images.
            if not extracted_text:
                print(f"[DEBUG] Skipping empty chapter: {item['href']}")
                continue

            byte_size = len(extracted_text.encode("utf-8"))
            print(f"[DEBUG] Chapter {i} extracted, size: {byte_size} bytes")

            # Add a filename suffix if images are present.
            has_images = bool(images_found)
            image_suffix = " - image" if has_images else ""
            chapter_filename = f"chapter_{i:02d}{image_suffix}.txt"
            file_path = os.path.join(output_dir, chapter_filename)

            if byte_size > max_bytes:
                parts = split_text_by_bytes(extracted_text, max_bytes)
                for j, part in enumerate(parts, 1):
                    part_filename = f"chapter_{i:02d}_part{j}{image_suffix}.txt"
                    part_path = os.path.join(output_dir, part_filename)
                    with open(part_path, "w", encoding="utf-8") as out_f:
                        out_f.write(part)
                    print(f"[DEBUG] Wrote {part_filename} ({len(part.encode('utf-8'))} bytes)")
            else:
                with open(file_path, "w", encoding="utf-8") as out_f:
                    out_f.write(extracted_text)
                print(f"[DEBUG] Wrote {chapter_filename} ({byte_size} bytes)")

def main(epub_path, output_dir, max_bytes=MAX_BYTE_LIMIT):
    """Main function to extract images and text from EPUB."""
    if not os.path.exists(epub_path):
        print(f"[ERROR] File not found: {epub_path}")
        return

    os.makedirs(output_dir, exist_ok=True)

    opf_path = get_opf_path(epub_path)
    print("[INFO] OPF path:", opf_path)

    with zipfile.ZipFile(epub_path, "r") as z:
        opf_content = z.read(opf_path)
    opf_tree = etree.fromstring(opf_content)

    manifest_items = [
        {
            "id": elem.get("id"),
            "href": elem.get("href"),
            "media_type": elem.get("media-type"),
        }
        for elem in opf_tree.xpath("//opf:manifest/opf:item", namespaces=namespaces)
    ]

    spine_ids = [spine.get("idref") for spine in opf_tree.xpath("//opf:spine/opf:itemref", namespaces=namespaces)]

    images_output_dir = os.path.join(output_dir, "images")
    image_map = extract_images(epub_path, opf_path, manifest_items, images_output_dir)

    extract_chapters(epub_path, opf_path, manifest_items, spine_ids, image_map, output_dir, max_bytes)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract EPUB images & text with placeholders.")
    parser.add_argument("epub_path", help="Path to .epub file")
    parser.add_argument("output_dir", help="Output directory for extracted files")
    parser.add_argument("--max-bytes", type=int, default=30000, help="Max file size in bytes before splitting")
    args = parser.parse_args()

    main(args.epub_path, args.output_dir, max_bytes=args.max_bytes)
