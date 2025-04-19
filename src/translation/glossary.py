"""
Glossary management module for the novel translation tool.

This module provides functionality for:
- Managing glossary files
- Building and updating glossaries
- Normalizing terms
"""

import os
import time
import re
from vertexai.generative_models import GenerativeModel, GenerationConfig
from .config import SAFETY_SETTING
from .context_aware_glossary import split_glossary

###############################################################################
# Glossary Management
###############################################################################

class Glossary:
    """
    Manages glossary operations for the translation tool.
    
    This class provides functionality for:
    - Managing glossary files
    - Building and updating glossaries
    - Normalizing terms
    """
    
    # Default file name, in the same directory as glossary.py
    DEFAULT_GLOSSARY_PATH = os.path.join(os.path.dirname(__file__), "glossary.txt")
    
    def __init__(self, glossary_path=None):
        """
        Initialize the glossary manager.
        
        Args:
            glossary_path: Optional path to a custom glossary file
        """
        self.current_glossary_path = glossary_path or self.DEFAULT_GLOSSARY_PATH
        self.ensure_glossary_exists(self.current_glossary_path)
        
    def set_current_glossary_file(self, custom_path):
        """
        Set a different glossary file to use.
        
        Args:
            custom_path: Path to the new glossary file
        """
        self.current_glossary_path = custom_path
        self.ensure_glossary_exists(custom_path)
        
    def get_current_glossary_file(self):
        """
        Get the current glossary file path.
        
        Returns:
            str: Path to the current glossary file
        """
        return self.current_glossary_path
        
    def ensure_glossary_exists(self, glossary_filename):
        """
        Ensure that the given glossary file exists.
        If not, creates an empty file.
        
        Args:
            glossary_filename: Path to the glossary file
        """
        if not os.path.exists(glossary_filename):
            with open(glossary_filename, "w", encoding="utf-8") as f:
                f.write("==================================== GLOSSARY START ===============================\n")
                f.write("==================================== GLOSSARY END =================================\n")
            print(f"[GLOSSARY] Created new file: {glossary_filename}")
            
    def normalize_term(self, term):
        """
        Normalize a glossary term for duplicate checking.
        Remove special characters and extra spaces.
        
        Args:
            term: The term to normalize
            
        Returns:
            str: Normalized term
        """
        # Remove special characters except spaces, keep only alphanumeric
        normalized = re.sub(r'[^\w\s]', '', term)
        # Normalize whitespace
        normalized = re.sub(r'\s+', ' ', normalized.strip().lower())
        return normalized
        
    def build_glossary(self, input_text, log_message, glossary_filename=None,
                       max_retries=2, retry_delay=60, split_glossary=True):
        """
        Build a glossary from input text.
        
        Args:
            input_text: Text to analyze for glossary terms
            log_message: Callback for logging messages
            glossary_filename: Optional path to save the glossary
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            split_glossary: Whether to split the glossary after updating (default: True)
            
        Returns:
            str: The built glossary text
        """
        # Use provided filename or current glossary path
        glossary_filename = glossary_filename or self.current_glossary_path

        # Ensure the file exists first
        self.ensure_glossary_exists(glossary_filename)

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
            "Output only lines of the form: Non-English Original Text => English => Gender Pronoun, with proper capitalization.",
            "Gender pronouns should be one of: he/him, she/her, they/them, or it/its.",
            "If no named entities are found, write: No named entities found.",
            "Remove any special characters that are not letters or numbers from the terms."
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
                # Call the API without using signal alarms.
                response = gloss_model.generate_content(input_text)
                new_glossary = response.text.strip()

                # Check if the model found no new terms
                if not new_glossary or "No named entities found" in new_glossary:
                    log_message("[GLOSSARY] No new terms found.")
                    return ""

                # Parse the AI response to extract glossary entries (Non-English => ENGLISH => Gender Pronoun)
                glossary_entries = []
                for line in new_glossary.split("\n"):
                    parts = line.split("=>")
                    if len(parts) == 3:
                        # Clean and normalize each part while preserving original case
                        term = re.sub(r'[^\w\s]', '', parts[0].strip())
                        meaning = re.sub(r'[^\w\s]', '', parts[1].strip())
                        gender = parts[2].strip()  # Keep gender pronouns as-is
                        if term and meaning:  # Only add if term and meaning are not empty
                            glossary_entries.append(f"{term} => {meaning} => {gender}")

                if not glossary_entries:
                    log_message("[GLOSSARY] No valid glossary terms extracted.")
                    return ""

                # Build a set of normalized terms already in the glossary
                existing_original_terms = set()
                for entry in existing_glossary:
                    parts = entry.split("=>")
                    if len(parts) == 3:
                        existing_original_terms.add(self.normalize_term(parts[0]))

                # Determine which entries are new
                updated_entries = []
                for entry in glossary_entries:
                    parts = entry.split("=>")
                    if len(parts) == 3:
                        term = parts[0].strip()
                        if self.normalize_term(term) not in existing_original_terms:
                            updated_entries.append(entry)
                            existing_original_terms.add(self.normalize_term(term))

                # Write new entries to the file if any are found
                if updated_entries:
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
                else:
                    log_message(f"[GLOSSARY] No new terms to add to {glossary_filename}; all extracted terms are duplicates.")

                # Only split the glossary if requested
                if split_glossary:
                    try:
                        from .context_aware_glossary import split_glossary
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

# For backward compatibility
def get_current_glossary_file():
    """Get the current glossary file path."""
    return Glossary().get_current_glossary_file()

def set_current_glossary_file(custom_path):
    """Set a different glossary file to use."""
    Glossary().set_current_glossary_file(custom_path)

def ensure_glossary_exists(glossary_filename):
    """Ensure that the given glossary file exists."""
    Glossary().ensure_glossary_exists(glossary_filename)

def normalize_term(term):
    """Normalize a glossary term for duplicate checking."""
    return Glossary().normalize_term(term)

def build_glossary(input_text, log_message, glossary_filename=None,
                   max_retries=2, retry_delay=60, split_glossary=True):
    """Build a glossary from input text."""
    return Glossary().build_glossary(input_text, log_message, glossary_filename,
                                     max_retries, retry_delay, split_glossary)


