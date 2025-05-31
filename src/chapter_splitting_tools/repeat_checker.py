import os
from datetime import datetime

# Constants
OUTPUT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../output"))
PROOFED_FOLDER = os.path.join(OUTPUT_FOLDER, "proofed_files")
LOG_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../logs"))
SUMMARY_LOG_FILE = os.path.join(LOG_FOLDER, "repeat_check_summary.log")

def detect_phase(file_path):
    filename = os.path.basename(file_path)
    if "proofed_files" in file_path.replace("\\", "/"):
        return "proofreading"
    elif filename.startswith("translated_"):
        return "translation"
    else:
        return "unknown"

def check_repeats(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.rstrip("\n") for line in f]
    except Exception as e:
        print(f"[ERROR] Cannot open file {file_path}: {e}")
        return []

    seen = {}
    duplicates = []

    for idx, line in enumerate(lines):
        stripped_line = line.strip()  # <--- trim spaces
        
        if not stripped_line:
            continue  # <--- Ignore blank/whitespace-only lines

        if stripped_line in seen:
            duplicates.append((seen[stripped_line], idx, stripped_line))
        else:
            seen[stripped_line] = idx

    return duplicates


def ensure_log_folder():
    os.makedirs(LOG_FOLDER, exist_ok=True)

def scan_and_check_folder(folder_path, results):
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".txt"):
                full_path = os.path.join(root, file)
                phase = detect_phase(full_path)
                duplicates = check_repeats(full_path)

                if duplicates:
                    results.append({
                        "file": os.path.relpath(full_path, start=OUTPUT_FOLDER),
                        "phase": phase,
                        "duplicates": len(duplicates),
                        "duplicate_lines": duplicates
                    })

def write_summary_log(results):
    ensure_log_folder()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(SUMMARY_LOG_FILE, "w", encoding="utf-8") as log_file:
        log_file.write(f"Repeat Check Summary Log - {timestamp}\n")
        log_file.write(f"Checked folders: {OUTPUT_FOLDER} and {PROOFED_FOLDER}\n\n")
        log_file.write(f"{'File':<50} | {'Phase':<12} | {'# Duplicates':<12}\n")
        log_file.write(f"{'-'*80}\n")
        
        for result in results:
            log_file.write(f"{result['file']:<50} | {result['phase']:<12} | {result['duplicates']:<12}\n")

        log_file.write(f"\nDetailed duplicate lines per file:\n")
        log_file.write(f"{'-'*80}\n\n")

        for result in results:
            log_file.write(f"File: {result['file']}\n")
            for first_idx, second_idx, line in result['duplicate_lines']:
                log_file.write(f"Line {first_idx+1} and Line {second_idx+1}: {line}\n")
            log_file.write("\n")

    print(f"[SUMMARY LOG] Written to {SUMMARY_LOG_FILE}")

def main():
    print(f"[INFO] Starting repeat check...")
    results = []
    
    # Scan both output and proofed folders
    scan_and_check_folder(OUTPUT_FOLDER, results)
    scan_and_check_folder(PROOFED_FOLDER, results)

    if results:
        write_summary_log(results)
        print(f"[WARNING] Duplicates found in {len(results)} files. See summary log.")
    else:
        print(f"[OK] No duplicates detected.")

if __name__ == "__main__":
    main()
