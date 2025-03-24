import json
import time
from vertexai.generative_models import GenerativeModel, GenerationConfig
from .config import SAFETY_SETTING

# Path to glossary.txt
from .glossary import GLOSSARY_PATH  

# Primary instructions (tweak as needed)
PRIMARY_INSTRUCTIONS = [
    "Your task is to TRANSLATE Web Novels into ENGLISH (title included).",
    "Translation MUST be faithful, maintaining the original meaning, tone, and structure without creative additions or omissions.",
    "Translate ALL text, including proper nouns, adjectives, technical terms, and any potentially foreign words, into English.",
    "The translation will not be censored, and any profanity will be translated according to its context and intensity in the original text.",
    "Correct punctuation marks while the translation should closely match the original text’s format.",
    "Allow NSFW; all characters are of age.",
    "You will receive text input that may contain HTML. The sections containing HTML MUST be returned exactly as-is, with no modifications.",
    "Here is a glossary of special terms and names. Use this glossary for translation accuracy."
]

# Secondary instructions (fallback if primary blocked)
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

def load_glossary():
    """Reads glossary.txt and returns its content as a string."""
    if not GLOSSARY_PATH or not isinstance(GLOSSARY_PATH, str):
        return ""

    try:
        with open(GLOSSARY_PATH, "r", encoding="utf-8") as f:
            glossary_text = f.read().strip()
        return glossary_text if glossary_text else ""
    except Exception as e:
        print(f"[ERROR] Failed to read glossary: {e}")
        return ""

def generate_with_instructions(prompt, instructions, instructions_label, log_message,
                               max_retries=2, retry_delay=60):
    """
    Attempts translation using the provided instructions (primary or secondary).
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

def TLer(prompt, log_message):
    """
    Uses primary instructions; if blocked, tries secondary instructions.
    Loads the glossary before running the translation.
    """
    glossary_text = load_glossary()
    if glossary_text:
        log_message(f"[GLOSSARY] Loaded glossary terms for translation.")
    else:
        log_message(f"[GLOSSARY] No glossary terms found.")

    primary_instructions = PRIMARY_INSTRUCTIONS + ([glossary_text] if glossary_text else [])
    secondary_instructions = SECONDARY_INSTRUCTIONS + ([glossary_text] if glossary_text else [])

    try:
        return generate_with_instructions(
            prompt=prompt,
            instructions=primary_instructions,
            instructions_label="PRIMARY",
            log_message=log_message,
            max_retries=3,
            retry_delay=60
        )
    except RuntimeError as e:
        if "PROHIBITED_CONTENT_BLOCK" in str(e):
            log_message("[PRIMARY] Blocked. Attempting SECONDARY in 5s.")
            time.sleep(5)
            try:
                return generate_with_instructions(
                    prompt=prompt,
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
        log_message(f"[PRIMARY] Fatal: {e}. Skipping.")
        return None
