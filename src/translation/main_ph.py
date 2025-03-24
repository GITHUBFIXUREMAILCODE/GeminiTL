import re
import os
from .glossary import build_glossary
from .translator import TLer
from .image_ocr import replace_image_tags_with_ocr
from .proofing import verify_translations

# Ensure input/ and output/ folders exist
script_dir = os.path.dirname(os.path.abspath(__file__))  # This points to src/translation
control_script_dir = os.path.dirname(os.path.dirname(script_dir))  # Move up twice to main dir
input_dir = os.path.join(control_script_dir, "input")   # Points to 'input/' next to ControlScript.py
output_dir = os.path.join(control_script_dir, "output") # Points to 'output/' next to ControlScript.py
os.makedirs(input_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

def is_html_only_image_tag(text):
    """
    Returns True if the text file is JUST a single <image .../> tag
    (ignoring whitespace).
    Example:
      <image src="embed0021_HD.jpg" alt="Embedded SVG Image"/>
    """
    stripped = text.strip()
    return bool(re.match(r'^<image[^>]*\/>\s*$', stripped, flags=re.IGNORECASE))

def build_glossary_in_batches(log_message):
    """
    1st pass: Read text files in batches and build/update the glossary from all chapters.
    No translation happens here.
    """
    text_files = sorted(
        [f for f in os.listdir(input_dir) if f.endswith(".txt")],
        key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else float('inf')
    )

    # Process in batches of 10 files at a time
    for i in range(0, len(text_files), 10):
        batch = text_files[i : i+10]
        log_message(f"\n=== GLOSSARY BUILDING for batch: {batch} ===")

        # Combine the entire text from this batch
        batch_text = ""
        for fname in batch:
            in_path = os.path.join(input_dir, fname)
            try:
                with open(in_path, "r", encoding="utf-8") as f:
                    batch_text += f.read() + "\n"
            except Exception as e:
                log_message(f"[ERROR reading {fname}]: {e}")

        # If there's any text, call build_glossary
        if batch_text.strip():
            log_message("[DEBUG] Calling build_glossary()...")
            glossary_text = build_glossary(batch_text, log_message)
            if glossary_text:
                log_message(f"[DEBUG] Glossary updated:\n{glossary_text}")
            else:
                log_message("[DEBUG] No glossary terms extracted.")
        else:
            log_message("[BATCH] No text found for glossary update.")

def translate_in_batches(log_message):
    """
    2nd pass: Read text files again in batches. Replace image tags with OCR text if needed,
    then translate using the final (now complete) glossary from the first pass.
    """
    text_files = sorted(
        [f for f in os.listdir(input_dir) if f.endswith(".txt")],
        key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else float('inf')
    )

    for i in range(0, len(text_files), 10):
        batch = text_files[i : i+10]
        log_message(f"\n=== TRANSLATING batch: {batch} ===")

        for fname in batch:
            in_file_path = os.path.join(input_dir, fname)
            out_file_path = os.path.join(output_dir, f"translated_{fname}")

            try:
                # Read & strip whitespace
                with open(in_file_path, "r", encoding="utf-8") as f_in:
                    content = f_in.read().strip()

                # Skip empty
                if not content:
                    log_message(f"[SKIP empty] {fname}")
                    continue

                # Skip if the file only has a single <image> tag
                if is_html_only_image_tag(content):
                    log_message(f"[SKIP IMAGE-ONLY] {fname} => copying as-is.")
                    with open(out_file_path, "w", encoding="utf-8") as f_out:
                        f_out.write(content)  # copy the content verbatim
                    continue

                # Otherwise, do OCR replacement & translate
                image_dir = os.path.join(input_dir, "images")
                updated_text = replace_image_tags_with_ocr(content, image_dir, log_message)

                translated = TLer(updated_text, log_message)
                if translated:
                    with open(out_file_path, "w", encoding="utf-8") as f_out:
                        f_out.write(translated)
                    log_message(f"[OK] {fname} -> translated_{fname}")
                else:
                    log_message(f"[SKIP] {fname} blocked or error.")

            except Exception as e:
                log_message(f"[ERROR processing {fname}]: {e}")

def main(log_message):
    # 1) First pass: glossary
    log_message("Starting first pass: building glossary from all chapters.")
    build_glossary_in_batches(log_message)
    log_message("Glossary-building pass is complete.\n")

    # 2) Second pass: translation
    log_message("Starting second pass: translating files using the complete glossary.")
    translate_in_batches(log_message)
    log_message("Translation pass is complete.\n")

    # 3) Third pass: verify we have only English characters in output
    log_message("Starting third pass: verifying translations for non-English chars.")

    error_log_path = os.path.join(control_script_dir, "error.txt")  
    image_dir = os.path.join(input_dir, "images")
    
    verify_translations(
        log_message=log_message,
        input_dir=input_dir,
        output_dir=output_dir,
        error_log_path=error_log_path,
        image_dir=image_dir
    )

    log_message("Verification pass is complete.")