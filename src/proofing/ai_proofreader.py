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
from .utils import split_text_into_chunks, call_with_timeout

PROOFREADING_INSTRUCTIONS = "\n".join([
    "SYSTEM INSTRUCTIONS — PROOFREADING",
    "",
    "ROLE: You are a professional English proofreader and editor specializing in translated Asian fiction (Japanese, Korean, and Chinese light novels and web novels).",
    "OBJECTIVE: Make the English translation read fluently and naturally, as if originally written in English by a native speaker, WITHOUT altering the original meaning, plot, or character intent.",
    "",
    "REFERENCE SECTIONS: The input may contain GLOSSARY and CONTEXT MATERIALS. These are for reference only. DO NOT edit or change anything within them.",
    "",
    "SCOPE: The text to be proofread is enclosed between the exact markers:",
    "=== CURRENT CHAPTER TO PROOFREAD START ===",
    "=== CURRENT CHAPTER TO PROOFREAD END ===",
    "Edit only the text between these markers and return only that text (omit the markers themselves).",
    "",
    "SPECIFIC GUIDELINES:",
    "1. NATURAL ENGLISH: Fix grammar, phrasing, and awkward sentences while preserving meaning.",
    "2. SLANG & IDIOMS: Replace literal translations with natural English equivalents that keep the author's intent.",
    "3. CHARACTER VOICE: Retain each character's distinct tone and vocabulary.",
    "4. HONORIFICS: Preserve all honorifics (e.g., -san, -kun, -sama).",
    "5. FORMATTING: Do not add ALL CAPS, bold, or extra punctuation unless clearly required by the original.",
    "6. HTML TAGS: Do not add or remove any <i>, <b>, or similar tags.",
    "7. IMAGE TAGS: Preserve <<<IMAGE_START>>> ... <<<IMAGE_END>>> exactly as given.",
    "8. CONTEXT CONSISTENCY: Consult the glossary and context materials to maintain terminology consistency.",
    "9. NSFW: NSFW content is allowed; characters are fictional and of legal age.",
    "10. NO CHANGES NEEDED: Leave text unchanged if it already reads fluently.",
    "11. EXPLANATION: After significant edits, append 'Explanation:' followed by a bulleted list of key changes. Do not repeat the explaination more than once.",
    "12. CAPITALIZATION: Capitalize proper nouns, names, and sentence beginnings only; avoid unnecessary ALL-CAPS.",
    "13. SENTENCE STRUCTURE: Avoid merging or splitting sentences unless essential for clarity; keep original pacing and paragraph breaks.",
    "14. REPETITION: Preserve intentional repetition (e.g., 'That, that was...') unless it sounds unnatural in English.",
    "---",
    "Context materials (Glossaries, Previous/Next Chapters) follow:"
])


def proofread_with_ai(file_path: str, glossary_path: str, log_message=print, max_retries=3, initial_retry_delay=60) -> str:
    """
    Runs AI-based proofreading on a file using glossary and chapter context.
    Uses exponential backoff for retries and timeout protection.
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
        #snext_file = os.path.join(base_dir, re.sub(r'\d+', str(num + 1).zfill(len(match.group(1))), current_fname, 1))

        if os.path.exists(prev_file):
            with open(prev_file, "r", encoding="utf-8") as pf:
                prev_text = pf.read().strip()
                glossary_context.append("Previous Chapter Context:\n" + prev_text)

        # Removing next chapter context
        # The code below is removed:
        # if os.path.exists(next_file):
        #     with open(next_file, "r", encoding="utf-8") as nf:
        #         next_text = nf.read().strip()
        #         glossary_context.append("Next Chapter Context:\n" + next_text)

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
        retry_delay = initial_retry_delay * (2.5 ** attempt)  # Exponential backoff
        
        try:
            log_message(f"[PROOFING] Attempt {attempt + 1}/{max_retries} for {os.path.basename(file_path)}")
            
            # Use call_with_timeout to prevent hanging
            success, result = call_with_timeout(
                model.generate_content, 
                args=(full_prompt,), 
                timeout=180  # 3 minute timeout
            )
            
            if not success:
                if isinstance(result, TimeoutError):
                    log_message(f"[TIMEOUT] AI proofing timed out after 180 seconds")
                else:
                    log_message(f"[ERROR] AI proofing failed: {result}")
                if attempt < max_retries - 1:
                    log_message(f"[RETRY] Waiting {retry_delay}s...")
                    time.sleep(retry_delay)
                continue
                
            response = result
            
            if "Explanation:" in response.text:
                proofed_text, explanation = response.text.split("Explanation:", 1)
                proofed_text = proofed_text.strip()
                log_message(f"[PROOFING] Changes in {os.path.basename(file_path)}: {explanation.strip()}")
            else:
                proofed_text = response.text.strip()
                
            # Remove any marker text that might have been included in the response
            proofed_text = proofed_text.replace("=== CURRENT CHAPTER TO PROOFREAD START ===", "").strip()
            proofed_text = proofed_text.replace("=== CURRENT CHAPTER TO PROOFREAD END ===", "").strip()

            proofed_line_count = len(proofed_text.splitlines())
            line_difference = abs(proofed_line_count - original_line_count)

            if line_difference > 10:
                log_message(f"[WARNING] Line count difference too large in {os.path.basename(file_path)}. "
                            f"Original: {original_line_count}, New: {proofed_line_count}. Keeping original.")
                return file_content

            return proofed_text

        except Exception as e:
            error_str = str(e).lower()
            if attempt < max_retries - 1:
                if "quota" in error_str or "429" in error_str:
                    log_message(f"[QUOTA] Rate limit hit. Retrying in {retry_delay}s...")
                else:
                    log_message(f"[ERROR] Proofing error: {e}")
                time.sleep(retry_delay)
            else:
                log_message(f"[FAILED] Proofing failed after {max_retries} attempts.")
                return file_content





