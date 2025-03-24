# proofing.py

import os
import unicodedata
from .image_ocr import replace_image_tags_with_ocr
from .translator import TLer

def contains_non_english_letters(text):
    """
    Return True if 'text' contains any letters that are not 'LATIN' in Unicode,
    which means they are likely non-English letters. Punctuation/symbols are ignored.
    """
    for char in text:
        # Only check letters (ignore punctuation, digits, etc.)
        if char.isalpha():
            # Get the Unicode name (e.g., 'LATIN SMALL LETTER A')
            name = unicodedata.name(char, "")
            if "LATIN" not in name:
                return True
    return False

def verify_translations(log_message, input_dir, output_dir, error_log_path, image_dir):
    """
    3rd pass: Scan output for non-English characters (excluding punctuation).
    If found, re-translate using the original text up to 3 times.
    If still failing after 3 tries, log the filename to error_log_path.

    Params:
    -------
    log_message     : function for logging
    input_dir       : path to the input/ directory
    output_dir      : path to the output/ directory
    error_log_path  : full path to the 'error.txt' file
    image_dir       : path to the input/images/ directory used for OCR
    """

    # Iterate over the translated files in output/
    for fname in sorted(os.listdir(output_dir)):
        # We only want to process files that match "translated_*.txt"
        if not fname.startswith("translated_") or not fname.endswith(".txt"):
            continue

        out_file_path = os.path.join(output_dir, fname)
        in_file_path = os.path.join(input_dir, fname.replace("translated_", ""))

        try:
            with open(out_file_path, "r", encoding="utf-8") as f_out:
                content = f_out.read()

            # Check if content contains any non-English letters
            if contains_non_english_letters(content):
                log_message(f"[VERIFY] {fname} seems to have non-English letters. Retrying translation...")

                # Try re-translation up to 3 times
                for attempt in range(3):
                    # Re-load original input text
                    with open(in_file_path, "r", encoding="utf-8") as f_in:
                        original_content = f_in.read()

                    # Replace <image> tags with OCR text if needed
                    updated_text = replace_image_tags_with_ocr(original_content, image_dir, log_message)

                    # Attempt translation
                    retranslated = TLer(updated_text, log_message)

                    # If the new translation has no non-English letters, we're good
                    if retranslated and not contains_non_english_letters(retranslated):
                        with open(out_file_path, "w", encoding="utf-8") as f_out:
                            f_out.write(retranslated)
                        log_message(f"[FIXED] {fname} passed on attempt {attempt + 1}")
                        break
                else:
                    # If we never broke out from the for-loop,
                    # we failed all 3 attempts => Log the file in 'error.txt'
                    with open(error_log_path, "a", encoding="utf-8") as f_err:
                        f_err.write(fname + "\n")
                    log_message(f"[ERROR] {fname} still failed after 3 attempts.")

        except Exception as e:
            log_message(f"[ERROR verifying {fname}]: {e}")
