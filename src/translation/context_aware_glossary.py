import os

def split_glossary(glossary_path):
    # Get the base directory and filename without extension
    base_dir = os.path.dirname(glossary_path)
    glossary_name = os.path.splitext(os.path.basename(glossary_path))[0]
    
    # Create subfolder for the subglossaries
    subfolder = os.path.join(base_dir, glossary_name)
    os.makedirs(subfolder, exist_ok=True)
    
    # Define paths for the subglossaries in the subfolder
    name_glossary_path = os.path.join(subfolder, "name_glossary.txt")
    context_glossary_path = os.path.join(subfolder, "context_glossary.txt")

    name_entries = []
    context_entries = []

    with open(glossary_path, "r", encoding="utf-8") as f:
        for line in f:
            if '=>' not in line:
                continue
            # Split into three parts: Non-English => English => Gender Pronoun
            parts = line.strip().split('=>')
            if len(parts) >= 3:
                non_english = parts[0].strip()
                english = parts[1].strip()
                gender = parts[2].strip()
                
                # Add to name glossary (Non-English => English)
                name_entries.append((non_english, english))
                
                # Add to context glossary (English => Gender Pronoun)
                context_entries.append((english, gender))
            elif len(parts) == 2:
                # Handle entries without gender pronoun
                non_english = parts[0].strip()
                english = parts[1].strip()
                name_entries.append((non_english, english))

    # Write name glossary with markers
    with open(name_glossary_path, "w", encoding="utf-8") as f:
        f.write("==================================== GLOSSARY START ===============================\n")
        for non_english, english in name_entries:
            f.write(f"{non_english} => {english}\n")
        f.write("==================================== GLOSSARY END ================================\n")

    # Write context glossary with markers
    with open(context_glossary_path, "w", encoding="utf-8") as f:
        f.write("==================================== GLOSSARY START ===============================\n")
        for english, gender in context_entries:
            f.write(f"{english} => {gender}\n")
        f.write("==================================== GLOSSARY END ================================\n")

    return {eng: gender for eng, gender in context_entries}

def inject_context(input_text, context_dict):
    injected_lines = [f"{name} is {desc}." for name, desc in context_dict.items()]
    context_header = "Context: " + " ".join(injected_lines)
    return f"{context_header}\n\n{input_text}"
