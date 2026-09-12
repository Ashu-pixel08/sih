"""
tests/test_end_to_end_voice_pipeline.py
=============================================================================
SIH260042: AI-Powered Vernacular Pedagogy & Real-Time Translation
End-to-End Test Suite: Teacher Voice -> Hindi ASR -> Translation -> FLN Output
=============================================================================

TEST COVERAGE:
1. Scenario 1: Teacher says a known classroom command ("बैठो").
2. Scenario 2: Teacher says a known numeracy instruction ("गिनो").
3. Scenario 3: Teacher says a known 1–20 number ("एक").
4. Scenario 4: Teacher says an unsupported/out-of-vocabulary sentence.
5. Scenario 5: Audio is silent (low energy below -45 dBFS).
6. Scenario 6: Audio is noisy (poor SNR below 8.0 dB).
7. Scenario 7: Hindi text has a low-confidence translation (refusal to hallucinate).
8. Scenario 8: Mundari audio asset exists (prototype WAV playback).
9. Scenario 9: Mundari audio asset is missing (graceful visual/text fallback).
10. Latency & Status Profiling: Desktop measured vs. Android estimated metrics.
=============================================================================
"""

import os
import sys
import unittest
import numpy as np

cur_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.normpath(os.path.join(cur_dir, ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from ai.integration_pipeline import VernacularPedagogyPipeline, PedagogySessionResponse


class TestEndToEndVoicePipeline(unittest.TestCase):
    """Verifies end-to-end teacher voice interaction pathway across all 9 scenarios."""

    @classmethod
    def setUpClass(cls):
        cls.pipeline = VernacularPedagogyPipeline()
        cls.recognizer = cls.pipeline.hindi_asr
        cls.sample_rate = 16000

    def test_scenario_1_known_classroom_command(self):
        """Scenario 1: Teacher says a known classroom command ('बैठो')."""
        audio = self.recognizer.synthesize_reference_signal("बैठो")
        res = self.pipeline.process_teacher_speech(audio, sample_rate=self.sample_rate)

        # 1. Input
        self.assertEqual(res.input_mode, "TEACHER_HINDI_VOICE")
        # 2. Recognized Hindi
        self.assertEqual(res.hindi_text, "बैठो")
        # 3. Translation Status
        self.assertEqual(res.translation_status, "VERIFIED_EDUCATIONAL_LOOKUP")
        # 4. Mundari Output
        self.assertEqual(res.mundari_text, "दुबपे")
        # 5. Content ID
        self.assertEqual(res.content_id, "PHR_MGMT_01")
        # 6. Audio ID
        self.assertEqual(res.audio_id, "PHR_MGMT_01")
        # 7. Fallback State
        self.assertFalse(res.fallback_recommended)
        self.assertTrue(res.is_success)
        self.assertEqual(res.status_code, "TEACHER_VOICE_COMMAND_SUCCESS")
        # Audio status
        self.assertEqual(res.audio_status, "SYNTHETIC_PROTOTYPE")
        self.assertTrue(os.path.exists(res.audio_asset_path))

    def test_scenario_2_known_numeracy_instruction(self):
        """Scenario 2: Teacher says a known numeracy instruction ('गिनो')."""
        audio = self.recognizer.synthesize_reference_signal("गिनो")
        res = self.pipeline.process_teacher_speech(audio, sample_rate=self.sample_rate)

        # 1. Input
        self.assertEqual(res.input_mode, "TEACHER_HINDI_VOICE")
        # 2. Recognized Hindi
        self.assertEqual(res.hindi_text, "गिनो")
        # 3. Translation Status
        self.assertEqual(res.translation_status, "VERIFIED_EDUCATIONAL_LOOKUP")
        # 4. Mundari Output
        self.assertEqual(res.mundari_text, "लेकापे")
        # 5. Content ID
        self.assertEqual(res.content_id, "PHR_NUM_01")
        # 6. Audio ID
        self.assertEqual(res.audio_id, "PHR_NUM_01")
        # 7. Fallback State
        self.assertFalse(res.fallback_recommended)
        self.assertTrue(res.is_success)
        self.assertEqual(res.audio_status, "SYNTHETIC_PROTOTYPE")
        self.assertTrue(os.path.exists(res.audio_asset_path))

    def test_scenario_3_known_1_to_20_number(self):
        """Scenario 3: Teacher says a known 1–20 number ('एक')."""
        audio = self.recognizer.synthesize_reference_signal("एक")
        res = self.pipeline.process_teacher_speech(audio, sample_rate=self.sample_rate)

        # 1. Input
        self.assertEqual(res.input_mode, "TEACHER_HINDI_VOICE")
        # 2. Recognized Hindi
        self.assertEqual(res.hindi_text, "एक")
        # 3. Translation Status
        self.assertEqual(res.translation_status, "VERIFIED_EDUCATIONAL_LOOKUP")
        # 4. Mundari Output
        self.assertEqual(res.mundari_text, "मिअद")
        # 5. Content ID
        self.assertEqual(res.content_id, "num_01")
        # 6. Audio ID
        self.assertEqual(res.audio_id, "num_01")
        # 7. Fallback State
        self.assertFalse(res.fallback_recommended)
        self.assertTrue(res.is_success)
        self.assertEqual(res.status_code, "TEACHER_VOICE_NUMERACY_SUCCESS")
        # Verify educational assets attached
        self.assertIsNotNone(res.lesson)
        self.assertIsNotNone(res.recommended_activity)
        self.assertIsNotNone(res.worksheet_ref)
        self.assertTrue(os.path.exists(res.flashcard_svg_path))

    def test_scenario_4_unsupported_sentence(self):
        """Scenario 4: Teacher says an unsupported/out-of-lexicon vocalization."""
        # Multi-frequency audio that does not correlate with any constrained template
        t = np.linspace(0, 0.8, int(0.8 * self.sample_rate), endpoint=False)
        unsupported_audio = (0.2 * np.sin(2 * np.pi * 50.0 * t) + 0.2 * np.sin(2 * np.pi * 7500.0 * t)).astype(np.float32)

        res = self.pipeline.process_teacher_speech(unsupported_audio, sample_rate=self.sample_rate)

        # 1. Input
        self.assertEqual(res.input_mode, "TEACHER_HINDI_VOICE")
        # 2. Recognized Hindi
        self.assertIsNone(res.hindi_text)
        # 3. Translation Status
        self.assertEqual(res.translation_status, "UNVERIFIED_AMBIGUOUS_AUDIO")
        # 4. Mundari Output
        self.assertIsNone(res.mundari_text)
        # 5. Content ID
        self.assertIsNone(res.content_id)
        # 6. Audio ID
        self.assertIsNone(res.audio_id)
        # 7. Fallback State
        self.assertTrue(res.fallback_recommended)
        self.assertFalse(res.is_success)
        self.assertEqual(res.status_code, "AMBIGUOUS_AUDIO_FALLBACK_RECOMMENDED")

    def test_scenario_5_audio_is_silent(self):
        """Scenario 5: Audio input is completely silent (< -45 dBFS)."""
        silence = np.zeros(int(0.8 * self.sample_rate), dtype=np.float32)
        res = self.pipeline.process_teacher_speech(silence, sample_rate=self.sample_rate)

        # 1. Input
        self.assertEqual(res.input_mode, "TEACHER_HINDI_VOICE")
        # 2. Recognized Hindi
        self.assertIsNone(res.hindi_text)
        # 3. Translation Status
        self.assertEqual(res.translation_status, "UNVERIFIED_AMBIGUOUS_AUDIO")
        # 4. Mundari Output
        self.assertIsNone(res.mundari_text)
        # 5. Content ID
        self.assertIsNone(res.content_id)
        # 6. Audio ID
        self.assertIsNone(res.audio_id)
        # 7. Fallback State
        self.assertTrue(res.fallback_recommended)
        self.assertFalse(res.is_success)
        self.assertEqual(res.status_code, "SILENCE_DETECTED_FALLBACK")

    def test_scenario_6_audio_is_noisy(self):
        """Scenario 6: Audio input is low-SNR background noise (< 8 dB SNR)."""
        rng = np.random.RandomState(42)
        noise = rng.normal(0, 0.004, int(0.8 * self.sample_rate)).astype(np.float32)
        res = self.pipeline.process_teacher_speech(noise, sample_rate=self.sample_rate)

        # 1. Input
        self.assertEqual(res.input_mode, "TEACHER_HINDI_VOICE")
        # 2. Recognized Hindi
        self.assertIsNone(res.hindi_text)
        # 3. Translation Status
        self.assertEqual(res.translation_status, "UNVERIFIED_AMBIGUOUS_AUDIO")
        # 4. Mundari Output
        self.assertIsNone(res.mundari_text)
        # 5. Content ID
        self.assertIsNone(res.content_id)
        # 6. Audio ID
        self.assertIsNone(res.audio_id)
        # 7. Fallback State
        self.assertTrue(res.fallback_recommended)
        self.assertFalse(res.is_success)
        self.assertIn(res.status_code, ["HIGH_NOISE_FALLBACK", "SILENCE_DETECTED_FALLBACK"])

    def test_scenario_7_low_confidence_translation_refusal(self):
        """Scenario 7: Hindi input has low-confidence translation -> refuses to hallucinate."""
        untranslatable_hindi = "नाभिकीय भौतिकी का परिष्कृत प्रयोग"
        res = self.pipeline.process_teacher_input(untranslatable_hindi)

        # 1. Input
        self.assertEqual(res.input_mode, "TEACHER_HINDI_TEXT")
        # 2. Recognized Hindi
        self.assertEqual(res.hindi_text, untranslatable_hindi)
        # 3. Translation Status
        self.assertEqual(res.translation_status, "OUT_OF_VOCABULARY_UNVERIFIED")
        # 4. Mundari Output (Must be None; strict zero hallucination)
        self.assertIsNone(res.mundari_text)
        # 5. Content ID
        self.assertIsNone(res.content_id)
        # 6. Audio ID
        self.assertIsNone(res.audio_id)
        # 7. Fallback State
        self.assertTrue(res.fallback_recommended)
        self.assertFalse(res.is_success)
        self.assertEqual(res.status_code, "OUT_OF_VOCABULARY_UNVERIFIED")

    def test_scenario_8_mundari_audio_asset_exists(self):
        """Scenario 8: Mundari audio asset exists on disk (verified prototype WAV)."""
        res = self.pipeline.process_direct_card_selection(5)

        self.assertTrue(res.is_success)
        self.assertEqual(res.content_id, "num_05")
        self.assertEqual(res.audio_id, "num_05")
        self.assertIsNotNone(res.audio_asset_path)
        self.assertTrue(os.path.isfile(res.audio_asset_path))
        self.assertGreater(os.path.getsize(res.audio_asset_path), 44)
        # Strict synthetic prototype designation
        self.assertEqual(res.audio_status, "SYNTHETIC_PROTOTYPE")
        self.assertFalse(res.fallback_recommended)

    def test_scenario_9_mundari_audio_asset_missing(self):
        """Scenario 9: Mundari audio asset is missing -> graceful visual/text fallback."""
        # Test 9A: Command with missing audio asset ('पढ़ो' / Read)
        res_no_audio = self.pipeline.process_teacher_input("पढ़ो")
        self.assertTrue(res_no_audio.is_success)
        self.assertEqual(res_no_audio.hindi_text, "पढ़ो")
        self.assertEqual(res_no_audio.translation_status, "VERIFIED_EDUCATIONAL_LOOKUP")
        self.assertEqual(res_no_audio.mundari_text, "पाड़ावपे")
        self.assertEqual(res_no_audio.content_id, "cmd_padho")
        self.assertIsNone(res_no_audio.audio_id)
        self.assertIsNone(res_no_audio.audio_asset_path)
        self.assertEqual(res_no_audio.audio_status, "MISSING")
        # Crucial: Pedagogical delivery succeeds via text/activity, never crashes!
        self.assertFalse(res_no_audio.fallback_recommended)

        # Test 9B: Voice input with missing audio asset ('पढ़ो')
        audio_padho = self.recognizer.synthesize_reference_signal("पढ़ो")
        res_voice_no_audio = self.pipeline.process_teacher_speech(audio_padho, sample_rate=self.sample_rate)
        self.assertTrue(res_voice_no_audio.is_success)
        self.assertEqual(res_voice_no_audio.hindi_text, "पढ़ो")
        self.assertEqual(res_voice_no_audio.mundari_text, "पाड़ावपे")
        self.assertEqual(res_voice_no_audio.audio_status, "MISSING")
        self.assertIsNone(res_voice_no_audio.audio_asset_path)
        self.assertFalse(res_voice_no_audio.fallback_recommended)

    def test_latency_breakdown_and_status_separation(self):
        """Verifies desktop measured timings vs Android estimated metrics separation."""
        audio = self.recognizer.synthesize_reference_signal("बैठो")
        res = self.pipeline.process_teacher_speech(audio, sample_rate=self.sample_rate)

        # Check latency breakdown fields
        breakdown = res.latency_breakdown
        self.assertIsNotNone(breakdown)
        self.assertIn("audio_preprocessing_ms", breakdown)
        self.assertIn("hindi_recognition_ms", breakdown)
        self.assertIn("translation_ms", breakdown)
        self.assertIn("fln_lookup_ms", breakdown)
        self.assertIn("audio_lookup_ms", breakdown)
        self.assertIn("total_end_to_end_ms", breakdown)

        # Check Hardware Profile separation
        profile = res.hardware_profile
        self.assertIsNotNone(profile)
        self.assertIn("DESKTOP_MEASURED", profile)
        self.assertIn("ANDROID_ESTIMATED", profile)
        self.assertIn("ANDROID_MEASURED", profile)

        # Android measured is honestly PENDING
        self.assertEqual(profile["ANDROID_MEASURED"], "PENDING_PHYSICAL_DEVICE_DEPLOYMENT")
        # Desktop measured total latency is reasonable
        self.assertGreater(profile["DESKTOP_MEASURED"]["total_end_to_end_ms"], 0.0)
        self.assertLess(profile["DESKTOP_MEASURED"]["total_end_to_end_ms"], 500.0)


if __name__ == "__main__":
    unittest.main()
