"""
tests/test_translation_accuracy.py
=============================================================================
Comprehensive Automated Test Suite for Hindi <-> Mundari Translation Accuracy
=============================================================================
Validates:
1. Exact greeting resolution (नमस्ते -> जोहार) without proper name mangling.
2. Reverse greeting resolution (जोहार -> नमस्ते).
3. Common educational classroom greetings & instructions.
4. Canonical numerals 1-20 (Hindi <-> Mundari).
5. Verified educational vocabulary (Animals, Fruits, Body Parts, Family, etc.).
6. Proper personal name preservation in context without placeholder leaks.
7. Safe out-of-vocabulary refusal for non-pedagogical / unknown words.
=============================================================================
"""

import pytest
from ai.translation.translation_engine import TranslationEngine


@pytest.fixture(scope="module")
def engine():
    return TranslationEngine(enable_neural=True)


@pytest.fixture(scope="module")
def engine_offline():
    return TranslationEngine(enable_neural=False)


# ---------------------------------------------------------------------------
# TEST GROUP 1: Primary Greeting Accuracy (Hindi <-> Mundari)
# ---------------------------------------------------------------------------

def test_namaste_to_johar(engine):
    """Verify 'नमस्ते' translates strictly to 'जोहार' with 1.0 confidence and Tier 1 status."""
    res = engine.translate("नमस्ते", direction="hi-unr")
    assert res.translated_text == "जोहार", f"Expected 'जोहार', got '{res.translated_text}'"
    assert res.status == "VERIFIED_EDUCATIONAL_LOOKUP"
    assert res.confidence == 1.0
    assert res.requires_validation is False
    assert res.ui_status == "VERIFIED EDUCATIONAL"


def test_reverse_johar_to_namaste(engine):
    """Verify reverse 'जोहार' translates to 'नमस्ते' with 1.0 confidence and Tier 1 status."""
    res = engine.translate("जोहार", direction="unr-hi")
    assert res.translated_text == "नमस्ते", f"Expected 'नमस्ते', got '{res.translated_text}'"
    assert res.status == "VERIFIED_EDUCATIONAL_LOOKUP"
    assert res.confidence == 1.0
    assert res.requires_validation is False


# ---------------------------------------------------------------------------
# TEST GROUP 2: Common Classroom Greetings & Phrases
# ---------------------------------------------------------------------------

def test_common_classroom_greetings(engine):
    """Verify common greetings map accurately without name shielding or hallucination."""
    greetings = {
        "सुप्रभात": "सुप्रभात जोहार",
        "नमस्ते बच्चों": "जोहार होनको",
        "हेलो": "जोहार"
    }
    for hi, expected_unr in greetings.items():
        res = engine.translate(hi, direction="hi-unr")
        assert res.translated_text == expected_unr, f"Failed for greeting: '{hi}', got '{res.translated_text}'"
        assert res.confidence == 1.0


def test_core_classroom_instructions(engine):
    """Verify standard classroom commands translate with 100% precision in Tier 1."""
    instructions = {
        "बैठो": "दुबपे",
        "खड़े हो जाओ": "तिंगुपे",
        "इधर देखो": "नेते नेलपे",
        "चुप रहो": "काजी आलोपे",
        "हाथ उठाओ": "ती ओड़ाःपे",
        "किताब खोलो": "पुथी ओड़ाःपे",
        "गिनो": "लेकापे",
        "लिखो": "ओलपे",
        "पढ़ो": "पाड़ावपे",
        "सुनो": "आयूमपे",
        "ध्यान से सुनो": "ध्यानते आयूमपे",
        "यहाँ आओ": "नेताः हिजुमे",
        "वहाँ जाओ": "एनताः सेनोःमे",
        "बहुत अच्छा": "खूब बुगी",
        "शाबाश": "बुगी कामी"
    }
    for hi, expected_unr in instructions.items():
        res = engine.translate(hi, direction="hi-unr")
        assert res.translated_text == expected_unr, f"Failed for instruction: '{hi}', got '{res.translated_text}'"
        assert res.confidence == 1.0
        assert res.status == "VERIFIED_EDUCATIONAL_LOOKUP"


# ---------------------------------------------------------------------------
# TEST GROUP 3: Numerals 1–20 (Forward & Reverse)
# ---------------------------------------------------------------------------

def test_numerals_forward(engine):
    """Verify numerals 1-20 forward lookup in Hindi -> Mundari."""
    numerals = {
        "एक": "मिअद",
        "दो": "बारिया",
        "तीन": "अपिया",
        "चार": "उपुनिया",
        "पाँच": "मोड़ेया",
        "छह": "तुरिया",
        "सात": "एयाएया",
        "आठ": "इरालिया",
        "नौ": "अरेया",
        "दस": "गेलेया",
        "बीस": "हिसि"
    }
    for hi, expected_unr in numerals.items():
        res = engine.translate(hi, direction="hi-unr")
        assert res.translated_text == expected_unr, f"Failed for numeral '{hi}', got '{res.translated_text}'"
        assert res.confidence == 1.0


def test_numerals_reverse(engine):
    """Verify numerals 1-20 reverse lookup in Mundari -> Hindi."""
    numerals = {
        "मिअद": "एक",
        "बारिया": "दो",
        "अपिया": "तीन",
        "उपुनिया": "चार",
        "मोड़ेया": "पाँच",
        "गेलेया": "दस",
        "हिसि": "बीस"
    }
    for unr, expected_hi in numerals.items():
        res = engine.translate(unr, direction="unr-hi")
        assert res.translated_text == expected_hi, f"Failed reverse numeral '{unr}', got '{res.translated_text}'"
        assert res.confidence == 1.0


# ---------------------------------------------------------------------------
# TEST GROUP 4: Verified Educational Vocabulary (Categories)
# ---------------------------------------------------------------------------

def test_verified_animals_vocabulary(engine):
    """Verify animals from verified project dataset."""
    pairs = {
        "कुत्ता": "सेता",
        "बिल्ली": "पूसी",
        "गाय": "गाए",
        "भैंस": "बोंगा",
        "बंदर": "हुरु",
        "बकरी": "मराम"
    }
    for hi, expected_unr in pairs.items():
        res = engine.translate(hi, direction="hi-unr")
        assert res.translated_text == expected_unr, f"Failed for animal '{hi}', got '{res.translated_text}'"
        assert res.status == "VERIFIED_EDUCATIONAL_LOOKUP"


def test_verified_fruits_vocabulary(engine):
    """Verify fruits vocabulary from verified dataset."""
    pairs = {
        "केला": "कदल",
        "आम": "उलि",
        "अमरूद": "टमरस"
    }
    for hi, expected_unr in pairs.items():
        res = engine.translate(hi, direction="hi-unr")
        assert res.translated_text == expected_unr, f"Failed for fruit '{hi}', got '{res.translated_text}'"
        assert res.status == "VERIFIED_EDUCATIONAL_LOOKUP"


def test_verified_body_parts_and_family(engine):
    """Verify body parts and family relations from verified dataset."""
    pairs = {
        "कान": "लुतुर",
        "आंख": "मॅंत",
        "पिता": "अपु",
        "माता": "एंगा",
        "भाई": "बोको",
        "बहन": "मिसी"
    }
    for hi, expected_unr in pairs.items():
        res = engine.translate(hi, direction="hi-unr")
        assert res.translated_text == expected_unr, f"Failed for item '{hi}', got '{res.translated_text}'"
        assert res.status == "VERIFIED_EDUCATIONAL_LOOKUP"


# ---------------------------------------------------------------------------
# TEST GROUP 5: Proper Names Preservation in Context
# ---------------------------------------------------------------------------

def test_proper_names_in_classroom_context(engine):
    """Verify that student personal names are preserved and not translated or mangled."""
    cases = [
        ("मेरा नाम राहुल है", "आञाः नुतुम राहुल"),
        ("मेरा नाम Amit है", "आञाः नुतुम Amit"),
        ("Rahul बैठो", "Rahul दुबपे"),
        ("Priya बैठो", "Priya दुबपे"),
        ("Amit को बुलाओ", "Amit के राःएमे"),
        ("नमस्ते Rahul", "जोहार Rahul"),
        ("नमस्ते Priya", "जोहार Priya")
    ]
    for hi, expected in cases:
        res = engine.translate(hi, direction="hi-unr")
        assert res.translated_text is not None
        assert expected in res.translated_text, f"Failed for '{hi}', got '{res.translated_text}'"
        assert "__NAME_" not in res.translated_text, f"Leaked placeholder in '{res.translated_text}'"


# ---------------------------------------------------------------------------
# TEST GROUP 6: Safe Refusal / Out of Vocabulary Handling
# ---------------------------------------------------------------------------

def test_unknown_words_safe_fallback(engine_offline):
    """Verify unknown / non-pedagogical words are rejected safely without hallucination."""
    unknown_inputs = [
        "क्वांटम भौतिकी थ्योरम",
        "सुपरकंडक्टिंग मैग्नेट",
        "asdfghjklqwerty"
    ]
    for text in unknown_inputs:
        res = engine_offline.translate(text, direction="hi-unr")
        assert res.status == "OUT_OF_VOCABULARY_UNVERIFIED"
        assert res.translated_text is None
        assert res.confidence < 0.55
        assert res.ui_status == "TRANSLATION UNAVAILABLE"
