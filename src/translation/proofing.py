# proofing.py

import os
import unicodedata
import re
from vertexai.generative_models import GenerativeModel, GenerationConfig
from .config import SAFETY_SETTING
from .translator import TLer

def contains_non_english_letters(text: str) -> bool:
    """
    Return True if 'text' contains any letters that are not 'LATIN' in Unicode,
    which means they are likely non-English letters. Punctuation/symbols are ignored.
    """
    for char in text:
        if char.isalpha():
            name = unicodedata.name(char, "")
            if "LATIN" not in name:
                return True
    return False

def load_context_glossary(glossary_path):
    """
    Loads the context glossary (English => Gender Pronoun) from the subfolder.
    Returns a dictionary mapping English names to their gender pronouns.
    """
    try:
        # Get the subfolder path (same name as glossary without extension)
        glossary_name = os.path.splitext(os.path.basename(glossary_path))[0]
        glossary_dir = os.path.dirname(glossary_path)
        context_glossary_path = os.path.join(glossary_dir, glossary_name, "context_glossary.txt")
        
        context_dict = {}
        with open(context_glossary_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Extract content between markers
            parts = content.split("==================================== GLOSSARY START ===============================")
            if len(parts) > 1:
                glossary_text = parts[1].split("==================================== GLOSSARY END ================================")[0].strip()
                for line in glossary_text.splitlines():
                    if '=>' in line:
                        english, gender = map(str.strip, line.split('=>'))
                        context_dict[english] = gender
        return context_dict
    except Exception as e:
        print(f"[ERROR] Failed to read context glossary: {e}")
        return {}

def proof_gender_pronouns(text: str, context_dict: dict, log_message) -> str:
    """
    Uses Vertex AI to proofread and correct gender pronouns in the text based on the context glossary.
    """
    if not context_dict:
        return text

    PROOFING_INSTRUCTIONS = [
        "Your task is to FIND and EDIT pronouns of the input so it is correct.",
        "Correct punctuation marks in the proofing should closely match the original text's format.",
        "Allow NSFW; all characters are of age.",
        "You will receive text input that may contain HTML. The sections containing HTML MUST be returned exactly as-is, with no modifications.",
        "Here is a glossary of special terms and names. Use this glossary for translation accuracy.",
    ]

    # Format the context information as a glossary
    context_glossary = "\n".join([f"{name} => {gender}" for name, gender in context_dict.items()])
    
    # Combine instructions with the context glossary
    instructions = PROOFING_INSTRUCTIONS + [context_glossary]

    proof_model = GenerativeModel(
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

    try:
        response = proof_model.generate_content(text)
        return response.text
    except Exception as e:
        log_message(f"[ERROR] Failed to proof gender pronouns: {e}")
        return text

def detect_and_log_non_english_lines(
    log_message,
    output_dir: str,
    log_file_path: str,
    input_dir: str
):
    """
    Scans the translated files in 'output_dir' for lines containing non-English characters.
    - Writes those lines to 'log_file_path'.
    - For each non-English line, attempts to re-translate it from the corresponding line
      in the matching input file. If re-translation succeeds, we replace the line
      in the translated file with the re-translated content.
    """
    with open(log_file_path, "w", encoding="utf-8") as log_file:
        # Look for all "translated_*.txt" files and sort them numerically
        text_files = [f for f in os.listdir(output_dir) if f.startswith("translated_") and f.endswith(".txt")]
        text_files.sort(key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else float('inf'))
        
        for fname in text_files:
            # The original file name (input) is the same but without 'translated_'
            original_fname = fname.replace("translated_", "", 1)
            out_file_path = os.path.join(output_dir, fname)
            in_file_path = os.path.join(input_dir, original_fname)

            # Skip if original input file doesn't exist
            if not os.path.exists(in_file_path):
                log_message(f"[WARNING] Original file not found for {fname}: {original_fname}")
                continue

            try:
                # Read the lines from the output (already translated)
                with open(out_file_path, "r", encoding="utf-8") as f_out:
                    output_lines = f_out.readlines()

                # Read all lines from the original input
                with open(in_file_path, "r", encoding="utf-8") as f_in:
                    input_lines = f_in.readlines()

                # If line counts differ, line-by-line matching might be off, but
                # we will do a best-effort approach (min of both lengths).
                max_lines = min(len(output_lines), len(input_lines))

                # We'll keep track if we changed anything
                changed_something = False

                # Check for non-English lines and re-translate them
                for line_num in range(max_lines):
                    out_line = output_lines[line_num]
                    if contains_non_english_letters(out_line):
                        # Log the line
                        log_message(f"[WARNING] Non-English text in {fname} (line {line_num+1}).")
                        log_file.write(f"File: {fname}, Line {line_num+1}:\n{out_line}\n")

                        # Attempt re-translation from the original input line
                        original_line = input_lines[line_num]
                        retranslated_line = TLer(original_line, log_message)

                        # If retranslation succeeded, replace the output line
                        if retranslated_line:
                            output_lines[line_num] = retranslated_line
                            changed_something = True
                        else:
                            log_message(f"[WARNING] Re-translation blocked or failed for {fname}, line {line_num+1}.")

                # If we changed something, rewrite the output file with updated lines
                if changed_something:
                    with open(out_file_path, "w", encoding="utf-8") as f_out:
                        f_out.writelines(output_lines)
                    log_message(f"[OK] Updated lines in {fname} after re-translation.")

            except Exception as e:
                log_message(f"[ERROR processing {fname}]: {e}")

def proof_gender_pronouns_for_all_files(
    log_message,
    output_dir: str,
    input_dir: str
):
    """
    Scans all translated files in 'output_dir' and runs gender pronoun proofing on each file.
    Uses the context glossary from the input directory's glossary subfolder.
    """
    # Load the context glossary
    glossary_path = os.path.join(os.path.dirname(__file__), "glossary.txt")
    context_dict = load_context_glossary(glossary_path)
    if context_dict:
        log_message("[PROOFING] Loaded context glossary for gender pronoun proofing.")
    else:
        log_message("[PROOFING] No context glossary found. Skipping gender pronoun proofing.")
        return

    # Look for all "translated_*.txt" files and sort them numerically
    text_files = [f for f in os.listdir(output_dir) if f.startswith("translated_") and f.endswith(".txt")]
    text_files.sort(key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else float('inf'))
    
    for fname in text_files:
        try:
            out_file_path = os.path.join(output_dir, fname)
            log_message(f"[PROOFING] Running gender pronoun proofing on {fname}...")
            
            with open(out_file_path, "r", encoding="utf-8") as f_out:
                content = f_out.read()
            
            proofed_content = proof_gender_pronouns(content, context_dict, log_message)
            
            if proofed_content != content:
                with open(out_file_path, "w", encoding="utf-8") as f_out:
                    f_out.write(proofed_content)
                log_message(f"[OK] Updated gender pronouns in {fname}.")

        except Exception as e:
            log_message(f"[ERROR processing {fname}]: {e}")

def proof_all_files(
    log_message,
    output_dir: str,
    log_file_path: str,
    input_dir: str
):
    """
    Runs both non-English line detection and gender pronoun proofing on all files.
    """
    # First run non-English line detection
    detect_and_log_non_english_lines(log_message, output_dir, log_file_path, input_dir)
    
    # Then run gender pronoun proofing
    proof_gender_pronouns_for_all_files(log_message, output_dir, input_dir)

def inject_context(input_text, context_dict):
    injected_lines = [f"{name} is {desc}." for name, desc in context_dict.items()]
    context_header = "Context: " + " ".join(injected_lines)
    return f"{context_header}\n\n{input_text}"
