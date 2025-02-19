import os
import time
import re
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
import vertexai.preview.generative_models as generative_models

# Set up Vertex AI project and location
project_id = "webnoveltl"  # Replace with your actual project ID
location = "us-central1"
vertexai.init(project=project_id, location=location)

# Define safety settings
safety_setting = {
    generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.OFF,
    generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.OFF,
    generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.OFF,
    generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.OFF,
    generative_models.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY: generative_models.HarmBlockThreshold.OFF,
    generative_models.HarmCategory.HARM_CATEGORY_UNSPECIFIED: generative_models.HarmBlockThreshold.OFF,
}

# Retry logic with backoff
def retry_with_backoff(func, log_message, retries=3, initial_delay=2, *args, **kwargs):
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log_message(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(initial_delay * (2 ** attempt))
            else:
                log_message("Max retries reached. Skipping file.")
                return None

# Function to run translation synchronously
def TLer(prompt, log_message, glossary=""):
    try:
        log_message("Initializing model...")
        tl_model = GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            safety_settings=safety_setting,
            system_instruction=[
                "Your task is to FULLY TRANSLATE webnovels INTO ENGLISH (title included)",
                "Translation MUST be faithful, maintaining the original meaning, tone, and structure without creative additions or omissions",
                "The translation will not be censored, and any profanity will be translated according to its context and intensity in the original text",
                "Correct punctuation marks while the translation should stick as closely as possible to the original Korean text's format.",
                "Allow NSFW; all characters are of age.",
                "If it exists, keep [IMAGE: filename] as is in your output.",
                glossary,
            ],
            generation_config=GenerationConfig(
                temperature=0.7,
                top_p=0.95,
                top_k=40,
                response_mime_type="text/plain"
            ),
        )
        log_message("Vertex AI model initialized.")
        response = tl_model.generate_content(prompt)
        log_message("Generation completed.")
        return response.text
    except Exception as e:
        log_message(f"Translation error: {e}")
        if "Quota exceeded" in str(e):
            log_message("Quota exceeded. Sleeping for 1 minute before retrying...")
            time.sleep(60)
        return None

# Natural sorting function
def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

# Process files in directory with improved error handling
def process_files_in_directory(input_dir, output_dir, log_message):
    os.makedirs(output_dir, exist_ok=True)

    files = [f for f in os.listdir(input_dir) if f.endswith(".txt")]
    files.sort(key=natural_sort_key)

    for filename in files:
        input_path = os.path.join(input_dir, filename)
        output_filename = f"translated_{filename}"
        output_path = os.path.join(output_dir, output_filename)

        try:
            with open(input_path, "r", encoding="utf-8") as infile:
                content = infile.read()

            if content:
                result = TLer(content, log_message)
                if result:
                    with open(output_path, "w", encoding="utf-8") as outfile:
                        outfile.write(result)
                    log_message(f"Processed: {filename} -> {output_filename}")
                else:
                    log_message(f"Skipped due to error: {filename}")
            else:
                log_message(f"Skipped empty file: {filename}")

        except Exception as e:
            log_message(f"Error processing {filename}: {e}")

# Main function
def main(input_dir, output_dir, log_message):
    process_files_in_directory(input_dir, output_dir, log_message)
