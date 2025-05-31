
"""
Module: glossary_proofing.py

Handles AI-based cleaning and consistency checking of glossary files.
"""

import os
import time
from vertexai.generative_models import GenerativeModel, GenerationConfig
from config.config import SAFETY_SETTING
from .utils import split_text_into_chunks

PROOF_GLOSSARY_INSTRUCTIONS = [
    "Your task is to proofread the given glossary for a Non-English-to-English translation project.",
    "Fix any inconsistencies, merge similar entries, and remove any similar and exact duplicates.",
    "If there is transliteration, translate it into the nearest English equivalent.",
    "Each glossary line is in this format: Original => English => Gender",
    "Ensure consistent formatting and spacing.",
    "If two ORIGINAL terms are CLEARLY spelling variants of the SAME name, merge them.",
    "Preserve honorifics by appending them to the translated term.",
    "Return ONLY the cleaned glossary lines. Do not explain or comment.",
    "All lines across all chunks should be used to determine consistency."
]

def proof_glossary_file(glossary_path: str, log_message=print, max_retries=3, retry_delay=60):
    if not os.path.exists(glossary_path):
        log_message(f"[ERROR] Glossary file not found: {glossary_path}")
        return

    with open(glossary_path, "r", encoding="utf-8") as f:
        content = f.read()

    parts = content.split("==================================== GLOSSARY START ===============================")
    if len(parts) < 2:
        log_message("[ERROR] Glossary markers not found in glossary file.")
        return

    glossary_text = parts[1].split("==================================== GLOSSARY END ================================")[0].strip()
    if not glossary_text:
        log_message("[INFO] Glossary is empty, skipping proofreading.")
        return

    model = GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        system_instruction="\n".join(PROOF_GLOSSARY_INSTRUCTIONS),
        safety_settings=SAFETY_SETTING,
        generation_config=GenerationConfig(
            temperature=0.4,
            top_p=0.9,
            top_k=40,
            response_mime_type="text/plain"
        )
    )

    glossary_chunks = split_text_into_chunks(glossary_text, max_bytes=10240)
    all_cleaned_entries = []

    previous_cleaned = []

    for i, chunk in enumerate(glossary_chunks):
        context = "\n".join(previous_cleaned)
        full_prompt = "\n".join(PROOF_GLOSSARY_INSTRUCTIONS)
        if context:
            full_prompt += f"\n\nPREVIOUS CLEANED ENTRIES:\n{context}"
        full_prompt += f"\n\nGlossary Part {i+1} (to proofread):\n{chunk}"

        attempt = 0
        while attempt < max_retries:
            try:
                log_message(f"[GLOSSARY PROOFING] Part {i+1}/{len(glossary_chunks)}, Attempt {attempt + 1}")
                response = model.generate_content(full_prompt)
                if response and response.text:
                    cleaned_chunk = response.text.strip()
                    previous_cleaned.append(cleaned_chunk)
                    all_cleaned_entries.append(cleaned_chunk)
                    break
                else:
                    log_message("[ERROR] Empty response from glossary proofing model.")
                    break
            except Exception as e:
                attempt += 1
                log_message(f"[ERROR] Part {i+1} attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    log_message(f"[RETRY] Waiting {retry_delay}s...")
                    time.sleep(retry_delay)
        else:
            log_message(f"[FAILED] Part {i+1} failed after {max_retries} attempts.")

    if all_cleaned_entries:
        new_content = (
            "==================================== GLOSSARY START ===============================\n"
            + "\n".join(all_cleaned_entries) + "\n"
            + "==================================== GLOSSARY END ================================"
        )
        with open(glossary_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        log_message(f"[OK] Glossary proofreading complete. Updated: {glossary_path}")
    else:
        log_message("[FAILED] No successful glossary batches were completed.")
