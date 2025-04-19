"""
Proofreading module for the novel translation tool.

This module provides functionality for:
- Proofreading translations
- Checking for common errors
- Improving translation quality
"""

import os
import time
import re
import unicodedata
from vertexai.generative_models import GenerativeModel, GenerationConfig
from .config import SAFETY_SETTING
from .translator import Translator
from .glossary import get_current_glossary_file

class Proofreader:
    """
    Handles proofreading of translations.
    
    This class provides functionality for:
    - Checking translation quality
    - Fixing common errors
    - Improving readability
    """
    
    # Define proofreading instructions at class level
    PROOFREADING_INSTRUCTIONS = [
        "You are a precise translation proofreader. "
        "Your task is to proofread and improve the English translation while maintaining the original meaning, feeling, and flow of the text.",
        "Allow NSFW; all characters are of age.",
        "but do not stylize or reformat words, exaggerate spacing, or alter emphasis or honorifics.",
        "If the translation is already perfect or is too short to proofread, return the original text without any changes.",
        "Attached is the previous chapter and the next chapter, along with the glossaries used for context."
        "After making changes, add 'Explanation:' followed by a brief summary of major changes made.",
        "You will receive text input that may contain HTML. Treat any HTML as plain text that should be returned without modification.",
    ]

    def __init__(self, log_message=None, glossary_path=None):
        self.log_message = log_message or print
        # store the custom glossary path (or None → fallback)
        self.glossary_path = glossary_path
        self.PROOFREADING_INSTRUCTIONS = "\n".join(self.PROOFREADING_INSTRUCTIONS)

    @staticmethod
    def split_into_sentences(text):
        """Basic sentence splitter using punctuation."""
        return re.split(r'(?<=[.!?])\s+', text)

    @staticmethod
    def contains_non_english_letters(text: str) -> bool:
        """
        Return True if 'text' contains any letters that are not LATIN.
        Ignores common Asian symbols and full-width punctuation.
        """
        ignore_chars = set("「」『』【】（）〈〉《》・ー〜～！？、。．，：；“”‘’・…—–‐≪≫〈〉『』【】〔〕（）［］｛｝｢｣ ㄴ ㅡ ㅋ ㅣ")

        for char in text:
            if char in ignore_chars:
                continue
            if char.isalpha():
                name = unicodedata.name(char, "")
                if "LATIN" not in name:
                    return True
        return False

    @staticmethod
    def load_context_glossary(glossary_path):
        """
        Loads the context glossary from the split subfolder.
        Returns a dictionary mapping both original and translated names to their gender pronouns.
        """
        try:
            glossary_name = os.path.splitext(os.path.basename(glossary_path))[0]
            glossary_dir = os.path.dirname(glossary_path)
            context_glossary_path = os.path.join(glossary_dir, glossary_name, "context_glossary.txt")
            
            context_dict = {}
            with open(context_glossary_path, "r", encoding="utf-8") as f:
                content = f.read()

            parts = content.split("==================================== GLOSSARY START ===============================")
            if len(parts) > 1:
                glossary_text = parts[1].split("==================================== GLOSSARY END ================================")[0].strip()
                for line in glossary_text.splitlines():
                    line = line.strip()
                    if not line or '=>' not in line:
                        continue

                    segments = [seg.strip() for seg in line.split("=>")]
                    if len(segments) == 2:
                        original, gender = segments
                        context_dict[original.lower()] = gender
                    elif len(segments) == 3:
                        original, translated, gender = segments
                        context_dict[original.lower()] = gender
                        context_dict[translated.lower()] = gender

            return context_dict

        except Exception as e:
            print(f"[ERROR] Failed to read context glossary: {e}")
            return {}
    

    def proof_gender_pronouns(self, text: str, context_dict: dict, max_retries: int = 3, retry_delay: int = 60) -> str:
        """
        Uses Vertex AI to proofread and correct gender pronouns in the text based on the context glossary.
        Includes retry logic for quota limits.
        """
        if not isinstance(context_dict, dict):
            self.log_message("[ERROR] Invalid context dictionary provided")
            return text

        if not context_dict:
            return text

        if not text or not text.strip():
            self.log_message("[ERROR] Empty text provided for gender proofing")
            return text

        # Format the context information as a string
        context_glossary = "\n".join([f"{name} => {gender}" for name, gender in context_dict.items()])
        
        PROOFING_INSTRUCTIONS = [
            "You are an English Proofreader. ",
            "Your task is to FIND and EDIT pronouns of the subjects in the input so it is correct.",
            "Allow NSFW; all characters are of age.",
            "Correct punctuation marks in the proofing should closely match the original text's format.",
            "You will receive text input that may contain HTML. The sections containing HTML MUST be returned exactly as-is, with no modifications.",
            "Here is a glossary of special terms and names. Use the attached glossary for translation accuracy:",
            context_glossary
        ]

        # Create the model with the instructions
        proof_model = GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            safety_settings=SAFETY_SETTING,
            system_instruction="\n".join(PROOFING_INSTRUCTIONS),
            generation_config=GenerationConfig(
                temperature=0.2,
                top_p=0.95,
                top_k=40,
                response_mime_type="text/plain"
            )
        )

        # Combine instructions and text
        prompt = "\n".join(PROOFING_INSTRUCTIONS) + "\n\nText to proof:\n" + text

        attempt = 0
        while attempt < max_retries:
            try:
                self.log_message(f"[PROOFING] Gender pronoun check attempt {attempt + 1}/{max_retries}")
                response = proof_model.generate_content(prompt)
                if response and response.text:
                    return response.text.strip()
                else:
                    self.log_message("[ERROR] Empty response from AI model")
                    return text
            except Exception as e:
                error_str = str(e).lower()
                attempt += 1
                
                if "429" in error_str or "quota" in error_str:
                    if attempt < max_retries:
                        self.log_message(f"[QUOTA] Hit rate limit. Attempt {attempt}/{max_retries}. "
                                       f"Waiting {retry_delay}s...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        self.log_message("[ERROR] Max retries reached for quota limit. "
                                       "Returning original text.")
                else:
                    self.log_message(f"[ERROR] Failed to proof gender pronouns: {e}")
                
                if attempt < max_retries:
                    self.log_message(f"[RETRY] Retrying gender pronoun check in {retry_delay}s... "
                                   f"(Attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                else:
                    self.log_message(f"[FAILED] All {max_retries} attempts failed for gender pronoun check. "
                                   "Returning original text.")
                    return text

        return text
    def detect_and_log_non_english_sentences(self, output_dir: str, log_file_path: str, input_dir: str,
                                            pause_event=None, cancel_flag=None):
        """
        Detects and loops retranslation until all non-English lines are removed from the translated files.
        Logs how many rounds of retranslation were performed.
        """
        self.log_message(f"[DEBUG] Checking output directory: {output_dir}")

        with open(log_file_path, "w", encoding="utf-8") as log_file:
            translated_files = [f for f in os.listdir(output_dir)
                                if f.lower().startswith('translated_')
                                and f.endswith('.txt')
                                and any(char.isdigit() for char in f)]

            if not translated_files:
                self.log_message("[WARNING] No translated files found in output directory")
                return

            def extract_last_number(filename):
                numbers = re.findall(r'\d+', filename)
                return int(numbers[-1]) if numbers else float('inf')

            translated_files.sort(key=extract_last_number)

            source_files = [f for f in os.listdir(input_dir) if f.endswith('.txt')]
            if not source_files:
                self.log_message(f"[ERROR] No source files found in input directory: {input_dir}")
                return

            source_files.sort(key=extract_last_number)
            source_file_map = {
                int(re.findall(r'\d+', f)[-1]): f for f in source_files if re.findall(r'\d+', f)
            }

            for fname in translated_files:
                if cancel_flag and cancel_flag():
                    self.log_message("[CONTROL] Proofing canceled before file: " + fname)
                    return

                numbers = re.findall(r'\d+', fname)
                if not numbers:
                    self.log_message(f"[WARNING] Could not extract number from translated file: {fname}")
                    continue

                file_number = int(numbers[-1])
                original_fname = source_file_map.get(file_number)
                if not original_fname:
                    self.log_message(f"[WARNING] No matching source file for {fname}")
                    continue

                translated_path = os.path.join(output_dir, fname)
                source_path = os.path.join(input_dir, original_fname)

                if not os.path.exists(source_path):
                    self.log_message(f"[WARNING] Source file not found: {source_path}")
                    continue

                try:
                    with open(source_path, "r", encoding="utf-8") as f_in:
                        input_lines = f_in.read().strip().splitlines()
                    with open(translated_path, "r", encoding="utf-8") as f_out:
                        translated_lines = f_out.read().strip().splitlines()

                    num_lines = min(len(input_lines), len(translated_lines))
                    new_translated = translated_lines.copy()
                    changed = False

                    for i in range(num_lines):
                        # Pause/Cancel check
                        if cancel_flag and cancel_flag():
                            self.log_message("[CONTROL] Proofing canceled mid-file.")
                            return
                        if pause_event:
                            self.log_message(f"[CONTROL] Paused before line {i+1} of {fname}...")
                            pause_event.wait()

                        if self.contains_non_english_letters(translated_lines[i]):
                            self.log_message(f"[NON-ENGLISH] Line {i+1} in {fname}: {translated_lines[i].strip()}")
                            log_file.write(f"File: {fname}, Line {i+1}:\n{translated_lines[i]}\n\n")

                            context_text = translated_lines[i]

                            system_instruction = "\n".join([
                                "You are a translation fixer.",
                                "Your job is to retranslate any sentence that contains non-English characters (e.g. Japanese, Korean, ㅇㅇ, な, etc.) into fluent English.",
                                "Preserve the original meaning and non-english formatting if it doesn't contribute to the meaning of the sentence.",
                                "Leave HTML tags untouched.",
                                "Only return the revised sentence.",
                                "Allow NSFW; all characters are of age.",
                            ])

                            proof_model = GenerativeModel(
                                model_name="gemini-2.0-flash-exp",
                                safety_settings=SAFETY_SETTING,
                                system_instruction=system_instruction,
                                generation_config=GenerationConfig(
                                    temperature=0.2,
                                    top_p=0.9,
                                    top_k=40,
                                    response_mime_type="text/plain"
                                )
                            )

                            max_retries = 3
                            retry_delay = 30
                            retranslated = None

                            for attempt in range(1, max_retries + 1):
                                try:
                                    response = proof_model.generate_content(context_text)
                                    if response and response.text:
                                        retranslated = response.text.strip()
                                        if retranslated:
                                            self.log_message(f"[GEMINI] Success on attempt {attempt} for line {i+1} in {fname}")
                                            break
                                        else:
                                            self.log_message(f"[WARNING] Empty response on attempt {attempt} for line {i+1}")
                                    else:
                                        self.log_message(f"[WARNING] No usable response on attempt {attempt} for line {i+1}")
                                except Exception as e:
                                    self.log_message(f"[ERROR] Gemini error on attempt {attempt} for line {i+1} in {fname}: {e}")

                                if attempt < max_retries:
                                    self.log_message(f"[RETRY] Retrying line {i+1} in {retry_delay} seconds...")
                                    time.sleep(retry_delay)

                            if retranslated:
                                re_lines = [line.strip() for line in retranslated.splitlines() if line.strip()]
                                replacement = None
                                for candidate in re_lines:
                                    if not self.contains_non_english_letters(candidate):
                                        replacement = candidate
                                        break

                                if replacement is None and re_lines:
                                    replacement = re_lines[len(re_lines) // 2]

                                if replacement:
                                    new_translated[i] = replacement
                                    changed = True
                                    self.log_message(f"[FIXED] Line {i+1} updated in {fname}: {replacement}")
                                else:
                                    self.log_message(f"[WARNING] No valid replacement for line {i+1}")
                            else:
                                self.log_message(f"[WARNING] No Gemini response for line {i+1}")

                    if changed:
                        with open(translated_path, "w", encoding="utf-8") as f_out:
                            f_out.write("\n".join(new_translated))
                        self.log_message(f"[UPDATED] File rewritten: {fname}")
                    else:
                        self.log_message(f"[OK] {fname} had no non-English issues.")
                except Exception as e:
                    self.log_message(f"[ERROR processing {fname}]: {e}")

    def proof_gender_pronouns_for_all_files(self, output_dir: str, context_dict: dict, max_retries: int = 3, retry_delay: int = 60):
        """
        Process all files with retry logic for quota limits and safeguard against excessive line count changes.
        """
        if not isinstance(context_dict, dict):
            self.log_message("[ERROR] Invalid context dictionary provided to proofing function")
            return

        if not context_dict:
            self.log_message("[PROOFING] No context glossary provided. Skipping gender pronoun proofing.")
            return

        self.log_message("[PROOFING] Loaded context glossary for gender pronoun proofing.")
        self.log_message(f"[DEBUG] Context dictionary contains {len(context_dict)} entries")

        text_files = [f for f in os.listdir(output_dir) 
                    if f.lower().startswith('translated') 
                    and f.endswith('.txt')
                    and any(char.isdigit() for char in f)]

        def extract_last_number(filename):
            numbers = re.findall(r'\d+', filename)
            return int(numbers[-1]) if numbers else float('inf')

        text_files.sort(key=extract_last_number)

        for fname in text_files:
            self.log_message(f"[PROOFING] Starting gender pronoun proofing pass for: {fname}")
            attempt = 0
            while attempt < max_retries:
                try:
                    out_file_path = os.path.join(output_dir, fname)

                    with open(out_file_path, "r", encoding="utf-8") as f_out:
                        content = f_out.read()

                    proofed_content = self.proof_gender_pronouns(content, context_dict)

                    # Check line count difference
                    original_line_count = len(content.splitlines())
                    proofed_line_count = len(proofed_content.splitlines())
                    line_difference = abs(proofed_line_count - original_line_count)

                    if line_difference > 10:
                        self.log_message(f"[WARNING] Line count difference too large in {fname}. "
                                        f"Original: {original_line_count}, New: {proofed_line_count}. "
                                        "Keeping original text.")
                        break  # Skip overwriting file

                    if proofed_content != content:
                        with open(out_file_path, "w", encoding="utf-8") as f_out:
                            f_out.write(proofed_content)
                        self.log_message(f"[OK] Updated gender pronouns in {fname}.")
                    else:
                        self.log_message(f"[OK] No changes needed for {fname}.")
                    break  # Success, move to next file

                except Exception as e:
                    error_str = str(e).lower()
                    attempt += 1

                    if "429" in error_str or "quota" in error_str:
                        if attempt < max_retries:
                            self.log_message(f"[QUOTA] Hit rate limit for {fname}. Attempt {attempt}/{max_retries}. Waiting {retry_delay}s...")
                            time.sleep(retry_delay)
                            continue
                        else:
                            self.log_message(f"[ERROR] Max retries reached for {fname}. Skipping file.")
                    else:
                        self.log_message(f"[ERROR processing {fname}]: {str(e)}")
                        break  # Non-quota error, skip this file
        
        def extract_last_number(filename):
            numbers = re.findall(r'\d+', filename)
            return int(numbers[-1]) if numbers else float('inf')
        
        text_files.sort(key=extract_last_number)
        
        for fname in text_files:
            self.log_message(f"[PROOFING] Starting gender pronoun proofing pass for: {fname}")
            attempt = 0
            while attempt < max_retries:
                try:
                    out_file_path = os.path.join(output_dir, fname)
                    
                    with open(out_file_path, "r", encoding="utf-8") as f_out:
                        content = f_out.read()

                    proofed_content = self.proof_gender_pronouns(content, context_dict)

                    if proofed_content != content:
                        with open(out_file_path, "w", encoding="utf-8") as f_out:
                            f_out.write(proofed_content)
                        self.log_message(f"[OK] Updated gender pronouns in {fname}.")
                    else:
                        self.log_message(f"[OK] No changes needed for {fname}.")
                    break  # Success, move to next file
                    
                except Exception as e:
                    error_str = str(e).lower()
                    attempt += 1
                    
                    if "429" in error_str or "quota" in error_str:
                        if attempt < max_retries:
                            self.log_message(f"[QUOTA] Hit rate limit for {fname}. Attempt {attempt}/{max_retries}. Waiting {retry_delay}s...")
                            time.sleep(retry_delay)
                            continue
                        else:
                            self.log_message(f"[ERROR] Max retries reached for {fname}. Skipping file.")
                    else:
                        self.log_message(f"[ERROR processing {fname}]: {str(e)}")
                        break  # Non-quota error, skip this file
    
    @staticmethod
    def load_proofing_glossaries(glossary_path, log_message=print):
        """
        Loads both the name and context glossaries from the glossary subfolder.
        Returns two strings: name_glossary_text and context_glossary_text.
        """
        glossary_name = os.path.splitext(os.path.basename(glossary_path))[0]
        glossary_dir = os.path.dirname(glossary_path)
        subfolder = os.path.join(glossary_dir, glossary_name)
        
        name_glossary_path = os.path.join(subfolder, "name_glossary.txt")
        context_glossary_path = os.path.join(subfolder, "context_glossary.txt")
        
        name_text, context_text = "", ""
        try:
            with open(name_glossary_path, "r", encoding="utf-8") as f:
                name_text = f.read().strip()
        except Exception as e:
            log_message(f"[ERROR] Unable to load name glossary from {name_glossary_path}: {e}")

        try:
            with open(context_glossary_path, "r", encoding="utf-8") as f:
                context_text = f.read().strip()
        except Exception as e:
            log_message(f"[ERROR] Unable to load context glossary from {context_glossary_path}: {e}")
        
        return name_text, context_text

    def proofread_with_ai(self, file_path: str, max_retries=3, retry_delay=60) -> str:
        """
        Proofreads the file's content using AI, injecting glossary and chapter context, with retry logic.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_content = f.read()
        except Exception as e:
            self.log_message(f"[ERROR] Cannot read file {file_path}: {e}")
            return ""

        original_line_count = len(file_content.splitlines())
        self.log_message(f"[DEBUG] Original line count for {os.path.basename(file_path)}: {original_line_count}")

        # Load glossary content
        # prefer the injected path, else fall back to default
        glossary_path = self.glossary_path or get_current_glossary_file()

        name_glossary, context_glossary = self.load_proofing_glossaries(glossary_path, self.log_message)

        # Format the glossary into a usable AI context
        glossary_context = []
        if name_glossary:
            glossary_context.append("Glossary of Proper Names:\n" + name_glossary)
        if context_glossary:
            glossary_context.append("Glossary of Gender Pronouns:\n" + context_glossary)

        # Load previous/next chapter context
        base_dir = os.path.dirname(file_path)
        current_fname = os.path.basename(file_path)
        match = re.search(r'(\d+)', current_fname)
        prev_text = next_text = ""

        if match:
            num = int(match.group(1))
            prev_file = os.path.join(base_dir, re.sub(r'\d+', str(num - 1).zfill(len(match.group(1))), current_fname, 1))
            next_file = os.path.join(base_dir, re.sub(r'\d+', str(num + 1).zfill(len(match.group(1))), current_fname, 1))

            if os.path.exists(prev_file):
                with open(prev_file, "r", encoding="utf-8") as pf:
                    prev_text = pf.read().strip()
                    glossary_context.append("Previous Chapter Context:\n" + prev_text)

            if os.path.exists(next_file):
                with open(next_file, "r", encoding="utf-8") as nf:
                    next_text = nf.read().strip()
                    glossary_context.append("Next Chapter Context:\n" + next_text)

        # Combine all context and current file text
        full_prompt = "\n\n".join(glossary_context) + "\n\nCurrent Chapter:\n" + file_content

        proofread_model = GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            safety_settings=SAFETY_SETTING,
            system_instruction=self.PROOFREADING_INSTRUCTIONS,
            generation_config=GenerationConfig(
                temperature=0.2,
                top_p=0.95,
                top_k=40,
                response_mime_type="text/plain"
            )
        )

        attempt = 0
        while attempt < max_retries:
            try:
                self.log_message(f"[PROOFING] Attempt {attempt + 1}/{max_retries} for {os.path.basename(file_path)}")
                response = proofread_model.generate_content(full_prompt)

                if "Explanation:" in response.text:
                    proofed_text, explanation = response.text.split("Explanation:", 1)
                    proofed_text = proofed_text.strip()
                    self.log_message(f"[PROOFING] Changes in {os.path.basename(file_path)}: {explanation.strip()}")
                else:
                    proofed_text = response.text.strip()

                proofed_line_count = len(proofed_text.splitlines())
                line_difference = abs(proofed_line_count - original_line_count)

                if line_difference > 10:
                    self.log_message(f"[WARNING] Line count difference too large in {os.path.basename(file_path)}. "
                                    f"Original: {original_line_count}, New: {proofed_line_count}. Keeping original.")
                    return file_content

                return proofed_text

            except Exception as e:
                error_str = str(e).lower()
                attempt += 1

                if "429" in error_str or "quota" in error_str:
                    if attempt < max_retries:
                        self.log_message(f"[QUOTA] Rate limit hit for {os.path.basename(file_path)}. "
                                        f"Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        self.log_message(f"[ERROR] Max retries reached for {os.path.basename(file_path)}. Returning original.")
                else:
                    self.log_message(f"[ERROR] Proofing failed for {os.path.basename(file_path)}: {e}")
                    break

        return file_content
    
    def proof_glossary_file(self, glossary_path: str, max_retries=3, retry_delay=60) -> None:
        """
        Uses AI to proofread and clean up the glossary for consistency.
        Detects duplicates, spelling variants, formatting inconsistencies.

        Args:
            glossary_path: Path to the glossary file
        """
        if not os.path.exists(glossary_path):
            self.log_message(f"[ERROR] Glossary file not found: {glossary_path}")
            return

        with open(glossary_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract glossary section only
        parts = content.split("==================================== GLOSSARY START ===============================")
        if len(parts) < 2:
            self.log_message("[ERROR] Glossary markers not found in glossary file.")
            return

        glossary_text = parts[1].split("==================================== GLOSSARY END ================================")[0].strip()

        if not glossary_text:
            self.log_message("[INFO] Glossary is empty, skipping proofreading.")
            return

        # Prepare prompt
        instructions = [
            "Your task is to proofread a glossary for a Non-English-to-English translation project.",
            "Fix any formatting inconsistencies, merge similar entries, and remove exact duplicates.",
            "Each glossary line is in this format: Original => English => Gender",
            "Ensure consistent formatting and spacing.",
            "If two ORIGINAL terms are CLEARLY spelling variants of the SAME name, merge them and choose the most appropriate English term and gender.",
            "Return ONLY the cleaned glossary lines, no explanation or comments.",
        ]

        model = GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            system_instruction="\n".join(instructions),
            safety_settings=SAFETY_SETTING,
            generation_config=GenerationConfig(
                temperature=0.4,
                top_p=0.9,
                top_k=40,
                response_mime_type="text/plain"
            )
        )

        prompt = "\n".join(instructions) + "\n\nGlossary:\n" + glossary_text

        attempt = 0
        while attempt < max_retries:
            try:
                self.log_message(f"[GLOSSARY PROOFING] Attempt {attempt + 1}/{max_retries}")
                response = model.generate_content(prompt)
                if response and response.text:
                    cleaned_text = response.text.strip()

                    # Reinsert glossary markers
                    new_content = (
                        "==================================== GLOSSARY START ===============================\n"
                        + cleaned_text + "\n"
                        + "==================================== GLOSSARY END ================================\n"
                    )

                    # Write back to glossary
                    with open(glossary_path, "w", encoding="utf-8") as f:
                        f.write(new_content)

                    self.log_message(f"[OK] Glossary proofreading complete. Updated: {glossary_path}")
                    return
                else:
                    self.log_message("[ERROR] Empty response from glossary proofing model.")
                    return
            except Exception as e:
                attempt += 1
                self.log_message(f"[ERROR] Attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    self.log_message(f"[RETRY] Waiting {retry_delay}s...")
                    time.sleep(retry_delay)

        self.log_message("[FAILED] All attempts to proof glossary failed.")

    @staticmethod
    def inject_context(input_text, context_dict):
        injected_lines = [f"{name} is {desc}." for name, desc in context_dict.items()]
        context_header = "Context: " + " ".join(injected_lines)
        return f"{context_header}\n\n{input_text}"