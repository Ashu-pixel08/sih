"""
tests/test_hinglish_normalizer.py
Comprehensive test suite for Governed Hinglish Normalization and Hinglish -> Mundari Translation:
1. Governed Lexicon validation (schema, non-empty, required fields)
2. Normalizer phrase matching (longest-match, case-insensitive)
3. Spelling & phonetic variant tolerance (baitho / betho, panch / paanch)
4. FLN Numerals 1-20 coverage
5. Multi-word classroom instructions
6. Ambiguity handling (kal marked AMBIGUOUS with confidence degradation)
7. Anti-hallucination safety (unattested Latin words remain unmapped and trigger OOV)
8. End-to-end TranslationEngine translation (Hinglish -> Devanagari -> Mundari)
9. Non-regression of standard Devanagari Hindi -> Mundari translation
"""

import os
import sys
import json
import pytest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ai.translation.hinglish_normalizer import HinglishNormalizer, HinglishNormalizationResult
from ai.translation.translation_engine import TranslationEngine, TranslationResult


@pytest.fixture(scope="module")
def normalizer():
    return HinglishNormalizer()


@pytest.fixture(scope="module")
def engine():
    return TranslationEngine()


class TestGovernedHinglishLexicon:
    """Validates the structure and content of data/approved/hinglish/governed_hinglish_lexicon.json."""

    def test_lexicon_file_exists_and_loads(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "approved", "hinglish", "governed_hinglish_lexicon.json"
        )
        assert os.path.exists(path), f"Lexicon file missing at {path}"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) >= 80, f"Expected at least 80 governed entries, got {len(data)}"

    def test_lexicon_entries_schema(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "approved", "hinglish", "governed_hinglish_lexicon.json"
        )
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        required_keys = {"hinglish", "hindi", "category", "source", "status"}
        for entry in data:
            missing = required_keys - set(entry.keys())
            assert not missing, f"Entry {entry} is missing keys: {missing}"
            assert entry["hinglish"].strip(), "hinglish key cannot be blank"
            assert entry["hindi"].strip(), "hindi key cannot be blank"


class TestHinglishNormalizerRules:
    """Unit tests for the HinglishNormalizer module."""

    def test_exact_phrase_normalization(self, normalizer):
        # Greetings
        res = normalizer.normalize("namaste")
        assert res.normalized_hindi == "नमस्ते"
        assert res.status == "EXACT_MATCH"

        res = normalizer.normalize("NAMASTE")
        assert res.normalized_hindi == "नमस्ते"

        # Classroom instructions
        res = normalizer.normalize("baitho")
        assert res.normalized_hindi == "बैठो"
        assert res.status == "EXACT_MATCH"

        res = normalizer.normalize("kitab kholo")
        assert res.normalized_hindi == "किताब खोलो"
        assert res.status == "EXACT_MATCH"

    def test_spelling_variants_tolerance(self, normalizer):
        # betho -> बैठो
        res = normalizer.normalize("betho")
        assert res.normalized_hindi == "बैठो"

        # kitaab kholo -> किताब खोलो
        res = normalizer.normalize("kitaab kholo")
        assert res.normalized_hindi == "किताब खोलो"

        # panch / paanch -> पाँच
        res1 = normalizer.normalize("panch")
        res2 = normalizer.normalize("paanch")
        assert res1.normalized_hindi == "पाँच"
        assert res2.normalized_hindi == "पाँच"

        # bahut accha / bahut achha -> बहुत अच्छा
        res_accha = normalizer.normalize("bahut accha")
        assert res_accha.normalized_hindi == "बहुत अच्छा"

    def test_fln_numerals_1_to_20(self, normalizer):
        expected_numerals = {
            "ek": "एक",
            "do": "दो",
            "teen": "तीन",
            "char": "चार",
            "paanch": "पाँच",
            "chhah": "छह",
            "saat": "सात",
            "aath": "आठ",
            "nau": "नौ",
            "das": "दस",
            "gyarah": "ग्यारह",
            "barah": "बारह",
            "terah": "तेरह",
            "chaudah": "चौदह",
            "pandrah": "पंद्रह",
            "solah": "सोलह",
            "satrah": "सत्रह",
            "atharah": "अठारह",
            "unnis": "उन्नीस",
            "bees": "बीस",
        }
        for hinglish_num, devanagari_num in expected_numerals.items():
            res = normalizer.normalize(hinglish_num)
            assert res.normalized_hindi == devanagari_num, (
                f"Failed for numeral {hinglish_num}: got {res.normalized_hindi}, expected {devanagari_num}"
            )

    def test_multi_word_longest_match(self, normalizer):
        res = normalizer.normalize("khade ho jao")
        assert res.normalized_hindi == "खड़े हो जाओ"

        res = normalizer.normalize("ek se das tak gino")
        assert res.normalized_hindi == "एक से दस तक गिनो"

    def test_ambiguity_handling(self, normalizer):
        res = normalizer.normalize("kal")
        assert res.status == "AMBIGUOUS"
        assert res.confidence <= 0.5
        assert "HELD_FOR_REVIEW" in res.notes or "Ambiguous" in res.notes

    def test_anti_hallucination_for_unknown_words(self, normalizer):
        res = normalizer.normalize("xyzrandom")
        assert res.status == "UNRESOLVED"
        assert res.confidence == 0.0
        assert "xyzrandom" in res.unmapped_tokens
        # Must NOT fabricate synthetic Devanagari
        assert res.normalized_hindi == "xyzrandom"

    def test_empty_and_whitespace_input(self, normalizer):
        assert normalizer.normalize("").status == "EMPTY_INPUT"
        assert normalizer.normalize("   ").status == "EMPTY_INPUT"
        assert normalizer.normalize(None).status == "EMPTY_INPUT"


class TestEndToEndHinglishToMundariTranslation:
    """Verifies end-to-end integration in TranslationEngine with src_lang='hinglish'."""

    def test_hinglish_greetings_translate_to_mundari(self, engine):
        res = engine.translate("namaste", direction="hi-unr", src_lang="hinglish")
        assert res.status == "VERIFIED_EDUCATIONAL_LOOKUP"
        assert res.translated_text == "जोहार"
        assert res.ui_status == "VERIFIED EDUCATIONAL"
        assert res.metadata.get("normalized_hindi") == "नमस्ते"

    def test_hinglish_classroom_instructions_translate(self, engine):
        # baitho -> बैठो -> दुबपे
        res = engine.translate("baitho", direction="hi-unr", src_lang="hinglish")
        assert res.status == "VERIFIED_EDUCATIONAL_LOOKUP"
        assert res.translated_text == "दुबपे"
        assert res.ui_status == "VERIFIED EDUCATIONAL"

        # kitab kholo -> किताब खोलो -> पुथी ओड़ाःपे
        res = engine.translate("kitab kholo", direction="hi-unr", src_lang="hinglish")
        assert res.status == "VERIFIED_EDUCATIONAL_LOOKUP"
        assert res.translated_text == "पुथी ओड़ाःपे"
        assert res.ui_status == "VERIFIED EDUCATIONAL"

    def test_hinglish_numerals_translate(self, engine):
        # paanch -> पाँच -> मोड़ेया
        res = engine.translate("paanch", direction="hi-unr", src_lang="hinglish")
        assert res.status == "VERIFIED_EDUCATIONAL_LOOKUP"
        assert "मो" in res.translated_text
        assert res.ui_status == "VERIFIED EDUCATIONAL"

    def test_unattested_hinglish_safely_refused(self, engine):
        res = engine.translate("xyzrandom_unattested", direction="hi-unr", src_lang="hinglish")
        assert res.status == "OUT_OF_VOCABULARY_UNVERIFIED"
        assert res.translated_text is None
        assert res.ui_status == "TRANSLATION UNAVAILABLE"

    def test_zero_regression_on_standard_devanagari(self, engine):
        """Devanagari Hindi translations must continue functioning identically."""
        res_hi = engine.translate("नमस्ते", direction="hi-unr")
        assert res_hi.status == "VERIFIED_EDUCATIONAL_LOOKUP"
        assert res_hi.translated_text == "जोहार"

        res_baitho = engine.translate("बैठो", direction="hi-unr")
        assert res_baitho.status == "VERIFIED_EDUCATIONAL_LOOKUP"
        assert res_baitho.translated_text == "दुबपे"

        res_paanch = engine.translate("पाँच", direction="hi-unr")
        assert res_paanch.status == "VERIFIED_EDUCATIONAL_LOOKUP"
        assert "मो" in res_paanch.translated_text
