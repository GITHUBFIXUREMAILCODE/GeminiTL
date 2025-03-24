import os
import re
import importlib.metadata

def get_imports_from_file(file_path):
    """Extracts imported modules from a given Python file, skipping files with syntax errors."""
    imports = set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                match = re.match(r"^\s*(?:import|from)\s+([\w\d_.]+)", line)
                if match:
                    imports.add(match.group(1).split(".")[0])  # Extract base module name
    except Exception as e:
        print(f"Skipping {file_path} due to error: {e}")
    return imports

def get_installed_packages():
    """Returns a set of all installed package names using importlib.metadata."""
    return {dist.metadata["Name"].lower() for dist in importlib.metadata.distributions()}

def generate_requirements(folder_path, output_file="requirements.txt"):
    """Scans Python files in a folder and generates a requirements.txt, skipping broken files."""
    all_imports = set()
    
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                all_imports.update(get_imports_from_file(file_path))

    installed_packages = get_installed_packages()
    required_packages = sorted(all_imports & installed_packages)

    with open(output_file, "w") as f:
        f.write("\n".join(required_packages) + "\n")

    print(f"Requirements saved to {output_file}")

# Run for a specific folder
folder_path = r"C:\Users\anhth\Downloads\GemeniAPIScript"
generate_requirements(folder_path)
