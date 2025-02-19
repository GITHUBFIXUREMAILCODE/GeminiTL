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

def get_opf_path(epub_path):
    """Return the 'full-path' to the OPF from META-INF/container.xml."""
    with zipfile.ZipFile(epub_path, "r") as z:
        container_xml = z.read("META-INF/container.xml")
        container_tree = etree.fromstring(container_xml)
        rootfile_elem = container_tree.xpath("/u:container/u:rootfiles/u:rootfile",
                                             namespaces=namespaces)[0]
        opf_path = rootfile_elem.get("full-path")
        return opf_path

def parse_manifest(epub_path, opf_path):
    """Parses the OPF file to extract manifest items, spine order, and cover image."""
    with zipfile.ZipFile(epub_path, "r") as z:
        opf_content = z.read(opf_path)
    opf_tree = etree.fromstring(opf_content)

    item_elems = opf_tree.xpath("//opf:manifest/opf:item", namespaces=namespaces)
    manifest_items = []
    for elem in item_elems:
        manifest_items.append({
            "id": elem.get("id"),
            "href": elem.get("href"),
            "media_type": elem.get("media-type"),
            "properties": elem.get("properties", ""),  # e.g. "cover-image"
        })

    spine_elems = opf_tree.xpath("//opf:spine/opf:itemref", namespaces=namespaces)
    spine_ids = [spine.get("idref") for spine in spine_elems]

    cover_id = None
    meta_cover = opf_tree.xpath("//opf:metadata/opf:meta[@name='cover']", namespaces=namespaces)
    if meta_cover:
        cover_id = meta_cover[0].get("content")

    if not cover_id:
        cover_items = [it for it in manifest_items if "cover-image" in it["properties"]]
        if cover_items:
            cover_id = cover_items[0]["id"]

    return manifest_items, spine_ids, cover_id

def extract_images(epub_path, opf_path, manifest_items, images_output_dir):
    """Extract images from EPUB and save them locally."""
    os.makedirs(images_output_dir, exist_ok=True)
    image_map = {}

    with zipfile.ZipFile(epub_path, "r") as z:
        root_dir = os.path.dirname(opf_path)
        for item in manifest_items:
            if item["media_type"] and item["media_type"].startswith("image"):
                in_zip_path = os.path.join(root_dir, item["href"]).replace("\\", "/")
                basename = os.path.basename(item["href"])
                print(f"[DEBUG] Extracting image: {basename}")
                image_data = z.read(in_zip_path)
                local_image_path = os.path.join(images_output_dir, basename)
                with open(local_image_path, "wb") as f:
                    f.write(image_data)
                image_map[basename] = local_image_path

    return image_map

def extract_documents_with_placeholders(epub_path, opf_path, manifest_items, spine_ids, image_map, output_dir):
    """Extracts XHTML documents, replacing image references with placeholders."""
    os.makedirs(output_dir, exist_ok=True)

    id_to_item = {item["id"]: item for item in manifest_items}
    spine_order = [id_to_item[idref] for idref in spine_ids if idref in id_to_item]
    non_spine = [item for item in manifest_items if item["id"] not in spine_ids and "xhtml" in item["media_type"]]

    doc_items = spine_order + non_spine

    print("\n[DEBUG] Spine Reading Order:")
    for item in spine_order:
        print(f"  -> {item['href']}")

    with zipfile.ZipFile(epub_path, "r") as z:
        root_dir = os.path.dirname(opf_path)

        for item in doc_items:
            if not item["media_type"] or "xhtml" not in item["media_type"]:
                continue

            in_zip_path = os.path.join(root_dir, item["href"]).replace("\\", "/")
            print(f"\n[DEBUG] Processing XHTML: {item['href']}")  # <<<< New Debugging
            try:
                doc_data = z.read(in_zip_path)
            except KeyError:
                print(f"[WARNING] Missing file: {in_zip_path}")
                continue

            doc_tree = etree.fromstring(doc_data)

            content_list = []
            has_images = False

            # Log detected images
            img_elems = doc_tree.xpath("//xhtml:img", namespaces=namespaces)
            svg_image_elems = doc_tree.xpath("//xhtml:svg//xhtml:image | //xhtml:svg//image", namespaces=namespaces)

            if img_elems or svg_image_elems:
                print(f"[DEBUG] Found {len(img_elems)} <img> and {len(svg_image_elems)} <svg><image> elements")

            # Process <img> tags
            for img in img_elems:
                src = img.get("src")
                if src:
                    has_images = True
                    basename = os.path.basename(src)
                    print(f"[DEBUG] Image detected in XHTML: {basename}")
                    if basename in image_map:
                        content_list.append(f'<image src="{basename}" alt="Embedded Image"/>')
                    else:
                        content_list.append(f'<image src="MISSING_IMAGE_{basename}" alt="Missing Image"/>')

            # Process <svg><image> elements
            for simg in svg_image_elems:
                href = simg.get("{http://www.w3.org/1999/xlink}href") or simg.get("href")
                if href:
                    has_images = True
                    basename = os.path.basename(href)
                    print(f"[DEBUG] SVG Image detected: {basename}")
                    if basename in image_map:
                        content_list.append(f'<image src="{basename}" alt="Embedded SVG Image"/>')
                    else:
                        content_list.append(f'<image src="MISSING_SVG_IMAGE_{basename}" alt="Missing SVG Image"/>')

            combined_text = "\n\n".join(content_list).strip()
            if not combined_text:
                continue

            filename = f"{os.path.splitext(os.path.basename(item['href']))[0]}.txt"
            file_path = os.path.join(output_dir, filename)

            with open(file_path, "w", encoding="utf-8") as out_f:
                out_f.write(combined_text)

            print(f"[DEBUG] Wrote extracted chapter: {filename}")

def main(epub_path, output_dir):
    """Main function for EPUB extraction."""
    if not os.path.exists(epub_path):
        print(f"[ERROR] File not found: {epub_path}")
        return

    os.makedirs(output_dir, exist_ok=True)

    opf_path = get_opf_path(epub_path)
    print("[INFO] OPF path:", opf_path)

    manifest_items, spine_ids, cover_id = parse_manifest(epub_path, opf_path)
    images_output_dir = os.path.join(output_dir, "images")
    image_map = extract_images(epub_path, opf_path, manifest_items, images_output_dir)

    extract_documents_with_placeholders(epub_path, opf_path, manifest_items, spine_ids, image_map, output_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract EPUB images & text with placeholders.")
    parser.add_argument("epub_path", help="Path to .epub file")
    parser.add_argument("output_dir", help="Output directory for extracted files")
    args = parser.parse_args()

    main(args.epub_path, args.output_dir)
