"""
tests/test_translation_expansion.py
=============================================================================
SIH260042: Translation Expansion & Indic Normalization Test Suite
=============================================================================
Validates:
1. All numbers 1-20 in words, Devanagari numerals, and digits.
2. Orthographic normalizer equivalence (पाँच/पांच, छह/छः/छ:, पंद्रह/पन्द्रह, अट्ठारह/अठारह).
3. Core classroom instructions (नमस्ते, बैठो, खड़े हो जाओ, किताब खोलो, गिनो, लिखो, पढ़ो, बहुत अच्छा).
4. Expanded phrases (हेलो, नमस्ते बच्चों, सभी किताब खोलो, मेरा नाम).
5. 17.8k parallel corpus retrieval for longer Hindi sentences.
6. Safe OOV refusal to hallucinate for unsupported/unrelated queries.
7. Reverse translation (Mundari -> Hindi).
8. Strict offline architecture (No INTERNET permission in AndroidManifest.xml).
=============================================================================
"""

import os
import sys
import unittest
import xml.etree.ElementTree as ET

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from ai.translation.hindi_normalizer import normalize_hindi, normalize_for_lookup
from ai.translation.translation_engine import TranslationEngine, TranslationResult


class TestTranslationExpansion(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = TranslationEngine()

    # -------------------------------------------------------------------------
    # 1. Normalizer Unit Tests
    # -------------------------------------------------------------------------
    def test_normalizer_anusvara_chandrabindu_equivalence(self):
        """Verify 'पाँच' and 'पांच' normalize to identical lookup keys."""
        k1 = normalize_for_lookup("पाँच")
        k2 = normalize_for_lookup("पांच")
        self.assertEqual(k1, k2)
        self.assertEqual(k1, "पांच")

    def test_normalizer_numeral_aliases(self):
        """Verify numeral spelling aliases resolve to standard forms."""
        self.assertEqual(normalize_for_lookup("छ:"), "छह")
        self.assertEqual(normalize_for_lookup("छः"), "छह")
        self.assertEqual(normalize_for_lookup("छ"), "छह")
        self.assertEqual(normalize_for_lookup("पन्द्रह"), "पंद्रह")
        self.assertEqual(normalize_for_lookup("पंद्रह"), "पंद्रह")
        self.assertEqual(normalize_for_lookup("अट्ठारह"), "अठारह")

    def test_normalizer_danda_and_punctuation_stripping(self):
        """Verify Indic dandas and standard punctuation are cleanly stripped."""
        raw = "नमस्ते! क्या हाल है? किताब खोलो।"
        clean = normalize_hindi(raw)
        self.assertNotIn("।", clean)
        self.assertNotIn("!", clean)
        self.assertNotIn("?", clean)
        self.assertEqual(clean, "नमस्ते क्या हाल है किताब खोलो")

    # -------------------------------------------------------------------------
    # 2. Numbers 1–20 Translation Tests
    # -------------------------------------------------------------------------
    def test_all_numbers_1_to_20_words(self):
        """Verify every numeral from 1 to 20 translates to attested Mundari word."""
        expected_numbers = {
            "एक": "मिअद", "दो": "बारिया", "तीन": "अपिया", "चार": "उपुनिया",
            "पाँच": "मोड़ेया", "छह": "तुरिया", "सात": "एयाएया", "आठ": "इरालिया",
            "नौ": "अरेया", "दस": "गेलेया", "ग्यारह": "गेल मिअद", "बारह": "गेल बारिया",
            "तेरह": "गेल अपिया", "चौदह": "गेल उपुनिया", "पंद्रह": "गेल मोड़ेया",
            "सोलह": "गेल तुरिया", "सत्रह": "गेल एयाएया", "अठारह": "गेल इरालिया",
            "उन्नीस": "गेल अरेया", "बीस": "हिसि"
        }
        for hi_word, expected_mun in expected_numbers.items():
            res = self.engine.translate(hi_word, direction="hi-unr")
            self.assertIn(res.status, ("VERIFIED_EDUCATIONAL_LOOKUP", "EXACT_CANONICAL_LOOKUP"))
            self.assertEqual(res.confidence, 1.0)
            self.assertEqual(res.translated_text, expected_mun, f"Failed for numeral: {hi_word}")

    def test_number_spelling_variants(self):
        """Verify spelling variants of numbers translate identically."""
        # 5 variants
        res_5a = self.engine.translate("पाँच")
        res_5b = self.engine.translate("पांच")
        res_5c = self.engine.translate("५")
        res_5d = self.engine.translate("5")
        self.assertEqual(res_5a.translated_text, "मोड़ेया")
        self.assertEqual(res_5b.translated_text, "मोड़ेया")
        self.assertEqual(res_5c.translated_text, "मोड़ेया")
        self.assertEqual(res_5d.translated_text, "मोड़ेया")

        # 6 variants
        res_6a = self.engine.translate("छह")
        res_6b = self.engine.translate("छः")
        res_6c = self.engine.translate("छ:")
        self.assertEqual(res_6a.translated_text, "तुरिया")
        self.assertEqual(res_6b.translated_text, "तुरिया")
        self.assertEqual(res_6c.translated_text, "तुरिया")

        # 15 variants
        res_15a = self.engine.translate("पंद्रह")
        res_15b = self.engine.translate("पन्द्रह")
        self.assertEqual(res_15a.translated_text, "गेल मोड़ेया")
        self.assertEqual(res_15b.translated_text, "गेल मोड़ेया")

    # -------------------------------------------------------------------------
    # 3. Core Classroom Instructions Tests
    # -------------------------------------------------------------------------
    def test_core_classroom_instructions(self):
        """Verify standard classroom commands translate with 100% precision."""
        commands = {
            "नमस्ते": "जोहार",
            "बैठो": "दुबपे",
            "खड़े हो जाओ": "तिंगुपे",
            "किताब खोलो": "पुथी ओड़ाःपे",
            "गिनो": "लेकापे",
            "लिखो": "ओलपे",
            "पढ़ो": "पाड़ावपे",
            "बहुत अच्छा": "खूब बुगी"
        }
        for cmd, expected_mun in commands.items():
            res = self.engine.translate(cmd)
            self.assertEqual(res.confidence, 1.0, f"Confidence not 1.0 for: {cmd}")
            self.assertEqual(res.translated_text, expected_mun, f"Incorrect translation for: {cmd}")

    # -------------------------------------------------------------------------
    # 4. Expanded Phrases Tests
    # -------------------------------------------------------------------------
    def test_expanded_phrases(self):
        """Verify expanded classroom phrases (हेलो, नमस्ते बच्चों, सभी किताब खोलो, मेरा नाम)."""
        # हेलो
        res_hello = self.engine.translate("हेलो")
        self.assertEqual(res_hello.translated_text, "जोहार")
        self.assertEqual(res_hello.confidence, 1.0)

        # नमस्ते बच्चों
        res_greet_kids = self.engine.translate("नमस्ते बच्चों")
        self.assertEqual(res_greet_kids.translated_text, "जोहार होनको")
        self.assertEqual(res_greet_kids.status, "COMPOSED_FROM_ATTESTED_FRAGMENTS")

        # सभी किताब खोलो
        res_open_books = self.engine.translate("सभी किताब खोलो")
        self.assertEqual(res_open_books.translated_text, "सोबेन पुथी ओड़ाःपे")
        self.assertEqual(res_open_books.status, "COMPOSED_FROM_ATTESTED_FRAGMENTS")

        # मेरा नाम
        res_my_name = self.engine.translate("मेरा नाम")
        self.assertEqual(res_my_name.translated_text, "आञाः नुतुम")
        self.assertEqual(res_my_name.confidence, 1.0)

    # -------------------------------------------------------------------------
    # 5. 17.8k Parallel Corpus Retrieval Tests
    # -------------------------------------------------------------------------
    def test_parallel_corpus_sentence_retrieval(self):
        """Verify longer Hindi sentences from 17.8k corpus match correctly."""
        test_sentences = [
            ("पानी के फव्वारों को हफ्ते में एक दिन सुखा दें।", "दाः राः फव्वारा पीटि रे मोसा आनजेदकेपे।"),
            ("घर बार सब जल उठा।", "ओड़ाः दुआर सोबेन ओनडोताना।"),
            ("उन्होंने अपनी स्कूलिंग पूरी कर ली है।", "इनिः आएः इसकुल पाड़ाओ चाबाकेदाएः।")
        ]
        for hi_sent, expected_mun in test_sentences:
            res = self.engine.translate(hi_sent)
            self.assertEqual(res.status, "CORPUS_RETRIEVAL_MATCH")
            self.assertGreaterEqual(res.confidence, 0.80)
            self.assertEqual(res.translated_text, expected_mun)

    # -------------------------------------------------------------------------
    # 6. Safe Out-of-Vocabulary Fallback Tests
    # -------------------------------------------------------------------------
    def test_safe_oov_rejection_without_hallucination(self):
        """Verify unrelated / out-of-domain queries are strictly rejected without hallucination."""
        oov_queries = [
            "क्वांटम कंप्यूटिंग अल्गोरिदम",
            "मंगल ग्रह पर रोवर खोज कर रहा है",
            "अंतर्राष्ट्रीय अंतरिक्ष स्टेशन पर शोध"
        ]
        for q in oov_queries:
            res = self.engine.translate(q)
            self.assertEqual(res.status, "OUT_OF_VOCABULARY_UNVERIFIED")
            self.assertIsNone(res.translated_text, f"Must not hallucinate for OOV: {q}")
            self.assertEqual(res.match_type, "BELOW_CONFIDENCE_THRESHOLD")

    # -------------------------------------------------------------------------
    # 7. Reverse Translation Tests (Mundari -> Hindi)
    # -------------------------------------------------------------------------
    def test_reverse_translation_mundari_to_hindi(self):
        """Verify reverse direction translates Mundari terms back to Hindi."""
        reverse_cases = {
            "मिअद": "एक",
            "बारिया": "दो",
            "दुबपे": "बैठो",
            "जोहार": "नमस्ते",
            "आञाः नुतुम": "मेरा नाम"
        }
        for mun, expected_hi in reverse_cases.items():
            res = self.engine.translate(mun, direction="unr-hi")
            self.assertEqual(res.confidence, 1.0)
            self.assertEqual(res.translated_text, expected_hi, f"Reverse translation failed for: {mun}")

    # -------------------------------------------------------------------------
    # 8. Offline Mandate Verification
    # -------------------------------------------------------------------------
    def test_android_manifest_no_internet_permission(self):
        """Verify AndroidManifest.xml strictly does NOT declare android.permission.INTERNET."""
        manifest_path = os.path.join(WORKSPACE_ROOT, "android", "app", "src", "main", "AndroidManifest.xml")
        self.assertTrue(os.path.exists(manifest_path), f"Manifest not found: {manifest_path}")

        tree = ET.parse(manifest_path)
        root = tree.getroot()

        # Check for any uses-permission elements
        permissions = []
        for elem in root.findall("uses-permission"):
            name = elem.attrib.get("{http://schemas.android.com/apk/res/android}name", "")
            permissions.append(name)

        self.assertNotIn(
            "android.permission.INTERNET",
            permissions,
            "CRITICAL: AndroidManifest.xml must NOT request INTERNET permission! Android must operate 100% offline."
        )


if __name__ == "__main__":
    unittest.main()
