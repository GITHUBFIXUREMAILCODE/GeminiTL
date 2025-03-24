# src/glossary.py

import os
import time
import re
from vertexai.generative_models import GenerativeModel, GenerationConfig
from .config import SAFETY_SETTING

GLOSSARY_PATH = os.path.join(os.path.dirname(__file__), "glossary.txt")

def ensure_glossary_exists():
    """
    Ensures that glossary.txt exists. If not, it creates an empty file.
    """
    if not os.path.exists(GLOSSARY_PATH):
        with open(GLOSSARY_PATH, "w", encoding="utf-8") as f:
            f.write("")
        print("[GLOSSARY] Created new glossary.txt.")

def normalize_term(term):
    """
    Normalize a glossary term for duplicate checking.
    Here we simply strip surrounding whitespace.
    """
    return term.strip()

def build_glossary(input_text, log_message, max_retries=2, retry_delay=60):
    """
    Uses a GPT-based model to extract named entities from the provided text and update the local glossary.
    
    The AI is instructed to output glossary entries in the following format:
    
      Non-English => ENGLISH
      
    If no named entities are found, it will output:
    
      No named entities found.
      
    The function extracts such entries, compares them with any existing terms in glossary.txt,
    writes new entries (avoiding exact duplicates), and returns the full glossary (existing plus new entries).
    """
    ensure_glossary_exists()  # Ensure glossary.txt exists

    # Glossary instructions pulled from OLDPH.py:
    GLOSSARY_INSTRUCTIONS = [
        "Extract a glossary of Non-English proper nouns (places, people, unique terms) from the given text.",
        "For each unique Non-English term, provide a recommended English translation.",
        "Output only lines of the form: Non-English => English, with proper capitalization.",
        "If no named entities are found, write: No named entities found."
    ]

    generation_config = GenerationConfig(
        temperature=0.4,
        top_p=0.9,
        top_k=40,
        response_mime_type="text/plain"
    )

    log_message("[GLOSSARY] Initializing model to build glossary...")

    gloss_model = GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        safety_settings=SAFETY_SETTING,
        system_instruction=GLOSSARY_INSTRUCTIONS,
        generation_config=generation_config
    )

    attempt = 0
    while attempt < max_retries:
        try:
            response = gloss_model.generate_content(input_text)
            new_glossary = response.text.strip()
            log_message(f"[DEBUG] Raw glossary response: {new_glossary}")

            # If the model outputs "No named entities found", log and return.
            if not new_glossary or "No named entities found" in new_glossary:
                log_message("[GLOSSARY] No new terms found.")
                return ""
            
            # Parse the AI response to extract glossary entries.
            # Expecting lines exactly of the form: Non-English => ENGLISH
            glossary_entries = []
            for line in new_glossary.split("\n"):
                parts = line.split("=>")
                if len(parts) == 2:
                    term = parts[0].strip()
                    meaning = parts[1].strip()
                    glossary_entries.append(f"{term} => {meaning}")
            if not glossary_entries:
                log_message("[GLOSSARY] No valid glossary terms extracted.")
                return ""
            
            # Load existing glossary entries from file.
            if os.path.exists(GLOSSARY_PATH):
                with open(GLOSSARY_PATH, "r", encoding="utf-8") as f:
                    existing_glossary = f.read().splitlines()
            else:
                existing_glossary = []
            
            # Build a set of normalized terms already in the glossary.
            existing_original_terms = set()
            for entry in existing_glossary:
                parts = entry.split("=>")
                if len(parts) == 2:
                    existing_original_terms.add(normalize_term(parts[0]))
            
            # Determine which entries are new (if the term is not already present).
            updated_entries = []
            for entry in glossary_entries:
                parts = entry.split("=>")
                if len(parts) == 2:
                    term = parts[0].strip()
                    if normalize_term(term) not in existing_original_terms:
                        updated_entries.append(entry)
                        existing_original_terms.add(normalize_term(term))
                    else:
                        log_message(f"[DEBUG] Term '{term}' is already in the glossary; skipping.")
            
            if updated_entries:
                log_message(f"[DEBUG] Writing {len(updated_entries)} new terms to glossary.txt")
                try:
                    with open(GLOSSARY_PATH, "a", encoding="utf-8") as f:
                        f.write("\n".join(updated_entries) + "\n")
                    log_message(f"[GLOSSARY] Updated glossary with {len(updated_entries)} new terms.")
                except Exception as e:
                    log_message(f"[ERROR] Failed to write glossary.txt: {e}")
                
                try:
                    with open(GLOSSARY_PATH, "r", encoding="utf-8") as f:
                        content = f.read()
                    log_message(f"[DEBUG] Final glossary content:\n{content}")
                except Exception as e:
                    log_message(f"[ERROR] Failed to verify written glossary: {e}")
            else:
                log_message("[GLOSSARY] No new terms to add; all extracted terms are duplicates.")
            
            return "\n".join(existing_glossary + updated_entries)
        except Exception as e:
            log_message(f"[GLOSSARY] Error on attempt {attempt+1}: {str(e)}")
            attempt += 1
            if attempt < max_retries:
                log_message(f"[GLOSSARY] Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                log_message("[GLOSSARY] Exhausted retries. Skipping glossary update.")
                return ""
