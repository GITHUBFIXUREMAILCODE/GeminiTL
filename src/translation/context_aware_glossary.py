import os

def split_glossary(glossary_path):
    """Split the main glossary into name and context glossaries."""
    if not glossary_path:
        raise ValueError("Glossary path cannot be None or empty")

    # Get the base directory and filename without extension
    base_dir = os.path.dirname(glossary_path)
    glossary_name = os.path.splitext(os.path.basename(glossary_path))[0]
    
    # Create subfolder with the same name as the glossary file
    subfolder = os.path.join(base_dir, glossary_name)
    print(f"[DEBUG] Creating subfolder at: {subfolder}")
    os.makedirs(subfolder, exist_ok=True)
    
    # Define paths for the subglossaries
    name_glossary_path = os.path.join(subfolder, "name_glossary.txt")
    context_glossary_path = os.path.join(subfolder, "context_glossary.txt")

    name_entries = []
    context_entries = []

    # Read and parse the main glossary
    with open(glossary_path, "r", encoding="utf-8") as f:
        content = f.read()
        if "==================================== GLOSSARY START ===============================" not in content:
            raise ValueError("Invalid glossary format: missing START marker")
            
        parts = content.split("==================================== GLOSSARY START ===============================")
        if len(parts) > 1:
            glossary_text = parts[1].split("==================================== GLOSSARY END ================================")[0].strip()
            
            for line in glossary_text.splitlines():
                if '=>' not in line:
                    continue
                # Split into parts: Non-English => English => Gender Pronoun
                parts = line.strip().split('=>')
                if len(parts) >= 3:
                    non_english = parts[0].strip()
                    english = parts[1].strip()
                    gender = parts[2].strip()
                    
                    name_entries.append((non_english, english))
                    context_entries.append((english, gender))
                elif len(parts) == 2:
                    non_english = parts[0].strip()
                    english = parts[1].strip()
                    name_entries.append((non_english, english))

    # Write name glossary
    with open(name_glossary_path, "w", encoding="utf-8") as f:
        f.write("==================================== GLOSSARY START ===============================\n")
        for non_english, english in name_entries:
            f.write(f"{non_english} => {english}\n")
        f.write("==================================== GLOSSARY END ================================\n")

    # Write context glossary
    with open(context_glossary_path, "w", encoding="utf-8") as f:
        f.write("==================================== GLOSSARY START ===============================\n")
        for english, gender in context_entries:
            f.write(f"{english} => {gender}\n")
        f.write("==================================== GLOSSARY END ================================\n")

    return name_glossary_path, context_glossary_path

def inject_context(input_text, context_dict):
    injected_lines = [f"{name} is {desc}." for name, desc in context_dict.items()]
    context_header = "Context: " + " ".join(injected_lines)
    return f"{context_header}\n\n{input_text}"


