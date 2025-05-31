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
from config.config import SAFETY_SETTING
from glossary.glossary import glossary
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
    
    
    def build_instructions(self, base, glossary_text=None):
        lang_hint = f"Translate the following {self.source_lang} text into fluent English."
        instructions = [lang_hint] + base
        if glossary_text:
            instructions.append(glossary_text)
        return instructions


# Primary instructions (tweak as needed)
    PRIMARY_INSTRUCTIONS = [
        "You are tasked with TRANSLATING web novels into ENGLISH, including the title.",
        "Your translation MUST be strictly faithful to the original—preserve all meaning, tone, structure, and nuance without adding or omitting anything.",
        "Translate ALL content: proper nouns, adjectives, technical terms, and any foreign-language words into English.",
        "DO NOT censor profanity or NSFW content. Translate explicit language according to its original tone and intensity.",
        "Correct punctuation and grammar as needed, but preserve the original formatting and layout as much as possible.",
        "NSFW content is allowed. All characters are confirmed to be of legal age.",
        "HTML markdowns may appear in the text. These MUST be returned **exactly as-is**, with zero alterations in your response.",
        "Use the provided glossary for all character names, terms, and special vocabulary. Follow it exactly.",
        "**You MUST output only the translated English version of the text.**",
        "**DO NOT output the original source language.**",
        "**DO NOT summarize, explain, annotate, or comment on the text.**",
        "Do not add any introductions, summaries, explanations, or meta commentary.",
        "**If the input text is already in English, output it unchanged.**",
        "**Onomatopoeia / Sound‑effect rules**",
        "• Any sound effect that is just one kana, hangul syllable, or any set of repeated ASCII letters (ドドド, ㅋㅋㅋ, DoDoDo, IIIII) must be romanised or transliterated **then compressed** to a maximum of four (4) visible repetitions.",
        "• Mixed‑syllable SFX (ガシャーン, 타다닥) keep their full pattern but **may not exceed 20 total characters** once romanised.",
        "• Under no circumstances output an endless run of the same Latin letter or digit.",
        "• If you are unsure, err on the side of shortening rather than lengthening.",
        "**You MUST output only the translated English text that obeys all rules above.**",
        ]


    # Secondary instructions (fallback if primary is blocked)
    SECONDARY_INSTRUCTIONS = [
    "You are translating a novel into ENGLISH, including the title.",
    "Translation MUST be faithful—preserve the original meaning, tone, and sentence structure without unnecessary changes.",
    "Translate ALL content, including proper nouns, foreign terms, and technical language, into English.",
    "If a word has no direct English equivalent, use the closest accurate translation or transliteration.",
    "Profanity and NSFW content must be translated as-is. Do NOT censor. All characters are of legal age.",
    "Preserve the original formatting, punctuation, and structure where possible while ensuring natural English flow.",
    "HTML tags may be included in the text. Return them unchanged, exactly as they appear.",
    "• Any sound effect that is just one kana, hangul syllable, or any set of repeated ASCII letters (ドドド, ㅋㅋㅋ, DoDoDo, IIIII) must be romanised or transliterated **then compressed** to a maximum of four (4) visible repetitions.",
    "• Mixed‑syllable SFX (ガシャーン, 타다닥) keep their full pattern but **may not exceed 20 total characters** once romanised.",
    "• Under no circumstances output an endless run of the same Latin letter or digit.",
    "• If you are unsure, err on the side of shortening rather than lengthening.",
    "**You MUST output only the translated English text that obeys all rules above.**",
    "Use the attached glossary to ensure accurate term usage and consistency. Follow it strictly.",
    ]


    def __init__(self, glossary_file=None, source_lang='Japanese'):
        """
        Initialize the translator.
        
        Args:
            glossary_file: Optional path to the glossary file to use for translation
        """
        self.source_lang = source_lang
        self.model_name = "gemini-2.0-flash-exp"  # Track what model is active
        self.initialize_model(self.model_name)
        self.glossary = Glossary(glossary_file)
        self.model = GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            safety_settings=SAFETY_SETTING,
            generation_config=GenerationConfig(
                temperature=0.4,
                top_p=0.95,
                top_k=40
            )
        )

    def initialize_model(self, model_name):
        self.model_name = model_name
        self.model = GenerativeModel(
            model_name=self.model_name,
            safety_settings=SAFETY_SETTING,
            generation_config=GenerationConfig(
                temperature=0.4,
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
                                    max_retries=2, retry_delay=90):
        """
        Attempts translation using the provided instructions (primary or secondary).
        Retries on certain errors. If blocked for prohibited content, raises RuntimeError.
        """
        log_message(f"[{instructions_label}] Attempting generation...")

        # Prepend instructions to prompt
        full_prompt = "\n".join(self.build_instructions(instructions, glossary_text=None)) + "\n\n" + prompt
        tl_model = self.model

        attempt = 0
        while attempt < max_retries:
            try:
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(tl_model.generate_content, full_prompt)
                    response = future.result(timeout=180)

                log_message(f"[{instructions_label}] Generation succeeded on attempt {attempt + 1}.")
                return response.text

            except concurrent.futures.TimeoutError:
                log_message(f"[{instructions_label}] Timeout after 180s on attempt {attempt + 1}")

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
        glossary_path = self.glossary.get_current_glossary_file()
        glossary_text = ""

        if glossary_path:
            glossary_name = os.path.splitext(os.path.basename(glossary_path))[0]
            glossary_dir = os.path.dirname(glossary_path)
            name_glossary_path = os.path.join(glossary_dir, glossary_name, "name_glossary.txt")

            glossary_text = get_matched_name_glossary_entries(name_glossary_path, text, log=log_message)
            if glossary_text:
                log_message("[GLOSSARY] Using matched terms from name_glossary.")
            else:
                log_message("[GLOSSARY] No matching name glossary terms found.")
        else:
            log_message("[GLOSSARY] No glossary file path available.")


        
        # Build instruction sets with glossary
        primary_instructions = self.build_instructions(self.PRIMARY_INSTRUCTIONS, glossary_text)
        secondary_instructions = self.build_instructions(self.SECONDARY_INSTRUCTIONS, glossary_text)

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

def get_matched_name_glossary_entries(glossary_path, chapter_text, log=None):
    """
    Extract matched glossary entries from the name_glossary.txt based on content in chapter_text.
    """
    matched_entries = []
    seen = set()

    if not os.path.exists(glossary_path):
        return ""

    try:
        with open(glossary_path, "r", encoding="utf-8") as f:
            content = f.read()
        glossary_section = content.split("==================================== GLOSSARY START ===============================")
        if len(glossary_section) < 2:
            return ""
        glossary_text = glossary_section[1].split("==================================== GLOSSARY END ================================")[0].strip()
    except Exception as e:
        if log:
            log(f"[GLOSSARY] Failed to read or parse name glossary: {e}")
        return ""

    for line in glossary_text.splitlines():
        if "=>" not in line:
            continue
        parts = [p.strip() for p in line.split("=>")]
        if len(parts) < 2:
            continue
        original_term = parts[0]
        # Match using regex for word boundaries and ignore whitespace issues
        if re.search(rf'\b{re.escape(original_term)}\b', chapter_text):
            if original_term not in seen:
                matched_entries.append(line.strip())
                seen.add(original_term)

    if log:
        log(f"[GLOSSARY] Matched {len(matched_entries)} terms for this chapter.")
    return "\n".join(matched_entries)

def load_relevant_glossary(glossary_path, chapter_text, log=None):
    matched_entries = []
    seen_keys = set()
    if not os.path.exists(glossary_path):
        return matched_entries

    with open(glossary_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        if "=>" not in line:
            continue
        parts = [p.strip() for p in line.strip().split("=>")]
        if len(parts) != 3:
            continue
        original, translated, pronoun = parts
        if original in chapter_text and original not in seen_keys:
            matched_entries.append(f"{original} => {translated} => {pronoun}")
            seen_keys.add(original)

    if log:
        log(f"[GLOSSARY] Matched {len(matched_entries)} glossary terms to this chapter.")

    return matched_entries

