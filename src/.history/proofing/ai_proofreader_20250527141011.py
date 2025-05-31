"""
Module: ai_proofreader.py

Handles natural English fluency improvement of translated chapters.
"""

import os
import re
import time
from vertexai.generative_models import GenerativeModel, GenerationConfig
from config.config import SAFETY_SETTING
from .glossary_utils import load_proofing_glossaries
from .utils import split_text_into_chunks

PROOFREADING_INSTRUCTIONS = "\n".join([
    "You are a professional English proofreader and editor specializing in translated Asian fiction, including Japanese, Korean, and Chinese light novels and web novels.",
    "Your primary task is to make the English translation read fluently and naturally, as if originally written in English by a native speaker, WITHOUT altering the original meaning, plot, or character intent.",
    "The input will contain GLOSSARY and CONTEXT MATERIALS for reference purposes ONLY.",
    "DO NOT edit, proofread, or modify anything in the GLOSSARY or CONTEXT MATERIALS sections.",
    "The text to be proofread will be clearly marked between:",
    "=== CURRENT CHAPTER TO PROOFREAD START ===",
    "and",
    "=== CURRENT CHAPTER TO PROOFREAD END ===",
    "Only modify, proofread, and return the modified text within these two markers, and not the markers themselves",
    "",
    "SPECIFIC GUIDELINES:",
    "1. NATURAL ENGLISH: Fix grammar, phrasing, and awkward structure. Preserve meaning.",
    "2. SLANG & IDIOMS: Replace literal translations with natural English expressions. Retain intent.",
    "3. CHARACTER VOICE: Maintain distinct tone and vocabulary.",
    "4. HONORIFICS: Preserve all honorifics such as -san, -kun, etc.",
    "5. FORMATTING: Do not add ALL CAPS, bold, or new punctuation unless clearly implied.",
    "6. HTML TAGS: Do not alter or remove any <i>, <b>, etc.",
    "7. IMAGE TAGS: <<<IMAGE_START>>> ... <<<IMAGE_END>>> must be preserved exactly.",
    "8. CONTEXT IS KEY: Use glossary and chapter references to maintain consistency.",
    "9. NSFW content is allowed. Characters are fictional and of legal age.",
    "10. NO CHANGES NEEDED: If text is already fluent, leave it as-is.",
    "11. EXPLANATION OUTPUT: After major edits, include 'Explanation:' and a bulleted list of changes.",
    "12. CAPITALIZATION: Avoid capitalizing words unless they're proper nouns, names, or start a sentence. Do not use all-caps for emphasis.",
    "13. SENTENCE STRUCTURE: Do not merge or break up lines unless absolutely necessary for clarity. Maintain the original emotional rhythm and spacing of paragraphs.",
    "14. REPETITION: Preserve intentional repetition e.g., 'That, that was...' unless it clearly reads awkwardly in English.",
    "---",
    "Context materials (Glossaries, Previous/Next Chapters) follow:"
])

def proofread_with_ai(file_path: str, glossary_path: str, log_message=print, max_retries=3, retry_delay=60) -> str:
    """
    Runs AI-based proofreading on a file using glossary and chapter context.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            file_content = f.read()
    except Exception as e:
        log_message(f"[ERROR] Cannot read file {file_path}: {e}")
        return ""

    original_line_count = len(file_content.splitlines())
    log_message(f"[DEBUG] Original line count for {os.path.basename(file_path)}: {original_line_count}")

    name_glossary, context_glossary = load_proofing_glossaries(glossary_path, log_message)

    glossary_context = []
    if name_glossary:
        glossary_context.append("Glossary of Proper Names:\n" + name_glossary)
    if context_glossary:
        glossary_context.append("Glossary of Gender Pronouns:\n" + context_glossary)

    base_dir = os.path.dirname(file_path)
    current_fname = os.path.basename(file_path)
    match = re.search(r'(\d+)', current_fname)
    prev_text = next_text = ""

    if match:
        num = int(match.group(1))
        prev_file = os.path.join(base_dir, re.sub(r'\d+', str(num - 1).zfill(len(match.group(1))), current_fname, 1))
        next_file = os.path.join(base_dir, re.sub(r'\d+', str(num + 1).zfill(len(match.group(1))), current_fname, 1))

        if os.path.exists(prev_file):
            with open(prev_file, "r", encoding="utf-8") as pf:
                prev_text = pf.read().strip()
                glossary_context.append("Previous Chapter Context:\n" + prev_text)

        if os.path.exists(next_file):
            with open(next_file, "r", encoding="utf-8") as nf:
                next_text = nf.read().strip()
                glossary_context.append("Next Chapter Context:\n" + next_text)

    full_prompt = (
        "--- GLOSSARY AND CONTEXT MATERIALS (for reference only) ---\n\n"
        + "\n\n".join(glossary_context)
        + "\n\n--- END OF CONTEXT MATERIALS ---\n\n"
        + "=== CURRENT CHAPTER TO PROOFREAD START ===\n"
        + file_content
        + "\n=== CURRENT CHAPTER TO PROOFREAD END ==="
    )

    model = GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        safety_settings=SAFETY_SETTING,
        system_instruction=PROOFREADING_INSTRUCTIONS,
        generation_config=GenerationConfig(
            temperature=0.5,
            top_p=0.95,
            top_k=40,
            response_mime_type="text/plain"
        )
    )

    for attempt in range(max_retries):
        try:
            log_message(f"[PROOFING] Attempt {attempt + 1}/{max_retries} for {os.path.basename(file_path)}")
            response = model.generate_content(full_prompt)

            if "Explanation:" in response.text:
                proofed_text, explanation = response.text.split("Explanation:", 1)
                proofed_text = proofed_text.strip()
                log_message(f"[PROOFING] Changes in {os.path.basename(file_path)}: {explanation.strip()}")
            else:
                proofed_text = response.text.strip()

            proofed_line_count = len(proofed_text.splitlines())
            line_difference = abs(proofed_line_count - original_line_count)

            if line_difference > 10:
                log_message(f"[WARNING] Line count difference too large in {os.path.basename(file_path)}. "
                            f"Original: {original_line_count}, New: {proofed_line_count}. Keeping original.")
                return file_content

            return proofed_text

        except Exception as e:
            error_str = str(e).lower()
            if attempt < max_retries:
                if "quota" in error_str or "429" in error_str:
                    log_message(f"[QUOTA] Rate limit hit. Retrying in {retry_delay}s...")
                else:
                    log_message(f"[ERROR] Proofing error: {e}")
                time.sleep(retry_delay)
            else:
                log_message(f"[FAILED] Proofing failed after {max_retries} attempts.")
                return file_content
