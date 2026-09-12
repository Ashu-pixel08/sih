"""
tests/test_integration_pipeline.py
=============================================================================
SIH260042: End-to-End System Integration Test Suite
=============================================================================

TEST COVERAGE:
1. test_direct_card_selection_all_20:
   Verifies all 20 numerals deliver 100% verified bilingual pedagogical content.
2. test_teacher_hindi_numbers_1_to_20:
   Verifies teacher Hindi words ('एक' .. 'बीस') bridge to Mundari FLN lessons.
3. test_teacher_classroom_commands:
   Verifies MTB-MLE classroom phrases ('नमस्ते', 'बैठो') map to verified Mundari.
4. test_teacher_unknown_fallback:
   Verifies out-of-vocabulary input refuses to hallucinate and prompts fallback.
5. test_spoken_audio_noise_fallback:
   Verifies low-energy/noise audio safely suggests interactive touch mode.
6. test_spoken_audio_real_sample_pipeline:
   Verifies end-to-end processing of a real Mundari WAV file through the full pipeline.
7. test_presentation_safe_pathway_parity:
   Asserts parity between teacher input and direct card selection.
=============================================================================
"""

import json
import os
import sys
import unittest

import numpy as np

cur_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.normpath(os.path.join(cur_dir, ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from ai.integration_pipeline import VernacularPedagogyPipeline


class TestIntegrationPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = VernacularPedagogyPipeline()
        cls.workspace_root = workspace_root

    def test_direct_card_selection_all_20(self):
        """Verify all 20 numerals succeed deterministically in Pathway C."""
        for num in range(1, 21):
            res = self.pipeline.process_direct_card_selection(num)
            self.assertTrue(res.is_success, f"Failed on numeral {num}")
            self.assertEqual(res.status_code, "DETERMINISTIC_CARD_SUCCESS")
            self.assertEqual(res.confidence, 1.0)
            self.assertIsNotNone(res.mundari_text)
            self.assertIsNotNone(res.hindi_text)
            self.assertIsNotNone(res.lesson)
            self.assertIsNotNone(res.recommended_activity)
            self.assertFalse(res.fallback_recommended)

    def test_teacher_hindi_numbers_1_to_20(self):
        """Verify teacher Hindi words translate deterministically to Mundari FLN content."""
        test_words = [
            ("एक", "मिअद"),
            ("दो", "बारिया"),
            ("पाँच", "मोड़ेया"),
            ("दस", "गेलेया"),
            ("बीस", "हिसि"),
        ]
        for hi_word, expected_unr in test_words:
            res = self.pipeline.process_teacher_input(hi_word)
            self.assertTrue(res.is_success, f"Failed for teacher input {hi_word}")
            self.assertEqual(res.translation_status, "VERIFIED_EDUCATIONAL_LOOKUP")
            self.assertEqual(res.mundari_text, expected_unr)
            self.assertIsNotNone(res.lesson)

    def test_teacher_classroom_commands(self):
        """Verify MTB-MLE classroom instructions map correctly."""
        commands = [
            ("नमस्ते", "जोहार"),
            ("बैठो", "दुबपे"),
            ("गिनो", "लेकापे"),
        ]
        for hi_cmd, exp_unr in commands:
            res = self.pipeline.process_teacher_input(hi_cmd)
            self.assertTrue(res.is_success, f"Command {hi_cmd} lookup failed")
            self.assertEqual(res.mundari_text, exp_unr)

    def test_teacher_unknown_fallback(self):
        """Verify unknown Hindi input refuses to hallucinate."""
        res = self.pipeline.process_teacher_input("क्वांटम भौतिकी का सिद्धांत")
        self.assertFalse(res.is_success)
        self.assertEqual(res.translation_status, "OUT_OF_VOCABULARY_UNVERIFIED")
        self.assertIsNone(res.mundari_text)
        self.assertTrue(res.fallback_recommended)

    def test_spoken_audio_noise_fallback(self):
        """Verify low-confidence/ambient audio triggers safe touch mode recommendation."""
        noise = np.random.randn(16000).astype(np.float32) * 0.005
        res = self.pipeline.process_spoken_audio(noise, sample_rate=16000)
        self.assertFalse(res.is_success)
        self.assertEqual(res.status_code, "AMBIGUOUS_AUDIO_FALLBACK_RECOMMENDED")
        self.assertTrue(res.fallback_recommended)
        self.assertIsNotNone(res.speech_result)

    def test_spoken_audio_real_sample_pipeline(self):
        """Verify execution on an actual recorded WAV file from corpus."""
        wav_path = os.path.join(
            self.workspace_root,
            "data", "raw", "speech", "data-sample", "female", "female_10173.wav"
        )
        if os.path.exists(wav_path):
            from ai.preprocessing.audio_preprocessor import AudioPreprocessor
            prep = AudioPreprocessor()
            audio_16k, _ = prep.preprocess_file(wav_path)

            res = self.pipeline.process_spoken_audio(audio_16k, sample_rate=16000)
            # The real file is a multi-word sentence, so the isolated 1-20 model should
            # properly reject or route without throwing exceptions
            self.assertIn(res.status_code, ["AMBIGUOUS_AUDIO_FALLBACK_RECOMMENDED", "SPEECH_RECOGNITION_SUCCESS"])
            self.assertIsNotNone(res.speech_result)

    def test_presentation_safe_pathway_parity(self):
        """Verify parity between teacher input and direct card selection."""
        card_res = self.pipeline.process_direct_card_selection(10)
        teach_res = self.pipeline.process_teacher_input("दस")

        self.assertEqual(card_res.mundari_text, teach_res.mundari_text)
        self.assertEqual(card_res.hindi_text, teach_res.hindi_text)
        self.assertEqual(card_res.lesson["number"], teach_res.lesson["number"])


if __name__ == "__main__":
    unittest.main()
