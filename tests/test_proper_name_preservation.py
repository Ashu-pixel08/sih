"""
tests/test_proper_name_preservation.py
=============================================================================
SIH260042: Test Suite for Proper Name & Personal Name Preservation
Verifies that student and teacher proper names are preserved exactly
across Hindi, Hinglish, and Mundari translation pipelines without
transliteration, phonetic mangling, or placeholder leakage.
=============================================================================
"""

import pytest
from ai.translation.translation_engine import TranslationEngine
from ai.translation.proper_name_protector import ProperNameProtector


@pytest.fixture(scope="module")
def engine():
    return TranslationEngine(enable_neural=False)


@pytest.fixture(scope="module")
def protector():
    return ProperNameProtector()


# ---------------------------------------------------------------------------
# TEST GROUP 1: Hindi -> Mundari Proper Name Preservation
# ---------------------------------------------------------------------------

def test_hi_unr_mera_naam_rahul(engine):
    res = engine.translate("मेरा नाम Rahul है", direction="hi-unr")
    assert res.translated_text is not None
    assert "Rahul" in res.translated_text
    assert "__NAME_" not in res.translated_text
    assert "आञाः नुतुम Rahul" in res.translated_text


def test_hi_unr_mera_naam_amit(engine):
    res = engine.translate("मेरा नाम Amit है", direction="hi-unr")
    assert res.translated_text is not None
    assert "Amit" in res.translated_text
    assert "__NAME_" not in res.translated_text


def test_hi_unr_mera_naam_priya(engine):
    res = engine.translate("मेरा नाम Priya है", direction="hi-unr")
    assert res.translated_text is not None
    assert "Priya" in res.translated_text
    assert "__NAME_" not in res.translated_text


def test_hi_unr_devanagari_name_rahul(engine):
    res = engine.translate("मेरा नाम राहुल है", direction="hi-unr")
    assert res.translated_text is not None
    assert "राहुल" in res.translated_text
    assert "__NAME_" not in res.translated_text


# ---------------------------------------------------------------------------
# TEST GROUP 2: Hinglish -> Mundari Proper Name Preservation
# ---------------------------------------------------------------------------

def test_hinglish_mera_naam_rahul_hai(engine):
    res = engine.translate("mera naam Rahul hai", direction="hi-unr")
    assert res.translated_text is not None
    assert "Rahul" in res.translated_text
    assert "__NAME_" not in res.translated_text


def test_hinglish_mera_naam_amit_casing_preserved(engine):
    # Case must be preserved exactly as entered by user
    res = engine.translate("mera naam amit hai", direction="hi-unr")
    assert res.translated_text is not None
    assert "amit" in res.translated_text
    assert "__NAME_" not in res.translated_text


def test_hinglish_amit_ko_bulao(engine):
    res = engine.translate("Amit ko bulao", direction="hi-unr")
    assert res.translated_text is not None
    assert "Amit" in res.translated_text
    assert "__NAME_" not in res.translated_text
    assert "राःएमे" in res.translated_text


def test_hinglish_priya_baitho(engine):
    res = engine.translate("Priya baitho", direction="hi-unr")
    assert res.translated_text is not None
    assert "Priya" in res.translated_text
    assert "__NAME_" not in res.translated_text
    assert "दुबपे" in res.translated_text


def test_hinglish_rahul_aur_priya_baitho(engine):
    res = engine.translate("Rahul aur Priya baitho", direction="hi-unr")
    assert res.translated_text is not None
    assert "Rahul" in res.translated_text
    assert "Priya" in res.translated_text
    assert "__NAME_" not in res.translated_text
    assert "दुबपे" in res.translated_text


def test_hinglish_rahul_ko_bulao(engine):
    res = engine.translate("Rahul ko bulao", direction="hi-unr")
    assert res.translated_text is not None
    assert "Rahul" in res.translated_text
    assert "__NAME_" not in res.translated_text


def test_hinglish_rahul_yahan_aao(engine):
    res = engine.translate("Rahul yahan aao", direction="hi-unr")
    assert res.translated_text is not None
    assert "Rahul" in res.translated_text
    assert "__NAME_" not in res.translated_text
    assert "हिजुमे" in res.translated_text or "हिजुपे" in res.translated_text


# ---------------------------------------------------------------------------
# TEST GROUP 3: Mundari -> Hindi Reverse Proper Name Preservation
# ---------------------------------------------------------------------------

def test_unr_hi_anja_nutum_rahul(engine):
    res = engine.translate("आञाः नुतुम Rahul", direction="unr-hi")
    assert res.translated_text is not None
    assert "Rahul" in res.translated_text
    assert "__NAME_" not in res.translated_text
    assert "मेरा नाम Rahul है" in res.translated_text


def test_unr_hi_rahul_dubpe(engine):
    res = engine.translate("Rahul दुबपे", direction="unr-hi")
    assert res.translated_text is not None
    assert "Rahul" in res.translated_text
    assert "__NAME_" not in res.translated_text
    assert "बैठो" in res.translated_text


def test_unr_hi_rahul_dubme(engine):
    res = engine.translate("Rahul दुबमे", direction="unr-hi")
    assert res.translated_text is not None
    assert "Rahul" in res.translated_text
    assert "__NAME_" not in res.translated_text
    assert "बैठो" in res.translated_text


def test_unr_hi_rahul_ke_raeme(engine):
    res = engine.translate("Rahul के राःएमे", direction="unr-hi")
    assert res.translated_text is not None
    assert "Rahul" in res.translated_text
    assert "__NAME_" not in res.translated_text
    assert "बुलाओ" in res.translated_text


# ---------------------------------------------------------------------------
# TEST GROUP 4: Negative Vocabulary Tests (Words NEVER shielded as names)
# ---------------------------------------------------------------------------

def test_negative_numbers_never_shielded(protector):
    for num in ["एक", "दो", "तीन", "पाँच", "panch", "das", "मोड़ेया", "गेल"]:
        assert protector.is_negative_word(num) is True


def test_negative_verbs_never_shielded(protector):
    for verb in ["बैठो", "पढ़ो", "likho", "suno", "दुबपे", "पाड़ावपे"]:
        assert protector.is_negative_word(verb) is True


def test_negative_language_names_never_shielded(protector):
    for lang in ["Hindi", "hindi", "Mundari", "mundari", "English", "english", "हिंदी", "मुंडारी"]:
        assert protector.is_negative_word(lang) is True


def test_placeholder_never_leaks(protector):
    # Simulate partial or malformed placeholder in text
    malformed = "मेरा नाम __NAME_0__ है और __NAME_1__ भी"
    restored = protector.restore(malformed, {"__NAME_0__": "Rohit"})
    assert "__NAME_" not in restored
    assert "Rohit" in restored
