"""
Module: gender_proofing.py

Handles AI-based gender pronoun correction using context and name glossaries.
"""

import os
import time
from vertexai.generative_models import GenerativeModel, GenerationConfig
from config.config import SAFETY_SETTING
from .glossary_utils import load_proofing_glossaries

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

    # --- System Instructions ---
    GENDER_PROOFING_INSTRUCTIONS = [
        "You are an expert English proofreader.",
        "Your ONLY task is to fix gender pronouns (he, she, his, hers, they, them, etc.) to match the character gender defined in the glossary.",
        "",
        "You MUST NOT change any character names, punctuation, sentence structure, or formatting.",
        "Do NOT invent, hallucinate, rephrase, or translate from scratch.",
        "",
        "HTML tags and <<<IMAGE_START>>>...<<<IMAGE_END>>> blocks MUST be preserved exactly.",
        "If no changes are needed, return the text exactly as-is.",
        "===========================CONTEXT GLOSSARY=========================",
        "Glossary (name => gender):",
        context_glossary_text or "(none)",
        "===========================NAME GLOSSARY=============================",
        "Glossary of Proper Names (read-only, for reference):",
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
        try:
            log_message(f"[PROOF-GENDER] attempt {attempt + 1}/{max_retries}")
            response = proof_model.generate_content(prompt)

            if response and response.text:
                result = response.text.strip()
                if result:
                    return result
            log_message("[ERROR] Empty or malformed AI response")
            return text
        except Exception as e:
            log_message(f"[ERROR] Proofing failed on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                log_message(f"[RETRY] Waiting {retry_delay}s...")
                time.sleep(retry_delay)

    log_message("[FAILED] All proofing attempts failed. Returning original.")
    return text
