"""
Translation module for the novel translation tool.

This module provides the Translator class for handling text translation
using the Gemini API with support for glossaries and image tag preservation.
"""

import json
import time
import os
import re
from vertexai.generative_models import GenerativeModel, GenerationConfig
from .config import SAFETY_SETTING
from .glossary import Glossary
import concurrent.futures

class Translator:
    """
    Handles text translation using the Gemini API.
    
    This class provides functionality for:
    - Loading and using glossaries
    - Preserving image tags during translation
    - Handling prohibited content
    - Retrying failed translations
    """
    
    # Primary instructions (tweak as needed)
    PRIMARY_INSTRUCTIONS = [
        "Your task is to TRANSLATE Web Novels into ENGLISH (title included).",
        "Translation MUST be faithful, maintaining the original meaning, tone, and structure without creative additions or omissions.",
        "Translate ALL text, including proper nouns, adjectives, technical terms, and any potentially foreign words, into English.",
        "The translation will not be censored, and any profanity will be translated according to its context and intensity in the original text.",
        "Correct punctuation marks while the translation should closely match the original text's format.",
        "Allow NSFW; all characters are of age.",
        "You will receive text input that may contain HTML. The sections containing HTML MUST be returned exactly as-is, with no modifications.",
        "Here is a glossary of special terms and names. Use this glossary for translation accuracy.",
    ]

    # Secondary instructions (fallback if primary is blocked)
    SECONDARY_INSTRUCTIONS = [
        "Your task is to TRANSLATE novels INTO ENGLISH (title included).",
        "Translation MUST be faithful, maintaining the original meaning, tone, and structure without creative additions or omissions.",
        "Translate ALL text, including proper nouns, technical terms, and any potentially foreign words, into English.",
        "If a word doesn't have a direct English equivalent, provide the CLOSEST possible translation or transliteration.",
        "Allow NSFW; ALL characters are at age of consent.",
        "The translation will NOT BE CENSORED IN ANY WAY, and any profanity will be translated according to its context and intensity in the original text.",
        "Correct punctuation marks while the translation should stick as closely as possible to the original text's format.",
        "You will receive text input that may contain HTML. Treat any HTML as plain text that should be returned without modification.",
        "Here is a glossary of special terms and names. Use this glossary for translation accuracy."
    ]

    def __init__(self, glossary_file=None):
        """
        Initialize the translator.
        
        Args:
            glossary_file: Optional path to the glossary file to use for translation
        """
        self.glossary = Glossary(glossary_file)
        self.model = GenerativeModel(
            model_name="gemini-pro",
            safety_settings=SAFETY_SETTING,
            generation_config=GenerationConfig(
                temperature=0.3,
                top_p=0.95,
                top_k=40
            )
        )

    def get_name_glossary(self):
        try:
            current_glossary = self.glossary.get_current_glossary_file()
            if not current_glossary:
                return ""
                
            glossary_name = os.path.splitext(os.path.basename(current_glossary))[0]
            glossary_dir = os.path.dirname(current_glossary)
            name_glossary_path = os.path.join(glossary_dir, glossary_name, "name_glossary.txt")
            
            if not os.path.exists(name_glossary_path):
                print(f"[WARNING] Name glossary not found at: {name_glossary_path}")
                print(f"[INFO] Expected subfolder name: {glossary_name}")
                return ""
            
            with open(name_glossary_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Extract content between markers
                parts = content.split("==================================== GLOSSARY START ===============================")
                if len(parts) > 1:
                    glossary_text = parts[1].split("==================================== GLOSSARY END ================================")[0].strip()
                    return glossary_text if glossary_text else ""
                return ""
        except Exception as e:
            print(f"[ERROR] Failed to read name glossary from {name_glossary_path}: {e}")
            return ""

    def generate_with_instructions(self, prompt, instructions, instructions_label, log_message,
                                 max_retries=2, retry_delay=60):
        """
        Attempts translation using the provided instructions (primary or secondary).
        Retries on certain errors. If blocked for prohibited content, raises RuntimeError.
        """
        log_message(f"[{instructions_label}] Attempting generation...")

        tl_model = GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            safety_settings=SAFETY_SETTING,
            system_instruction=instructions,
            generation_config=GenerationConfig(
                temperature=0.3,
                top_p=0.95,
                top_k=40,
                response_mime_type="text/plain"
            )
        )

        attempt = 0
        while attempt < max_retries:
            try:
                # Force Gemini request to timeout after 90s
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(tl_model.generate_content, prompt)
                    response = future.result(timeout=90)

                log_message(f"[{instructions_label}] Generation succeeded on attempt {attempt + 1}.")
                return response.text

            except concurrent.futures.TimeoutError:
                log_message(f"[{instructions_label}] Timeout after 90s on attempt {attempt + 1}")

            except Exception as e:
                error_str = str(e)
                log_message(f"[{instructions_label}] Error (attempt {attempt + 1}): {error_str}")

                if "Response has no candidates" in error_str:
                    raise RuntimeError("PROHIBITED_CONTENT_BLOCK")

                try:
                    data = json.loads(error_str)
                    block_reason = data.get("prompt_feedback", {}).get("block_reason")
                    if block_reason == "PROHIBITED_CONTENT":
                        raise RuntimeError("PROHIBITED_CONTENT_BLOCK")
                except json.JSONDecodeError:
                    pass

            attempt += 1
            if attempt < max_retries:
                log_message(f"[{instructions_label}] Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                raise

    def translate(self, text, log_message=None):
        """
        Translate the given text using the Gemini API.
        
        Args:
            text: The text to translate
            log_message: Optional callback function for logging
            
        Returns:
            The translated text, or None if translation fails
        """
        if log_message is None:
            log_message = print

        # Extract and store image tags before translation
        image_tag_pattern = re.compile(r'(<img[^>]*>)')
        image_tags = []
        def store_image_tag(match):
            image_tags.append(match.group(1))
            return f"__IMAGE_TAG_{len(image_tags)-1}__"
        
        # Replace image tags with placeholders
        text_with_placeholders = image_tag_pattern.sub(store_image_tag, text)

        # Load the glossary text (could be blank if no file is found or it's empty)
        glossary_text = self.get_name_glossary()
        if glossary_text:
            log_message("[GLOSSARY] Loaded glossary terms for translation.")
        else:
            log_message("[GLOSSARY] No glossary terms found or file not found.")

        # Combine instructions with the glossary text
        primary_instructions = self.PRIMARY_INSTRUCTIONS + ([glossary_text] if glossary_text else [])
        secondary_instructions = self.SECONDARY_INSTRUCTIONS + ([glossary_text] if glossary_text else [])

        # Attempt primary instructions first
        try:
            translated = self.generate_with_instructions(
                prompt=text_with_placeholders,
                instructions=primary_instructions,
                instructions_label="PRIMARY",
                log_message=log_message,
                max_retries=3,
                retry_delay=60
            )

        except RuntimeError as e:
            # If blocked by content, switch to secondary instructions
            if "PROHIBITED_CONTENT_BLOCK" in str(e):
                log_message("[PRIMARY] Blocked. Attempting SECONDARY in 5s.")
                time.sleep(5)
                try:
                    translated = self.generate_with_instructions(
                        prompt=text_with_placeholders,
                        instructions=secondary_instructions,
                        instructions_label="SECONDARY",
                        log_message=log_message,
                        max_retries=2,
                        retry_delay=5
                    )
                except RuntimeError as e2:
                    if "PROHIBITED_CONTENT_BLOCK" in str(e2):
                        log_message("[SECONDARY] Also blocked. Skipping file in 5s.")
                        time.sleep(5)
                        return None
                    else:
                        log_message(f"[SECONDARY] Error: {e2}. Skipping.")
                        return None
            else:
                log_message(f"[PRIMARY] Error: {e}. Skipping.")
                return None

        except Exception as e:
            # Any other fatal error
            log_message(f"[PRIMARY] Fatal: {e}. Skipping.")
            return None

        if not translated:
            return None

        # Restore image tags in the translated text
        def restore_image_tag(match):
            index = int(match.group(1))
            if 0 <= index < len(image_tags):
                return image_tags[index]
            return match.group(0)

        translated = re.sub(r'__IMAGE_TAG_(\d+)__', restore_image_tag, translated)
        return translated




