import json
import time
import os
import re
from vertexai.generative_models import GenerativeModel, GenerationConfig
from .config import SAFETY_SETTING

# Import the function to get whichever glossary file is "current."
# That file can be changed at runtime by calling set_current_glossary_file(...)
# in glossary.py.
from .glossary import get_current_glossary_file

###############################################################################
# Translation Instructions
###############################################################################

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

###############################################################################
# Glossary Loading
###############################################################################

def load_glossary():
    """
    Reads the name_glossary file from the subfolder of the current glossary.
    Returns its content as a string. If the file doesn't exist or fails to read, returns "".
    """
    glossary_path = get_current_glossary_file()
    try:
        # Get the subfolder path (same name as glossary without extension)
        glossary_name = os.path.splitext(os.path.basename(glossary_path))[0]
        glossary_dir = os.path.dirname(glossary_path)
        name_glossary_path = os.path.join(glossary_dir, glossary_name, "name_glossary.txt")
        
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

###############################################################################
# Core Translation Logic
###############################################################################

def generate_with_instructions(prompt, instructions, instructions_label, log_message,
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
            temperature=0.7,
            top_p=0.95,
            top_k=40,
            response_mime_type="text/plain"
        )
    )

    attempt = 0
    while attempt < max_retries:
        try:
            response = tl_model.generate_content(prompt)
            log_message(f"[{instructions_label}] Generation succeeded on attempt {attempt+1}.")
            return response.text
        except Exception as e:
            error_str = str(e)
            log_message(f"[{instructions_label}] Error (attempt {attempt+1}): {error_str}")

            # If the error indicates prohibited content, raise a specific exception
            if "Response has no candidates" in error_str:
                raise RuntimeError("PROHIBITED_CONTENT_BLOCK")

            # Check JSON structure in the error in case we get additional feedback
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

def TLer(prompt, log_message):
    """
    1) Loads the current glossary file set in glossary.py.
    2) Uses PRIMARY_INSTRUCTIONS for translation.
    3) If blocked for prohibited content, tries SECONDARY_INSTRUCTIONS.
    4) If all attempts fail, returns None.
    5) Preserves image tags during translation.
    """
    # Extract and store image tags before translation
    image_tag_pattern = re.compile(r'(<img[^>]*>)')
    image_tags = []
    def store_image_tag(match):
        image_tags.append(match.group(1))
        return f"__IMAGE_TAG_{len(image_tags)-1}__"
    
    # Replace image tags with placeholders
    text_with_placeholders = image_tag_pattern.sub(store_image_tag, prompt)

    # Load the glossary text (could be blank if no file is found or it's empty)
    glossary_text = load_glossary()
    if glossary_text:
        log_message("[GLOSSARY] Loaded glossary terms for translation.")
    else:
        log_message("[GLOSSARY] No glossary terms found or file not found.")

    # Combine instructions with the glossary text
    primary_instructions = PRIMARY_INSTRUCTIONS + ([glossary_text] if glossary_text else [])
    secondary_instructions = SECONDARY_INSTRUCTIONS + ([glossary_text] if glossary_text else [])

    # Attempt primary instructions first
    try:
        translated = generate_with_instructions(
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
                translated = generate_with_instructions(
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
