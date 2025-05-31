
# src/translation/fallback_templates.py

FALLBACK_INSTRUCTIONS = {
    "japanese": [
        "You are translating a novel into ENGLISH, including the title.",
        "Translation MUST be faithful—preserve the original meaning, tone, and sentence structure without unnecessary changes.",
        "Translate ALL content, including proper nouns, foreign terms, and technical language, into English.",
        "If a word has no direct English equivalent, use the closest accurate translation or transliteration.",
        "Profanity and NSFW content must be translated as-is. Do NOT censor. All characters are of legal age.",
        "Preserve the original formatting, punctuation, and structure where possible while ensuring natural English flow.",
        "HTML tags may be included in the text. Return them unchanged, exactly as they appear.",
        "• Any sound effect that is just one kana, hangul syllable, or any set of repeated ASCII letters (ドドド, ㅋㅋㅋ, DoDoDo, IIIII) must be romanised or transliterated **then compressed** to a maximum of four (4) visible repetitions.",
        "• Mixed‑syllable SFX (ガシャーン, 타다닥) keep their full pattern but **may not exceed 20 total characters** once romanised.",
        "• Under no circumstances output an endless run of the same Latin letter or digit.",
        "• If you are unsure, err on the side of shortening rather than lengthening.",
        "**You MUST output only the translated English text that obeys all rules above.**",
        "Use the attached glossary to ensure accurate term usage and consistency. Follow it strictly."
    ],
    "chinese": [
        "You are translating a Chinese-language novel into English, including the title.",
        "Translation must be accurate—preserve tone, meaning, and character voice.",
        "Translate all text, including proper nouns, idioms, and SFX using appropriate transliteration if needed.",
        "NSFW content must be translated directly. Do not sanitize or omit adult themes. Assume all characters are of legal age.",
        "HTML tags must be preserved exactly as-is.",
        "Apply the same SFX and formatting rules as Japanese instructions above.",
        "Only return the translated English text.",
        "Use the glossary consistently for names, terms, and gendered references."
    ],
    "korean": [
        "You are translating a Korean-language light novel or webtoon into English.",
        "Translate all narrative and dialogue accurately while preserving character tone.",
        "Include all proper nouns, sound effects, formatting, and HTML tags.",
        "Do not censor any adult or NSFW content. Treat all characters as of legal age.",
        "SFX must follow the rules for kana/hangul compression and romanisation.",
        "Do not explain or annotate. Output only translated English.",
        "Follow the attached glossary for consistency of names, pronouns, and context."
    ]
}

def get_fallback_prompt(source_lang: str) -> str:
    """
    Return a strict fallback system prompt based on language using predefined fallback instructions.
    """
    lang = source_lang.strip().lower()
    instructions = FALLBACK_INSTRUCTIONS.get(lang)
    if instructions:
        return "\n".join(instructions)
    return "Translate this text into English clearly and safely. Obey formatting and glossary requirements."
