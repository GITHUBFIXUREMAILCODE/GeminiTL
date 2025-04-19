"""
OCR Fail Detection module for the novel translation tool.

This module provides functionality for:
- Detecting OCR failures in translated text files
- Reporting failed OCR attempts
"""

import os

class OCRFailDetector:
    """
    Handles detection of OCR failures in translated text files.
    
    This class provides functionality for:
    - Scanning output files for OCR failures
    - Reporting failed OCR attempts with file and line numbers
    """
    
    def __init__(self, log_function=None):
        self.log_function = log_function or print

    def detect_failures(self, output_dir=None):
        """
        Scans all .txt files in the output directory for 'OCR Failed' messages.
        If output_dir is not provided, looks two folders up from the script for an 'output' folder.
        
        Args:
            output_dir (str, optional): Path to the output directory. Defaults to None.
        """
        if output_dir is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_dir = os.path.join(script_dir, "..", "..", "output")

        if not os.path.isdir(output_dir):
            self.log_function(f"[ERROR] 'output' folder not found at: {output_dir}")
            return

        # List items in 'output' folder (non-recursive)
        for item in os.listdir(output_dir):
            # Only process .txt files
            if item.lower().endswith(".txt"):
                file_path = os.path.join(output_dir, item)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        for line_num, line in enumerate(f, start=1):
                            if "OCR Failed" in line:
                                self.log_function(f"[OCR FAIL DETECTED] -> {file_path} (line {line_num}): {line.strip()}")
                except Exception as e:
                    self.log_function(f"[ERROR] Could not read {file_path}: {e}")

def main():
    """
    Command-line entry point for OCR failure detection.
    """
    detector = OCRFailDetector()
    detector.detect_failures()

if __name__ == "__main__":
    main()
