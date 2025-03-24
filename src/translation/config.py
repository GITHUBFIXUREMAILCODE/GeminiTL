# src/config.py
import os
import vertexai
import vertexai.preview.generative_models as generative_models

# Move up two levels to the main directory where `ControlScript.py` is located
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  
config_file = os.path.join(script_dir, "config.txt")

def read_config():
    """Reads configuration values from config.txt."""
    config = {}
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    config[key.strip()] = value.strip()
    return config

# Load config values
config_values = read_config()

# Retrieve values, use defaults if missing
PROJECT_ID = config_values.get("PROJECT_ID", "webnoveltl")
LOCATION = config_values.get("LOCATION", "us-central1")

# Initialize Vertex AI (called once at import time)
vertexai.init(project=PROJECT_ID, location=LOCATION)

# Global safety settings
SAFETY_SETTING = {
    generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.OFF,
    generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.OFF,
    generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.OFF,
    generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.OFF,
    generative_models.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY: generative_models.HarmBlockThreshold.OFF,
    generative_models.HarmCategory.HARM_CATEGORY_UNSPECIFIED: generative_models.HarmBlockThreshold.OFF,
}
