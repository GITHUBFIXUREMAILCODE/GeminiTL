import os

def is_valid_part(filename):
    """Return True if the file is not a part or is part_1."""
    if "_part_" in filename:
        return filename.endswith("_part_1.txt")
    return filename.endswith(".txt")

def get_chapter_title(filepath):
    """Reads the first line of a file, stripping newline characters."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.readline().strip()

def prepend_title_if_missing(title, filepath):
    """Prepend the title to the file if it's not already at the top."""
    with open(filepath, "r+", encoding="utf-8") as f:
        content = f.read()
        if not content.startswith(title):
            f.seek(0, 0)
            f.write(f"{title}\n\n{content}")

def process_chapter_titles(output_dir, proofread_dir):
    """Main routine to propagate chapter titles from output to proofread_ai."""
    for filename in os.listdir(output_dir):
        if not filename.endswith(".txt") or not is_valid_part(filename):
            continue

        output_path = os.path.join(output_dir, filename)
        proofread_path = os.path.join(proofread_dir, filename)

        if not os.path.exists(proofread_path):
            continue  # Skip if the proofread file doesn't exist

        chapter_title = get_chapter_title(output_path)
        prepend_title_if_missing(chapter_title, proofread_path)

if __name__ == "__main__":
    # Determine base script folder
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

    OUTPUT_DIR = os.path.join(BASE_DIR, "output")
    PROOFREAD_DIR = os.path.join(BASE_DIR, "output", "proofed_ai")

    process_chapter_titles(OUTPUT_DIR, PROOFREAD_DIR)
