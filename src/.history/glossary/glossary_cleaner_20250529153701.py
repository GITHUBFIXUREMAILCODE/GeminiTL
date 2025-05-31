import os
import re
import argparse
from pathlib import Path
import unicodedata
from .glossary import Glossary, normalize_term

def is_english(text):
    """Check if a string is primarily English."""
    # Remove numbers and punctuation
    text = re.sub(r'[0-9\s\W]', '', text)
    if not text:
        return False
    
    # Count English characters
    english_chars = sum(1 for c in text if ord('a') <= ord(c.lower()) <= ord('z'))
    return english_chars / len(text) > 0.7  # If more than 70% are English chars

def clean_glossary(glossary_path, log_message=print):
    """
    Clean the glossary by:
    1. Removing entries where the term (left side) is primarily English
    2. Removing entries with symbols from a predetermined list
    """
    if not os.path.exists(glossary_path):
        log_message(f"[ERROR] Glossary file not found: {glossary_path}")
        return False
    
    # Symbols to remove (entries containing these will be removed)
    symbols_to_remove = [
        "…", "「", "」", "『", "』", "、", "。", "！", "？", "～", "・",
        "（", "）", "【", "】", "《", "》", "〈", "〉", "〔", "〕", "［", "］",
        "｛", "｝", "〝", "〟", "〃", "：", "；", "，", "．", "＿", "／", "＼"
    ]
    
    try:
        with open(glossary_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Split content by markers
        parts = content.split("==================================== GLOSSARY START ===============================")
        if len(parts) < 2:
            log_message(f"[ERROR] Invalid glossary format in {glossary_path}")
            return False
        
        header = parts[0]
        glossary_section = parts[1].split("==================================== GLOSSARY END ================================")[0]
        footer = "==================================== GLOSSARY END ================================" + \
                 parts[1].split("==================================== GLOSSARY END ================================")[1]
        
        # Process each line
        cleaned_entries = []
        removed_count = 0
        
        for line in glossary_section.splitlines():
            if "=>" not in line:
                continue
            
            parts = line.split("=>")
            if len(parts) < 2:
                continue
            
            term = parts[0].strip()
            
            # Skip if term is primarily English
            if is_english(term):
                removed_count += 1
                log_message(f"[CLEAN] Removed English term: {term}")
                continue
            
            # Skip if term contains any of the symbols to remove
            if any(symbol in term for symbol in symbols_to_remove):
                removed_count += 1
                log_message(f"[CLEAN] Removed term with symbols: {term}")
                continue
            
            # Keep this entry
            cleaned_entries.append(line.strip())
        
        # Rebuild the glossary
        new_content = header + \
                     "==================================== GLOSSARY START ===============================\n" + \
                     "\n".join(cleaned_entries) + "\n" + \
                     footer
        
        # Write back to file
        with open(glossary_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        log_message(f"[CLEAN] Glossary cleaned: {glossary_path}")
        log_message(f"[CLEAN] Removed {removed_count} entries, kept {len(cleaned_entries)} entries")
        
        # Split the glossary after cleaning
        try:
            from glossary.glossary_splitter import split_glossary
            split_glossary(glossary_path)
            log_message("[CLEAN] Successfully split cleaned glossary into name/context files.")
        except Exception as e:
            log_message(f"[CLEAN] Failed to split glossary after cleaning: {e}")
        
        return True
    
    except Exception as e:
        log_message(f"[ERROR] Failed to clean glossary: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Clean a glossary file by removing English terms and symbols")
    parser.add_argument("glossary_path", help="Path to the glossary file to clean")
    args = parser.parse_args()
    
    clean_glossary(args.glossary_path)

if __name__ == "__main__":
    main()