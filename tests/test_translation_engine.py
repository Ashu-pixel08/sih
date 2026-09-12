import os
import sys
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ai.translation.translation_engine import TranslationEngine, TranslationResult


class TestTranslationEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = TranslationEngine()

    def test_exact_1_to_20_lookup(self):
        """Verify all numbers 1 to 20 match with 100% confidence and VERIFIED_EDUCATIONAL_LOOKUP."""
        hindi_number_words = [
            "एक", "दो", "तीन", "चार", "पाँच",
            "छह", "सात", "आठ", "नौ", "दस",
            "ग्यारह", "बारह", "तेरह", "चौदह", "पंद्रह",
            "सोलह", "सत्रह", "अठारह", "उन्नीस", "बीस"
        ]
        hindi_numerals = [
            "१", "२", "३", "४", "५",
            "६", "७", "८", "९", "१०",
            "११", "१२", "१३", "१४", "१५",
            "१६", "१७", "१८", "१९", "२०"
        ]

        for idx in range(1, 21):
            word = hindi_number_words[idx - 1]
            numeral = hindi_numerals[idx - 1]
            digit = str(idx)

            # Test by Hindi word
            res_word = self.engine.translate(word)
            self.assertEqual(res_word.status, "VERIFIED_EDUCATIONAL_LOOKUP", f"Failed for word: {word}")
            self.assertEqual(res_word.confidence, 1.0)
            self.assertTrue(res_word.translated_text)
            self.assertEqual(res_word.metadata["number"], idx)

            # Test by Hindi numeral
            res_num = self.engine.translate(numeral)
            self.assertEqual(res_num.status, "VERIFIED_EDUCATIONAL_LOOKUP", f"Failed for numeral: {numeral}")
            self.assertEqual(res_num.confidence, 1.0)
            self.assertEqual(res_num.translated_text, res_word.translated_text)

            # Test by ASCII digit
            res_digit = self.engine.translate(digit)
            self.assertEqual(res_digit.status, "VERIFIED_EDUCATIONAL_LOOKUP", f"Failed for digit: {digit}")
            self.assertEqual(res_digit.confidence, 1.0)
            self.assertEqual(res_digit.translated_text, res_word.translated_text)

    def test_educational_phrasebook_lookup(self):
        """Verify classroom commands and greetings map correctly in Tier 1."""
        phrases = {
            "नमस्ते": "जोहार",
            "बैठो": "दुबपे",
            "गिनो": "लेकापे",
            "लिखो": "ओलपे",
            "पढ़ो": "पाड़ावपे",
            "सुनो": "आयूमपे"
        }
        for hi, expected_mu in phrases.items():
            res = self.engine.translate(hi)
            self.assertEqual(res.status, "VERIFIED_EDUCATIONAL_LOOKUP", f"Failed for phrase {hi}")
            self.assertEqual(res.confidence, 1.0)
            self.assertEqual(res.translated_text, expected_mu)

    def test_normalization(self):
        """Verify punctuation, leading/trailing whitespace, and formatting variations normalize cleanly."""
        test_cases = [
            ("  पाँच  ", "पाँच"),
            ("पाँच!", "पाँच"),
            ("पाँच।", "पाँच"),
            ("  एक ? ", "एक"),
            ("चौदह ...", "चौदह")
        ]
        for noisy_input, clean_input in test_cases:
            res_noisy = self.engine.translate(noisy_input)
            res_clean = self.engine.translate(clean_input)
            self.assertEqual(res_noisy.status, "VERIFIED_EDUCATIONAL_LOOKUP")
            self.assertEqual(res_noisy.translated_text, res_clean.translated_text)

    def test_known_corpus_exact_match(self):
        """Verify sentence present in parallel corpus achieves CORPUS_RETRIEVAL_MATCH with high similarity."""
        query = "वे भी कमजोर पड़ रहे हैं"
        res = self.engine.translate(query)
        self.assertEqual(res.status, "CORPUS_RETRIEVAL_MATCH")
        self.assertGreaterEqual(res.confidence, 0.95)
        self.assertEqual(res.translated_text, "इनकु कमजोरोःतानाको")
        self.assertEqual(res.provenance, "KARYA_PARALLEL_CORPUS_RETRIEVAL")

    def test_known_corpus_similarity_match(self):
        """Verify partial sentence matching retrieves relevant corpus line above similarity threshold."""
        query = "सुधार के लिए आठ महीने"
        res = self.engine.translate(query)
        self.assertEqual(res.status, "CORPUS_RETRIEVAL_MATCH")
        self.assertGreaterEqual(res.confidence, self.engine.similarity_threshold)
        self.assertEqual(res.match_type, "TIER_2_SIMILARITY_CORPUS")
        self.assertIn("इरालिआ", res.translated_text)

    def test_unknown_input_low_confidence_fallback(self):
        """Verify out-of-vocabulary and low-similarity input strictly returns OUT_OF_VOCABULARY_UNVERIFIED."""
        unknown_queries = [
            "क्वांटम कंप्यूटिंग अल्गोरिदम",
            "एक्सटर्नल सैटेलाइट कम्यूनिकेशन प्रोटोकॉल",
            "xyz123abc random gibberish"
        ]
        for q in unknown_queries:
            res = self.engine.translate(q)
            self.assertEqual(res.status, "OUT_OF_VOCABULARY_UNVERIFIED", f"Failed to reject: {q}")
            self.assertIsNone(res.translated_text, "Must not hallucinate translation for unknown query")
            self.assertLess(res.confidence, self.engine.similarity_threshold)

    def test_empty_and_whitespace_input(self):
        """Verify empty and whitespace inputs return OUT_OF_VOCABULARY_UNVERIFIED without errors."""
        for empty_val in ["", "   ", "\t\n"]:
            res = self.engine.translate(empty_val)
            self.assertEqual(res.status, "OUT_OF_VOCABULARY_UNVERIFIED")
            self.assertEqual(res.confidence, 0.0)
            self.assertIsNone(res.translated_text)

            res_rev = self.engine.translate(empty_val, direction="unr-hi")
            self.assertEqual(res_rev.status, "OUT_OF_VOCABULARY_UNVERIFIED")
            self.assertEqual(res_rev.confidence, 0.0)
            self.assertIsNone(res_rev.translated_text)

    def test_deterministic_output(self):
        """Verify queries repeatedly return identical results."""
        q = "दस"
        res1 = self.engine.translate(q)
        res2 = self.engine.translate(q)
        self.assertEqual(res1, res2, "Engine outputs must be strictly deterministic")

    def test_reverse_numerals_lookup(self):
        """Verify Mundari number words translate back to Hindi in Tier 1."""
        test_pairs = [
            ("मिअद", "एक"),
            ("बारिया", "दो"),
            ("बारिआ", "दो"),   # Devanagari ya/ia variant
            ("अपिया", "तीन"),
            ("उपुनिया", "चार"),
            ("मोड़ेया", "पाँच"),
            ("मोनेया", "पाँच"),  # Attested variant
            ("गेलेया", "दस"),
            ("गेल", "दस"),       # Attested root
            ("हिसि", "बीस")
        ]
        for mun_word, expected_hi in test_pairs:
            res = self.engine.translate(mun_word, direction="unr-hi")
            self.assertEqual(res.status, "VERIFIED_EDUCATIONAL_LOOKUP", f"Failed reverse for: {mun_word}")
            self.assertEqual(res.confidence, 1.0)
            self.assertEqual(res.translated_text, expected_hi)

    def test_reverse_phrasebook_lookup(self):
        """Verify Mundari classroom commands map back to Hindi in Tier 1."""
        phrases = {
            "जोहार": "नमस्ते",
            "दुबपे": "बैठो",
            "लेकापे": "गिनो",
            "ओलपे": "लिखो",
            "पाड़ावपे": "पढ़ो",
            "आयूमपे": "सुनो"
        }
        for mun, expected_hi in phrases.items():
            res = self.engine.translate(mun, direction="unr-hi")
            self.assertEqual(res.status, "VERIFIED_EDUCATIONAL_LOOKUP", f"Failed reverse for {mun}")
            self.assertEqual(res.confidence, 1.0)
            self.assertEqual(res.translated_text, expected_hi)

    def test_reverse_corpus_match(self):
        """Verify Mundari sentence in parallel corpus retrieves Hindi equivalent in Tier 2."""
        mun_query = "इनकु कमजोरोःतानाको"
        res = self.engine.translate(mun_query, direction="unr-hi")
        self.assertEqual(res.status, "CORPUS_RETRIEVAL_MATCH")
        self.assertGreaterEqual(res.confidence, 0.95)
        self.assertEqual(res.translated_text, "वे भी कमजोर पड़ रहे हैं")
        self.assertEqual(res.provenance, "KARYA_PARALLEL_CORPUS_RETRIEVAL")

    def test_reverse_unknown_input_fallback(self):
        """Verify unknown Mundari / random input returns OUT_OF_VOCABULARY_UNVERIFIED."""
        unknown_queries = [
            "अल्गोरिदम डेटाबेस प्रोटोकॉल",
            "xyz random token unrecognized",
            "सुपरकंडक्टिंग चुंबक"
        ]
        for q in unknown_queries:
            res = self.engine.translate(q, direction="unr-hi")
            self.assertEqual(res.status, "OUT_OF_VOCABULARY_UNVERIFIED", f"Failed reverse fallback for: {q}")
            self.assertIsNone(res.translated_text)
            self.assertLess(res.confidence, self.engine.similarity_threshold)


if __name__ == "__main__":
    unittest.main()

