
# src/translation/fallback_templates.py

def get_fallback_prompt(source_lang: str) -> str:
    """
    Return a simplified or safer system prompt for fallback use if the main translation fails.
    """

    if source_lang.lower() == "japanese":
        return """You are a translator. Translate this Japanese text into English. Be concise and neutral.
Preserve the original meaning. Avoid offensive content. Skip untranslated tags or symbols.
Ignore or omit content that may trigger filters. Do not transliterate. Just translate."""

    elif source_lang.lower() == "chinese":
        return """Translate the following Chinese content into fluent English.
Keep the meaning clear. Avoid any inappropriate or sensitive content.
You may omit or simplify parts that could trigger content filters. Do not comment."""

    elif source_lang.lower() == "korean":
        return """Translate the following Korean text into English.
Avoid cultural jokes or explicit tone. Stay safe and literal if unsure.
Do not add any personal comments or context. Just provide the translation."""

    else:
        return "Translate this text into English clearly and safely. Skip or simplify any risky or sensitive parts."
