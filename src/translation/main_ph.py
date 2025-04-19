"""
Main entry point for the translation process.

This script handles the translation workflow including:
- Processing input files (if available)
- Translating content using the Gemini API
- Handling image tags and OCR
- Running three proofing passes:
    1. Checking for non-English text and retranslating problematic sentences using surrounding context.
    2. Fixing any gender pronouns using the context glossary from the custom glossary folder.
    3. Running AI-based proofreading for syntax and continuity improvements.
- Managing output files
"""

import re
import os
import sys
import time

from translation.translator import Translator
from translation.glossary import Glossary
from translation.proofing import Proofreader
from translation.image_ocr import ImageOCR

def main(log_message=None, glossary_file=None, proofing_only=False, skip_phase1=False, pause_event=None, cancel_flag=None):

    if log_message is None:
        log_message = print

    glossary = Glossary()

    # If a custom glossary file is provided, set it
    if glossary_file:
        glossary.set_current_glossary_file(glossary_file)

    # ✅ Always split glossary even if skipping Phase 1
    try:
        from translation.context_aware_glossary import split_glossary
        split_glossary(glossary.get_current_glossary_file())
        log_message("[GLOSSARY] Ensured name/context subfiles exist.")
    except Exception as e:
        log_message(f"[GLOSSARY] Split error or missing glossary: {e}")

    # Translator and Proofreader must use the SAME glossary object
    translator = Translator()
    translator.glossary = glossary  # Force use of selected glossary path

    proofreader = Proofreader(log_message, glossary.get_current_glossary_file())
    
    # Ensure input and output directories exist
    if not os.path.exists("output"):
        os.makedirs("output")
        log_message("Created 'output' directory")

    # Determine the source of files based on the existence of input files.
    def numeric_key(filename):
        match = re.search(r'\d+', filename)
        return int(match.group()) if match else float('inf')

    input_files = []
    if os.path.exists("input"):
        input_files = [f for f in os.listdir("input") if f.endswith(".txt")]

    if input_files:
        text_files = sorted(input_files, key=numeric_key)
        run_full_translation = True
    else:
        log_message("No input files found; using files from 'output' for proofing.")
        text_files = sorted([f for f in os.listdir("output") if f.endswith(".txt")], key=numeric_key)
        run_full_translation = False

    if not proofing_only:
        # Phase 1: Glossary Building & Glossary Proofing
        if run_full_translation and not skip_phase1:
            log_message("\n=== Phase 1: Building Glossary ===")
            batch_size = 10
            total_batches = (len(text_files) + batch_size - 1) // batch_size
    
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(text_files))
                current_batch = text_files[start_idx:end_idx]
    
                log_message(f"\nProcessing glossary batch {batch_num + 1} of {total_batches}")
                for filename in current_batch:
                    input_path = os.path.join("input", filename)
                    try:
                        with open(input_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        # Build glossary without splitting after each chapter
                        glossary.build_glossary(content, log_message, split_glossary=False)
                        log_message(f"Processed {filename} for glossary")
                    except Exception as e:
                        log_message(f"Error processing {filename} for glossary: {str(e)}")    
            try:
                from translation.context_aware_glossary import split_glossary
                split_glossary(glossary.get_current_glossary_file())
                log_message("[GLOSSARY] Split into name/context glossaries.")
            except Exception as e:
                log_message(f"[GLOSSARY] Split error: {e}")

            log_message("Glossary building completed")

            # Phase 1.5: Glossary Proofreading
            log_message("\n--- Glossary Proofreading ---")
            proofreader.proof_glossary_file(glossary.get_current_glossary_file()) 

        # ✅ Phase 2 must run even if Phase 1 is skipped
        if run_full_translation:
            log_message("\n=== Phase 2: Translation with Name Glossary ===")
            for i, filename in enumerate(text_files, 1):
                input_path = os.path.join("input", filename)
                output_path = os.path.join("output", f"translated_{filename}")
                log_message(f"\nTranslating file {i} of {len(text_files)}: {filename}")
                if cancel_flag and cancel_flag():
                    log_message("[CONTROL] Translation canceled before processing next chapter.")
                    break
                if pause_event:
                    log_message("[CONTROL] Waiting for resume...")
                    pause_event.wait()
                try:
                    with open(input_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Handle image tags and OCR if present
                    if "<img" in content:
                        content = ImageOCR.replace_image_tags_with_ocr(content, os.path.join("input", "images"))

                    translated = translator.translate(content, log_message)
                    if translated is None:
                        log_message(f"Skipping {filename} due to translation failure")
                        continue

                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(translated)
                    log_message(f"Translated {filename}")
                except Exception as e:
                    log_message(f"Error processing {filename}: {str(e)}")

    # Phase 3: Proofing Translated Files - 3 Passes
    log_message("\n=== Phase 3: Proofing Translated Files ===")
    non_english_log = os.path.join("output", "non_english_lines.log")
    
    # Pass 1: Check for non-English text and retranslate problematic sentences with context.
    log_message("\n--- Proofing Pass 1: Non-English Text Detection & Contextual Retranslation ---")
    proofreader.detect_and_log_non_english_sentences("output", non_english_log, "input")

    # Pass 2: Fix gender pronouns using the custom context glossary.
    log_message("\n--- Proofing Pass 2: Fixing Gender Pronouns Using Context Glossary ---")
    
    def custom_load_context_glossary(_):
        context_dict = {}  # Initialize empty dictionary
        # Use the existing glossary instance instead of creating a new one
        custom_glossary_path = glossary.get_current_glossary_file()
        glossary_name = os.path.splitext(os.path.basename(custom_glossary_path))[0]
        glossary_dir = os.path.dirname(custom_glossary_path)
        context_glossary_path = os.path.join(glossary_dir, glossary_name, "context_glossary.txt")
        
        try:
            with open(context_glossary_path, "r", encoding="utf-8") as f:
                content = f.read()
                parts = content.split("==================================== GLOSSARY START ===============================")
                if len(parts) > 1:
                    glossary_text = parts[1].split("==================================== GLOSSARY END ================================")[0].strip()
                    for line in glossary_text.splitlines():
                        if '=>' in line:
                            english, gender = map(str.strip, line.split("=>"))
                            context_dict[english] = gender
        except Exception as e:
            log_message(f"[ERROR] Failed to read context glossary: {e}")
        return context_dict

    # Apply the patch so that the proofing process will use the custom glossary
    proofreader.load_context_glossary = custom_load_context_glossary
    
    # Get the context dictionary first
    context_dict = custom_load_context_glossary(None)
    # Then pass it to the proofing function
    proofreader.proof_gender_pronouns_for_all_files("output", context_dict)

    # Ensure files are being processed
    log_message("[PROOFING] Gender pronoun proofing completed.")

    # Pass 3: Final AI-based proofreading for syntax and continuity errors.
    log_message("\n--- Proofing Pass 3: AI-driven Proofreading for Syntax and Continuity ---")
    translated_files = [f for f in os.listdir("output") if f.startswith("translated_") and f.endswith(".txt")]
    translated_files.sort(key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else float('inf'))
    for fname in translated_files:
        out_file_path = os.path.join("output", fname)
        try:
            log_message(f"[PROOFING] Running AI proofreading on {fname}...")
            with open(out_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            proofed_content = proofreader.proofread_with_ai(out_file_path)
            if proofed_content != content:
                with open(out_file_path, "w", encoding="utf-8") as f:
                    f.write(proofed_content)
                log_message(f"[OK] AI proofreading updated {fname}.")
            else:
                log_message(f"[OK] No AI proofreading changes needed for {fname}.")
        except Exception as e:
            log_message(f"[ERROR processing {fname} during AI proofreading]: {e}")

    log_message("\nProofing completed for all translated files.")
    log_message("\nTranslation process completed")

if __name__ == "__main__":
    main()
