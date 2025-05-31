
"""Refactored main_ph.py — Main entry point for the translation workflow."""

import os
import re
from translation.translator import Translator
from glossary.glossary import Glossary
from proofing.proofing import Proofreader
from translation.image_ocr import ImageOCR
from glossary.glossary_splitter import split_glossary

def setup_glossary(glossary_file, log_message):
    glossary = Glossary()
    if glossary_file:
        glossary.set_current_glossary_file(glossary_file)
    try:
        split_glossary(glossary.get_current_glossary_file())
        log_message("[GLOSSARY] Ensured name/context subfiles exist.")
    except Exception as e:
        log_message(f"[GLOSSARY] Split error or missing glossary: {e}")
    return glossary

def run_glossary_phase(text_files, glossary, log_message):
    log_message("\n=== Phase 1: Building Glossary ===")
    for idx, filename in enumerate(text_files, 1):
        input_path = os.path.join("input", filename)
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                content = f.read()
            glossary.build_glossary(content, log_message, split_glossary=False)
            log_message(f"Processed {filename} for glossary")
        except Exception as e:
            log_message(f"[ERROR] {filename}: {e}")

    log_message("\n--- Glossary Proofreading ---")
    proofreader = Proofreader(log_message, glossary.get_current_glossary_file())
    proofreader.proof_glossary_file(glossary.get_current_glossary_file())
    try:
        split_glossary(glossary.get_current_glossary_file())
        log_message("[GLOSSARY] Split into name/context glossaries.")
    except Exception as e:
        log_message(f"[GLOSSARY] Split error: {e}")

def run_translation_phase(text_files, glossary, log_message, pause_event, cancel_flag, source_lang):
    translator = Translator(source_lang=source_lang)
    translator.glossary = glossary
    if not os.path.exists("output"):
        os.makedirs("output")
        log_message("Created 'output' directory")

    for i, filename in enumerate(text_files, 1):
        input_path = os.path.join("input", filename)
        output_path = os.path.join("output", f"translated_{filename}")
        log_message(f"\nTranslating file {i} of {len(text_files)}: {filename}")

        if cancel_flag and cancel_flag():
            log_message("[CONTROL] Translation canceled before processing.")
            break
        if pause_event and pause_event.is_set():
            log_message("[CONTROL] Paused. Waiting...")
            pause_event.wait()
            log_message("[CONTROL] Resumed.")
            if cancel_flag and cancel_flag():
                log_message("[CONTROL] Translation canceled after resume.")
                break

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                log_message(f"[SKIP] {filename} is empty.")
                continue

            html_only = re.sub(r"<[^>]+>", "", content).strip() == ""
            if html_only:
                log_message(f"[SKIP] {filename} is HTML only. Copying...")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(content)
                continue

            if "<img" in content:
                log_message(f"[INFO] Running OCR for {filename}...")
                image_ocr = ImageOCR(log_function=log_message)
                content = image_ocr.replace_image_tags_with_ocr(content, os.path.join("input", "images"))

            translated = translator.translate(content, log_message)
            if translated is None:
                log_message(f"[ERROR] Failed to translate {filename}")
                continue

            original_size = len(content.encode("utf-8"))
            translated_size = len(translated.encode("utf-8"))
            retry_threshold_percent = 125.0
            percent_diff = ((translated_size - original_size) / original_size * 100) if original_size else 0
            final_translation = translated
            max_retries = 4
            retry_count = 0

            while abs(percent_diff) > retry_threshold_percent and retry_count < max_retries:
                retry_count += 1
                log_message(f"[RETRY] Translation size mismatch for {filename}: {percent_diff:.2f}%. Retrying {retry_count}/{max_retries}")
                translated_retry = translator.translate(content, log_message)
                if translated_retry:
                    retry_size = len(translated_retry.encode("utf-8"))
                    retry_percent_diff = ((retry_size - original_size) / original_size * 100) if original_size else 0
                    if abs(retry_percent_diff) <= retry_threshold_percent:
                        final_translation = translated_retry
                        log_message("[OK] Retry successful.")
                        break
                    percent_diff = retry_percent_diff
                else:
                    log_message("[ERROR] Retry translation failed.")
                    break
            else:
                log_message("[NOTICE] Using original translation result despite size deviation.")

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_translation)
            log_message(f"[OK] Translated output saved: {output_path}")

            placeholder_pattern = re.compile(r'__IMAGE_TAG_(\d+)__')
            original_placeholders = set(placeholder_pattern.findall(content))
            translated_placeholders = set(placeholder_pattern.findall(final_translation))
            if original_placeholders != translated_placeholders:
                log_message(f"[WARNING] Placeholder mismatch in {filename}: Original={len(original_placeholders)}, Translated={len(translated_placeholders)}")

        except Exception as e:
            log_message(f"[ERROR] Failed during {filename}: {e}")

    def run_proofing_phase(glossary, log_message, pause_event=None, cancel_flag=None):
        proofreader = Proofreader(log_message, glossary.get_current_glossary_file())

        log_message("\n========= proofing phase start =========")

        # --- Non-English Proofing
        log_message("=== Subphase: Non-English Check ===")
        non_english_log = os.path.join("output", "non_english_lines.log")
        proofreader.detect_and_log_non_english_sentences(
            "output", non_english_log, "input", pause_event, cancel_flag
        )
        log_message("=== End Subphase: Non-English Check ===")

        # --- Gender Pronoun Fix
        log_message("=== Subphase: Gender-Proofing ===")
        translated_files = [f for f in os.listdir("output") if f.startswith("translated_") and f.endswith(".txt")]
        translated_files.sort(key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else float('inf'))

        context_dict = proofreader.load_context_glossary()
        for fname in translated_files:
            try:
                file_path = os.path.join("output", fname)
                with open(file_path, "r", encoding="utf-8") as f:
                    translated = f.read()

                proofed = proofreader.proof_gender_pronouns(translated, context_dict, glossary_path=glossary.get_current_glossary_file())
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(proofed)
                log_message(f"[OK] Gender fix done for {fname}")
            except Exception as e:
                log_message(f"[ERROR] Gender fix failed for {fname}: {e}")
        log_message("=== End Subphase: Gender-Proofing ===")

        # --- AI Proofreading
        log_message("=== Subphase: AI Proofreading ===")
        for fname in translated_files:
            try:
                file_path = os.path.join("output", fname)
                with open(file_path, "r", encoding="utf-8") as f:
                    proofed = f.read()

                ai_proofed = proofreader.proofread_with_ai(file_path)
                original_size = len(proofed.encode("utf-8"))
                proofed_size = len(ai_proofed.encode("utf-8"))
                diff_kb = abs(proofed_size - original_size) / 1024.0
                retry_threshold_kb = 10.0
                max_retries = 2
                retry_count = 0

                while diff_kb > retry_threshold_kb and retry_count < max_retries:
                    retry_count += 1
                    log_message(f"[RETRY] Proofread size difference {diff_kb:.2f} KB. Retrying {retry_count}/{max_retries}")
                    ai_retry = proofreader.proofread_with_ai(file_path)
                    if ai_retry:
                        retry_size = len(ai_retry.encode("utf-8"))
                        diff_kb = abs(retry_size - original_size) / 1024.0
                        if diff_kb <= retry_threshold_kb:
                            ai_proofed = ai_retry
                            break
                    else:
                        log_message("[ERROR] Proofread retry failed.")
                        break

                proofed_dir = os.path.join("output", "proofed_ai")
                os.makedirs(proofed_dir, exist_ok=True)
                with open(os.path.join(proofed_dir, fname), "w", encoding="utf-8") as f:
                    f.write(ai_proofed)
                log_message(f"[OK] AI proofreading complete: {fname}")
            except Exception as e:
                log_message(f"[ERROR] AI Proofing failed for {fname}: {e}")
        log_message("=== End Subphase: AI Proofreading ===")

        log_message("========= proofing phase end =========\n")


def main(log_message=None, glossary_file=None, proofing_only=False,
         skip_phase1=False, pause_event=None, cancel_flag=None,
         source_lang="Japanese"):

    if log_message is None:
        log_message = print

    glossary = setup_glossary(glossary_file, log_message)

    input_files = [f for f in os.listdir("input") if f.endswith(".txt")] if os.path.exists("input") else []
    run_translation = bool(input_files)
    text_files = sorted(input_files if run_translation else
                        [f for f in os.listdir("output") if f.endswith(".txt")])

    if not proofing_only:
        if run_translation and not skip_phase1:
            run_glossary_phase(text_files, glossary, log_message)
        if run_translation:
            run_translation_phase(text_files, glossary, log_message, pause_event, cancel_flag, source_lang)

    run_proofing_phase(glossary, log_message, pause_event, cancel_flag)

if __name__ == "__main__":
    main()
