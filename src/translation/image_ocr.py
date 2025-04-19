"""
Image OCR module for the novel translation tool.

This module provides functionality for:
- Preprocessing images for OCR
- Running OCR on images
- Replacing image tags with OCR text
"""

import os
import re
import cv2
import pytesseract
from PIL import Image

class ImageOCR:
    """
    Handles OCR (Optical Character Recognition) for images in the translation process.
    
    This class provides functionality for:
    - Preprocessing images for better OCR accuracy
    - Running OCR on images
    - Replacing image tags with OCR text or embedded images
    """
    
    def __init__(self, log_function=None):
        self.log_function = log_function or print

    @staticmethod
    def preprocess_for_ocr(image_path):
        """
        Preprocess the image for OCR:
          1. Convert to grayscale.
          2. Scale up 2x for better accuracy.
          3. Apply adaptive thresholding for a high-contrast binary image.

        Returns: Path to a temporary preprocessed image, or None if reading fails.
        """
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            return None

        # Scale up the image 2x
        image = cv2.resize(image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # Adaptive threshold => high-contrast binary
        image = cv2.adaptiveThreshold(
            image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )

        temp_preprocessed = "temp_preprocessed.png"
        cv2.imwrite(temp_preprocessed, image)
        return temp_preprocessed

    @staticmethod
    def run_ocr_on_image(image_path):
        """
        Runs OCR on the given image and returns recognized text.
        If OCR fails, returns None instead of an error message.
        """
        try:
            preprocessed = ImageOCR.preprocess_for_ocr(image_path)
            if not preprocessed:
                return None

            # Whitelist only digits 0-9; if you expect letters, remove or adjust this
            custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
            text = pytesseract.image_to_string(Image.open(preprocessed), config=custom_config)

            os.remove(preprocessed)
            return text.strip() if text.strip() else None
        except Exception:
            return None  # Return None if OCR fails instead of an error string

    def replace_image_tags_with_ocr(self, text, image_dir):
        """
        Scans the input `text` for <image src="embedXXXX.jpg" ...> tags.
          - If the image name includes "_HD", leave the tag as-is (skip OCR).
          - Otherwise, run OCR on the image.
          - If OCR succeeds, replace the <image> tag with recognized text.
          - If OCR fails or image is missing, insert an XHTML <img> tag.

        Example match: <image src="embed0007.jpg" alt="some alt text"/>
        """

        # If there's no images/ folder, do nothing
        if not os.path.isdir(image_dir):
            return text

        # Regex: capture the entire <image> tag and the .jpg filename
        pattern = re.compile(r'(<image\s+[^>]*src\s*=\s*"([^"]+\.jpg)"[^>]*>)', re.IGNORECASE)

        def replacer(match):
            full_tag = match.group(1)
            image_name = match.group(2)

            # Skip HD images
            if "_HD" in image_name.upper():
                return full_tag

            # Build the actual path to the image
            image_path = os.path.join(image_dir, image_name)
            if not os.path.exists(image_path):
                replacement = f'<img src="{image_name}" alt="Image not found"/>'
                self.log_function(f"[REPLACED] Missing Image: {image_name} -> Embedded Image")
                return replacement

            # OCR the image
            ocr_text = self.run_ocr_on_image(image_path)
            if ocr_text:
                return ocr_text  # Replace the entire <image> tag with recognized text

            # If OCR failed, replace with an XHTML embed
            replacement = f'<img src="{image_name}" alt="OCR Failed"/>'
            self.log_function(f"[REPLACED] OCR Failed: {image_name} -> Embedded Image")
            return replacement  

        return pattern.sub(replacer, text)
