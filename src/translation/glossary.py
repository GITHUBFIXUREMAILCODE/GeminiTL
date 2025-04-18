import os
import time
import re
from vertexai.generative_models import GenerativeModel, GenerationConfig
from .config import SAFETY_SETTING
from .context_aware_glossary import split_glossary
###############################################################################
# Adjustable Glossary File Paths
###############################################################################

# Default file name, in the same directory as glossary.py
DEFAULT_GLOSSARY_PATH = os.path.join(os.path.dirname(__file__), "glossary.txt")

# This is the file currently chosen for glossary usage. It starts as DEFAULT_GLOSSARY_PATH,
# but can be changed at runtime.
CURRENT_GLOSSARY_PATH = DEFAULT_GLOSSARY_PATH

def set_current_glossary_file(custom_path):
    """
    Lets you specify a different glossary file at runtime.
    """
    global CURRENT_GLOSSARY_PATH
    CURRENT_GLOSSARY_PATH = custom_path
    
    # Ensure the file exists
    ensure_glossary_exists(custom_path)

def get_current_glossary_file():
    """
    Returns whichever glossary file is currently set (default or user-chosen).
    """
    return CURRENT_GLOSSARY_PATH

###############################################################################
# Glossary Utilities
###############################################################################

def ensure_glossary_exists(glossary_filename):
    """
    Ensures that the given glossary file exists. If not, creates an empty file.
    """
    if not os.path.exists(glossary_filename):
        with open(glossary_filename, "w", encoding="utf-8") as f:
            f.write("==================================== GLOSSARY START ===============================\n")
            f.write("==================================== GLOSSARY END =================================\n")
        print(f"[GLOSSARY] Created new file: {glossary_filename}")

def normalize_term(term):
    """
    Normalize a glossary term for duplicate checking.
    Currently, we just strip surrounding whitespace.
    """
    return term.strip()

###############################################################################
# Core Glossary-Building Function
###############################################################################

def build_glossary(input_text, log_message, glossary_filename=None,
                   max_retries=2, retry_delay=60):
    """
    Uses a GPT-based model to extract named entities from the provided text and
    update the local glossary file.

    If glossary_filename is None, we use get_current_glossary_file() (the file
    currently selected at runtime). Otherwise, we create/use the specified path.

    The model is instructed to output lines of the form:
        Non-English => ENGLISH => Gender Pronoun
    or:
        No named entities found.

    New terms are appended to the chosen glossary file, skipping duplicates.
    Returns the combined (existing + new) glossary content as a string.
    """
    # Decide which glossary file to use
    if glossary_filename is None:
        glossary_filename = get_current_glossary_file()

    # Ensure the file exists first
    ensure_glossary_exists(glossary_filename)

    # Load existing glossary entries from the file
    existing_glossary = []
    if os.path.exists(glossary_filename):
        with open(glossary_filename, "r", encoding="utf-8") as f:
            content = f.read()
            # Split content by markers and get the middle section
            parts = content.split("==================================== GLOSSARY START ===============================")
            if len(parts) > 1:
                middle = parts[1].split("==================================== GLOSSARY END ================================")[0]
                existing_glossary = [line for line in middle.splitlines() if line.strip()]

    GLOSSARY_INSTRUCTIONS = [
        "Extract a glossary of Non-English proper nouns (places, people, unique terms) from the given text.",
        "For each unique Non-English term, provide a recommended English translation and gender pronoun ONLY.",
        "Output only lines of the form: Non-English => English => Gender Pronoun, with proper capitalization.",
        "Gender pronouns should be one of: he/him, she/her, they/them, or it/its.",
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
            # Generate the glossary text from input
            response = gloss_model.generate_content(input_text)
            new_glossary = response.text.strip()
            log_message(f"[DEBUG] Raw glossary response: {new_glossary}")

            # Check if the model found no new terms
            if not new_glossary or "No named entities found" in new_glossary:
                log_message("[GLOSSARY] No new terms found.")
                return ""

            # Parse the AI response to extract glossary entries (Non-English => ENGLISH => Gender Pronoun)
            glossary_entries = []
            for line in new_glossary.split("\n"):
                parts = line.split("=>")
                if len(parts) == 3:  # Now expecting 3 parts
                    term = parts[0].strip()
                    meaning = parts[1].strip()
                    gender = parts[2].strip()
                    glossary_entries.append(f"{term} => {meaning} => {gender}")

            if not glossary_entries:
                log_message("[GLOSSARY] No valid glossary terms extracted.")
                return ""

            # Build a set of normalized terms already in the glossary
            existing_original_terms = set()
            for entry in existing_glossary:
                parts = entry.split("=>")
                if len(parts) == 3:  # Now expecting 3 parts
                    existing_original_terms.add(normalize_term(parts[0]))

            # Determine which entries are new
            updated_entries = []
            for entry in glossary_entries:
                parts = entry.split("=>")
                if len(parts) == 3:  # Now expecting 3 parts
                    term = parts[0].strip()
                    if normalize_term(term) not in existing_original_terms:
                        updated_entries.append(entry)
                        existing_original_terms.add(normalize_term(term))
                    else:
                        log_message(f"[DEBUG] Term '{term}' is already in {glossary_filename}; skipping.")

            # Write new entries to the file if any are found
            if updated_entries:
                log_message(f"[DEBUG] Writing {len(updated_entries)} new terms to {glossary_filename}")
                try:
                    # Read the current content
                    with open(glossary_filename, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # Split content by markers
                    parts = content.split("==================================== GLOSSARY START ===============================")
                    if len(parts) > 1:
                        middle = parts[1].split("==================================== GLOSSARY END ================================")[0]
                        # Combine existing and new entries
                        all_entries = [line for line in middle.splitlines() if line.strip()] + updated_entries
                        # Remove duplicates while preserving order
                        seen = set()
                        unique_entries = []
                        for entry in all_entries:
                            if entry not in seen:
                                seen.add(entry)
                                unique_entries.append(entry)
                        
                        # Write back with markers
                        with open(glossary_filename, "w", encoding="utf-8") as f:
                            f.write("==================================== GLOSSARY START ===============================\n")
                            f.write("\n".join(unique_entries) + "\n")
                            f.write("==================================== GLOSSARY END ================================\n")
                    else:
                        # If markers are missing, write new content with markers
                        with open(glossary_filename, "w", encoding="utf-8") as f:
                            f.write("==================================== GLOSSARY START ===============================\n")
                            f.write("\n".join(updated_entries) + "\n")
                            f.write("==================================== GLOSSARY END ================================\n")
                    
                    log_message(f"[GLOSSARY] Updated {glossary_filename} with {len(updated_entries)} new terms.")
                except Exception as e:
                    log_message(f"[ERROR] Failed to write {glossary_filename}: {e}")

                # Debug: Check final file content
                try:
                    with open(glossary_filename, "r", encoding="utf-8") as f:
                        content = f.read()
                    log_message(f"[DEBUG] Final glossary content:\n{content}")
                except Exception as e:
                    log_message(f"[ERROR] Failed to verify written glossary: {e}")
            else:
                log_message(f"[GLOSSARY] No new terms to add to {glossary_filename}; all extracted terms are duplicates.")

            # Automatically split the glossary into name/context parts
            try:
                split_glossary(glossary_filename)
                log_message("[GLOSSARY] Successfully split glossary into name/context files.")
            except Exception as e:
                log_message(f"[GLOSSARY] Failed to split glossary: {e}")

            # Return the combined (existing + new) glossary
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
