#!/usr/bin/env python3
import os
import argparse

def split_text_by_bytes(text, max_bytes=20000):
    """
    Splits text into chunks each under max_bytes while ensuring splits happen at line boundaries.
    """
    parts = []
    current_text = ""
    current_size = 0
    lines = text.split("\n")  # Split by single line breaks

    for line in lines:
        line = line.strip()
        if not line:
            continue  # Skip empty lines

        # Check the size of the new chunk after adding the line
        candidate = f"{current_text}\n{line}" if current_text else line
        candidate_size = len(candidate.encode("utf-8"))

        if candidate_size > max_bytes:
            # Save the current chunk and start a new one
            if current_text:
                parts.append(current_text.strip())
            current_text = line  # Start new part with the current oversized line
            current_size = len(line.encode("utf-8"))
        else:
            current_text = candidate
            current_size = candidate_size

    # Save any remaining text
    if current_text.strip():
        parts.append(current_text.strip())

    return parts

def split_large_files(input_folder, max_bytes=30000):
    """
    Processes all .txt files in input_folder, splitting them into parts if they exceed max_bytes.
    The original file is deleted, and split parts are saved with " - part #" appended.
    """
    for filename in os.listdir(input_folder):
        if filename.lower().endswith(".txt"):
            file_path = os.path.join(input_folder, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            byte_size = len(content.encode("utf-8"))
            if byte_size > max_bytes:
                print(f"[INFO] Splitting file: {filename} (Size: {byte_size} bytes)")
                parts = split_text_by_bytes(content, max_bytes)
                base, ext = os.path.splitext(filename)
                for i, part in enumerate(parts, start=1):
                    new_filename = f"{base} - part {i}{ext}"
                    new_file_path = os.path.join(input_folder, new_filename)
                    with open(new_file_path, "w", encoding="utf-8") as f:
                        f.write(part)
                    print(f"[INFO] Created: {new_filename} (Size: {len(part.encode('utf-8'))} bytes)")
                os.remove(file_path)
                print(f"[INFO] Original file '{filename}' removed after splitting.")
            else:
                print(f"[INFO] File '{filename}' does not exceed {max_bytes} bytes; no splitting needed.")

def main():
    parser = argparse.ArgumentParser(
        description="Split text files in a folder if they exceed a specified byte size."
    )
    parser.add_argument("input_folder", help="Path to the folder containing text files")
    parser.add_argument("--max-bytes", type=int, default=30000,
                        help="Maximum number of bytes per file before splitting (default: 30000)")
    args = parser.parse_args()
    split_large_files(args.input_folder, args.max_bytes)

if __name__ == "__main__":
    main()
