"""
Module: gender_proofing.py

Handles AI-based gender pronoun correction using context and name glossaries.
"""

import os
import time
from vertexai.generative_models import GenerativeModel, GenerationConfig
from config.config import SAFETY_SETTING
from .glossary_utils import load_proofing_glossaries
from proofing.utils import call_with_timeout

def proof_gender_pronouns(text: str, context_dict: dict, glossary_path: str,
                           log_message=print, max_retries=3, retry_delay=60) -> str:
    if not text.strip():
        log_message("[ERROR] Empty text for gender proofing")
        return text

    # --- Load both glossaries ---
    name_glossary_text, _ = load_proofing_glossaries(glossary_path, log_message)
    context_glossary_text = "\n".join(
        f"{name} => {gender}" for name, gender in context_dict.items()
    )

    GENDER_PROOFING_INSTRUCTIONS = [
            "You are an expert English proofreader, specializing in pronoun correction.",
            "Your ONLY task is to correct gender pronouns (he, she, his, hers, him, her, they, them, their, theirs, himself, herself, themselves) within the text to accurately reflect the character's gender as defined in the provided glossary.",
            "",
            "Prioritize accuracy: Use the glossary and *context* to ensure pronoun changes are grammatically correct and logically consistent within the sentence and surrounding text.",  # Emphasize context
            "If a pronoun is ambiguous and not clearly linked to a character in the glossary, leave it unchanged.  Do *NOT* guess or assume.", # Explicit about ambiguity
            "",
            "You MUST NOT change any character names, punctuation, sentence structure, word choice, formatting, or any other aspect of the text besides the gender pronouns that conflict with the provided glossary.",
            "Do NOT invent, hallucinate, rephrase, or translate from scratch. Only make the smallest changes necessary to correct pronouns.",
            "",
            "HTML tags and <<<IMAGE_START>>>...<<<IMAGE_END>>> blocks MUST be preserved exactly.  Do not modify or remove them.",
            "If no gender pronouns require correction based on the glossary, return the text exactly as-is.",
            "If the provided 'context_glossary_text' is empty or contains '(none)', skip pronoun correction and return the text exactly as-is.", #handles no context glossary
            "",
            "===========================CONTEXT GLOSSARY=========================",
            "Glossary (character name => gender pronoun set):  Use these to replace existing pronouns in the main text. Example sets: 'he/him/his/himself', 'she/her/hers/herself', 'they/them/their/themselves'.", #clarifying and adding pronouns
            context_glossary_text or "(none)",
            "===========================NAME GLOSSARY=============================",
            "Glossary of Proper Names (read-only, for reference only; DO NOT USE TO REPLACE PRONOUNS): This glossary contains a list of character names, locations, items and other proper nouns that may appear in the text.",
            name_glossary_text or "(none)",
            "",
            "===========================GLOSSARY END================================",
            "Begin proofreading below:"
        ]

    prompt = text.strip()

    proof_model = GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        safety_settings=SAFETY_SETTING,
        system_instruction="\n".join(GENDER_PROOFING_INSTRUCTIONS),
        generation_config=GenerationConfig(
            temperature=0.4,
            top_p=0.95,
            top_k=40,
            response_mime_type="text/plain"
        )
    )

    for attempt in range(max_retries):
        retry_delay = retry_delay * (2 ** attempt)  # Exponential backoff
        
        try:
            log_message(f"[PROOF-GENDER] attempt {attempt + 1}/{max_retries}")
            
            # Use call_with_timeout to prevent hanging
            success, result = call_with_timeout(
                proof_model.generate_content, 
                args=(prompt,), 
                timeout=150  # 2 minute timeout
            )
            
            if not success:
                if isinstance(result, TimeoutError):
                    log_message(f"[TIMEOUT] Gender proofing timed out after 120 seconds")
                else:
                    log_message(f"[ERROR] Gender proofing failed: {result}")
                if attempt < max_retries - 1:
                    log_message(f"[RETRY] Waiting {retry_delay}s...")
                    time.sleep(retry_delay)
                continue
                
            response = result

            if response and response.text:
                result = response.text.strip()

                # --- Reject overly short or empty results ---
                if not result:
                    log_message("[ERROR] Empty AI response text.")
                    return text

                # --- Reject trivial outputs like "No changes needed" ---
                if result.lower().strip() in {
                    "no changes needed", "no edits necessary", "unchanged", "no change needed"
                }:
                    log_message("[INFO] Gender proofing returned no changes.")
                    return text

                # --- Sanity check: avoid returning radically short output ---
                orig_lines = text.strip().splitlines()
                result_lines = result.splitlines()
                if len(result_lines) < max(5, 0.2 * len(orig_lines)):
                    log_message(f"[WARNING] Gender proofing output too short ({len(result_lines)} lines vs {len(orig_lines)}). Keeping original.")
                    return text

                return result

            log_message("[ERROR] Empty or malformed AI response object")
            return text

        except Exception as e:
            log_message(f"[ERROR] Proofing failed on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                log_message(f"[RETRY] Waiting {retry_delay}s...")
                time.sleep(retry_delay)

    log_message("[FAILED] All proofing attempts failed. Returning original.")
    return text

