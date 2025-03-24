import os

def main():
    """
    Looks two folders up for a folder named 'output',
    scans all .txt files (non-recursive),
    and searches for 'OCR Failed'.
    """

    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Two folders up + "output" folder
    output_path = os.path.join(script_dir, "..", "..", "output")

    if not os.path.isdir(output_path):
        print(f"[ERROR] 'output' folder not found at: {output_path}")
        return

    # List items in 'output' folder (non-recursive)
    for item in os.listdir(output_path):
        # Only process .txt files
        if item.lower().endswith(".txt"):
            file_path = os.path.join(output_path, item)
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    for line_num, line in enumerate(f, start=1):
                        if "OCR Failed" in line:
                            print(f"[OCR FAIL DETECTED] -> {file_path} (line {line_num}): {line.strip()}")
            except Exception as e:
                print(f"[ERROR] Could not read {file_path}: {e}")


if __name__ == "__main__":
    main()
