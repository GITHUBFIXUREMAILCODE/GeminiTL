import os
import zipfile
import re
from pathlib import Path
import shutil
import html

def escape_special_chars(text):
    """Escape special characters to make the text XHTML-compliant."""
    return html.escape(text)

def natural_key(file):
    """Sort files in natural order (e.g., Chapter 2 before Chapter 10)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(file))]

def create_epub(output_dir, epub_name, image_dir=None):
    epub_dir = Path(output_dir)
    image_dir = Path(image_dir) if image_dir else None

    if not epub_dir.exists():
        raise FileNotFoundError(f"The output directory '{output_dir}' does not exist.")

    # If user provided an image_dir path but it doesn't exist, just warn and skip images
    if image_dir and not image_dir.exists():
        print(f"[WARNING] The image directory '{image_dir}' does not exist. Images will be skipped.")
        image_dir = None

    temp_dir = epub_dir / "temp_epub"
    os.makedirs(temp_dir / "META-INF", exist_ok=True)
    os.makedirs(temp_dir / "EPUB", exist_ok=True)

    mimetype_path = temp_dir / "mimetype"
    with open(mimetype_path, "w", encoding="utf-8") as f:
        f.write("application/epub+zip")

    container_path = temp_dir / "META-INF" / "container.xml"
    with open(container_path, "w", encoding="utf-8") as f:
        f.write("""<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>""")

    text_files = sorted(epub_dir.glob("*.txt"), key=natural_key)
    if not text_files:
        raise FileNotFoundError("No .txt files found in the output directory.")

    manifest_items = ['<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>']
    spine_items = []
    toc_items = []

    # Track all images found in the directory and which ones are used
    all_image_files = set()
    used_image_files = set()

    # Regex patterns
    image_placeholder_pattern = re.compile(r'\[IMAGE:.*?\]', re.IGNORECASE)
    newstyle_pattern = re.compile(
        r'<image\s+[^>]*src\s*=\s*"([^"]+)"(?:[^>]*alt\s*=\s*"([^"]*)")?[^>]*>',
        re.IGNORECASE
    )

    def replace_newstyle_placeholder(match):
        img_name = match.group(1).strip()
        alt_text = match.group(2) if match.group(2) else "Embedded Image"
        if image_dir:
            used_image_files.add(img_name)
            alt_text_escaped = escape_special_chars(alt_text)
            # Remove any existing 'images/' prefix to avoid duplication
            img_name = img_name.replace('images/', '')
            return f'<img src="images/{img_name}" alt="{alt_text_escaped}"/>'
        else:
            return ""

    # First pass: process all chapters and track used images
    for i, text_file in enumerate(text_files, start=1):
        chapter_id = f"chapter{i}"
        xhtml_filename = f"{chapter_id}.xhtml"
        xhtml_path = temp_dir / "EPUB" / xhtml_filename

        with open(text_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Remove all [IMAGE: *] placeholders if no image_dir is provided
        if not image_dir:
            content = re.sub(image_placeholder_pattern, '', content)

        # Replace <image> placeholders with proper <img> tags
        content = re.sub(newstyle_pattern, replace_newstyle_placeholder, content)

        # Fix any remaining image paths that don't have the images/ prefix
        content = re.sub(
            r'<img\s+[^>]*src\s*=\s*"(?!images/)([^"]+)"',
            lambda m: m.group(0).replace(f'src="{m.group(1)}"', f'src="images/{m.group(1)}"'),
            content
        )

        lines = content.splitlines()
        xhtml_body = []
        for line in lines:
            if "<img " in line:
                xhtml_body.append(f"<p>{line}</p>")
            else:
                xhtml_body.append(f"<p>{escape_special_chars(line)}</p>")

        xhtml_body_str = "\n".join(xhtml_body)

        xhtml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"
    "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>Chapter {i}</title>
  </head>
  <body>
    <h1>Chapter {i}</h1>
    {xhtml_body_str}
  </body>
</html>
"""
        with open(xhtml_path, "w", encoding="utf-8") as f:
            f.write(xhtml_content)

        manifest_items.append(f'<item id="{chapter_id}" href="{xhtml_filename}" media-type="application/xhtml+xml"/>')
        spine_items.append(f'<itemref idref="{chapter_id}" />')
        toc_items.append(f'<navPoint id="{chapter_id}" playOrder="{i}"><navLabel><text>Chapter {i}</text></navLabel><content src="{xhtml_filename}"/></navPoint>')

    # Get all available images if image_dir exists
    if image_dir:
        all_image_files = {f.name for f in image_dir.glob("*") if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".svg"}}
        unused_images = all_image_files - used_image_files

        # Create Illustrations chapter if there are unused images
        if unused_images:
            illustrations_id = "illustrations"
            illustrations_filename = f"{illustrations_id}.xhtml"
            illustrations_path = temp_dir / "EPUB" / illustrations_filename

            # Create HTML content for illustrations
            illustrations_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"
    "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>Illustrations</title>
  </head>
  <body>
    <h1>Illustrations</h1>
"""
            for img_name in sorted(unused_images):
                illustrations_content += f'    <p><img src="images/{img_name}" alt="Illustration"/></p>\n'
            illustrations_content += "  </body>\n</html>"

            with open(illustrations_path, "w", encoding="utf-8") as f:
                f.write(illustrations_content)

            # Add to manifest, spine, and TOC
            manifest_items.append(f'<item id="{illustrations_id}" href="{illustrations_filename}" media-type="application/xhtml+xml"/>')
            spine_items.append(f'<itemref idref="{illustrations_id}" />')
            toc_items.append(f'<navPoint id="{illustrations_id}" playOrder="{len(text_files) + 1}"><navLabel><text>Illustrations</text></navLabel><content src="{illustrations_filename}"/></navPoint>')

    # Copy all images to EPUB
    if image_dir and (used_image_files or unused_images):
        os.makedirs(temp_dir / "EPUB/images", exist_ok=True)
        for img_name in used_image_files | unused_images:
            src_img_path = image_dir / img_name
            if not src_img_path.exists():
                print(f"[WARNING] Missing image: {img_name}")
                continue

            dest_img_path = temp_dir / "EPUB/images" / img_name
            shutil.copy(src_img_path, dest_img_path)

            ext = src_img_path.suffix.lower()
            mime = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".svg": "image/svg+xml"
            }.get(ext, "application/octet-stream")

            manifest_items.append(f'<item id="{img_name}" href="images/{img_name}" media-type="{mime}"/>')

    epub_title = Path(epub_name).stem  # Extract the filename without the .epub extension

    content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>{escape_special_chars(epub_title)}</dc:title>
    <dc:language>en</dc:language>
    <dc:identifier id="bookid">urn:uuid:12345</dc:identifier>
  </metadata>
  <manifest>
    {'\n    '.join(manifest_items)}
  </manifest>
  <spine toc="ncx">
    {'\n    '.join(spine_items)}
  </spine>
</package>"""

    with open(temp_dir / "EPUB/content.opf", "w", encoding="utf-8") as f:
        f.write(content_opf)

    with open(temp_dir / "EPUB/toc.ncx", "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <navMap>
    {'\n    '.join(toc_items)}
  </navMap>
</ncx>""")

    epub_path = epub_dir / epub_name
    with zipfile.ZipFile(epub_path, "w") as epub:
        # First add mimetype file uncompressed
        epub.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)
        
        # Then add all other files
        for path in temp_dir.rglob("*"):
            if path.name != "mimetype":  # Skip mimetype as it's already added
                epub.write(path, path.relative_to(temp_dir))

    shutil.rmtree(temp_dir)
    print(f"EPUB created: {epub_path}")

if __name__ == "__main__":
    output_folder = input("Enter the path to the output folder: ").strip()
    image_folder = input("Enter the path to the image folder (Press Enter to skip): ").strip() or None
    create_epub(output_folder, "generated.epub", image_folder)
