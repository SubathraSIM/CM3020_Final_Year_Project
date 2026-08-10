import src.ui.translations as translations


# Test case 1: Check that the selected translation model is NLLB-200
def test_translation_model():
    assert translations.TRANSLATION_MODEL == (
        "facebook/nllb-200-distilled-600M"
    )


# Test case 2: Check that Malay uses the correct NLLB language code
def test_malay_language_code():
    assert translations.LANGUAGE_CODES[
        "Malay"
    ] == "zsm_Latn"


# Test case 3: Check that Chinese uses the correct NLLB language code
def test_chinese_language_code():
    assert translations.LANGUAGE_CODES[
        "Chinese"
    ] == "zho_Hans"


# Test case 4: Check that Tamil uses the correct NLLB language code
def test_tamil_language_code():
    assert translations.LANGUAGE_CODES[
        "Tamil"
    ] == "tam_Taml"


# Test case 5: Check that all supported translation languages are available
def test_supported_languages():
    assert set(
        translations.LANGUAGE_CODES.keys()
    ) == {
        "Malay",
        "Chinese",
        "Tamil",
    }


# Test case 6: Check that important English interface text is registered
def test_english_interface_text():
    assert translations.ENGLISH_TEXT[
        "home"
    ] == "Home"

    assert translations.ENGLISH_TEXT[
        "check_in"
    ] == "Check-in"

    assert translations.ENGLISH_TEXT[
        "trends"
    ] == "Trends"

    assert translations.ENGLISH_TEXT[
        "settings"
    ] == "Settings"

    assert translations.ENGLISH_TEXT[
        "logout"
    ] == "Log out"


# Test case 7: Check that English text does not go through translation
def test_english_translation_bypass():
    text = (
        "Take a short break after your shift."
    )

    result = translations.translate_text(
        text,
        "English"
    )

    assert result == text


# Test case 8: Check that English interface text can be retrieved correctly
def test_get_english_text():
    original_translations = (
        translations.TRANSLATIONS
    )

    translations.TRANSLATIONS = {
        "English": dict(
            translations.ENGLISH_TEXT
        )
    }

    result = translations.get_text(
        "English",
        "home"
    )

    translations.TRANSLATIONS = (
        original_translations
    )

    assert result == "Home"


# Test case 9: Check that translated interface text can be retrieved correctly
def test_get_translated_text():
    original_translations = (
        translations.TRANSLATIONS
    )

    translations.TRANSLATIONS = {
        "Malay": {
            "home": "Laman utama"
        }
    }

    result = translations.get_text(
        "Malay",
        "home"
    )

    translations.TRANSLATIONS = (
        original_translations
    )

    assert result == "Laman utama"