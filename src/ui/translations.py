import gc, json
from pathlib import Path

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
DATA.mkdir(parents=True, exist_ok=True)

TRANSLATION_FILE = DATA / "ui_translations.json"
TRANSLATION_MODEL = "facebook/nllb-200-distilled-600M"

LANGUAGE_CODES = {
    "Malay": "zsm_Latn",
    "Chinese": "zho_Hans",
    "Tamil": "tam_Taml",
}

ENGLISH_TEXT = {
    "home": "Home",
    "check_in": "Check-in",
    "trends": "Trends",
    "settings": "Settings",
    "logout": "Log out",
    "welcome": "Welcome",
    "start_check_in": "Start check-in",

    "settings_title": "Settings",
    "settings_subtitle": "Manage your application preferences.",
    "language": "Language",
    "language_description":
        "Choose the language used for the interface, speech recognition and wellbeing recommendations.",
    "application_language": "Application language",
    "language_note": "The selected language will be used for future check-ins.",
}

TRANSLATIONS = {}


def load_translations():
    if TRANSLATION_FILE.exists():
        with open(TRANSLATION_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    return {}


def save_translations(data):
    with open(TRANSLATION_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def translate_batch(model, tokenizer, texts, language, device):
    tokenizer.src_lang = "eng_Latn"
    target_id = tokenizer.convert_tokens_to_ids(LANGUAGE_CODES[language])
    translated = []

    for start in range(0, len(texts), 8):
        batch = texts[start:start + 8]

        inputs = tokenizer(
            batch,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=256,
        )
        inputs = {key: value.to(device) for key, value in inputs.items()}

        with torch.inference_mode():
            output = model.generate(
                **inputs,
                forced_bos_token_id=target_id,
                max_length=256,
            )

        translated.extend(
            tokenizer.batch_decode(output, skip_special_tokens=True)
        )

    return translated


def prepare_translations():
    global TRANSLATIONS

    saved = load_translations()
    old_english = saved.get("English", {})

    changed = {
        key
        for key, value in ENGLISH_TEXT.items()
        if old_english.get(key) != value
    }

    saved["English"] = dict(ENGLISH_TEXT)

    missing = {
        language: [
            key for key in ENGLISH_TEXT
            if key in changed or key not in saved.get(language, {})
        ]
        for language in LANGUAGE_CODES
    }

    missing = {
        language: keys
        for language, keys in missing.items()
        if keys
    }

    if missing:
        device = "cuda" if torch.cuda.is_available() else "cpu"

        tokenizer = AutoTokenizer.from_pretrained(
            TRANSLATION_MODEL,
            src_lang="eng_Latn",
        )

        model = AutoModelForSeq2SeqLM.from_pretrained(
            TRANSLATION_MODEL
        ).to(device)
        model.eval()

        for language, keys in missing.items():
            results = translate_batch(
                model,
                tokenizer,
                [ENGLISH_TEXT[key] for key in keys],
                language,
                device,
            )

            saved.setdefault(language, {})

            for key, text in zip(keys, results):
                saved[language][key] = text.strip()

        del model, tokenizer
        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    save_translations(saved)
    TRANSLATIONS = saved


def get_text(language, key):
    return TRANSLATIONS.get(language, {}).get(key) or ENGLISH_TEXT.get(key, key)


def translate_text(text, language):
    if language == "English":
        return text

    device = "cuda" if torch.cuda.is_available() else "cpu"

    tokenizer = AutoTokenizer.from_pretrained(
        TRANSLATION_MODEL,
        src_lang="eng_Latn",
    )

    model = AutoModelForSeq2SeqLM.from_pretrained(
        TRANSLATION_MODEL
    ).to(device)
    model.eval()

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=512,
    )
    inputs = {key: value.to(device) for key, value in inputs.items()}

    with torch.inference_mode():
        output = model.generate(
            **inputs,
            forced_bos_token_id=tokenizer.convert_tokens_to_ids(
                LANGUAGE_CODES[language]
            ),
            max_length=512,
        )

    translated = tokenizer.batch_decode(
        output,
        skip_special_tokens=True,
    )[0]

    del model, tokenizer
    gc.collect()

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return translated.strip()