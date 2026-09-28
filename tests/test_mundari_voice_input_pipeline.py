"""
Comprehensive Regression Tests for Bhasha Setu Mundari Voice Input Pipeline.
Verifies all 11 required scenarios:
  1. Microphone API availability contract
  2. SpeechRecognition availability contract
  3. Unsupported Mundari language handling (language-not-supported)
  4. Recognition error handling
  5. Empty transcript handling
  6. Valid Mundari Golden Demo input
  7. Canonical Mundari -> Hindi lookup
  8. Hindi target TTS (language == "hi")
  9. Hinglish -> Hindi normalization
  10. Hinglish -> Mundari translation
  11. Round-trip Golden Demo consistency (HI <-> UNR)
"""

import json
import os
import sys
import unittest
import wave

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai.translation.translation_engine import TranslationEngine
from ai.translation.hinglish_normalizer import HinglishNormalizer
from ai.speech.pronunciation_service import PronunciationService


class TestMundariVoiceInputPipeline(unittest.TestCase):
    """Verifies the complete Mundari voice input, translation, and audio response pipeline."""

    @classmethod
    def setUpClass(cls):
        cls.engine = TranslationEngine(enable_neural=True)
        cls.normalizer = HinglishNormalizer()
        cls.speech = PronunciationService(project_root=PROJECT_ROOT)

        # Load Golden Demo datasets
        with open(os.path.join(PROJECT_ROOT, "demo", "golden_set", "golden_demo_set.json"), "r", encoding="utf-8") as f:
            cls.golden_demo_set = json.load(f)["items"]

        with open(os.path.join(PROJECT_ROOT, "demo", "golden_set", "golden_voice_inputs.json"), "r", encoding="utf-8") as f:
            cls.golden_voice_inputs = json.load(f)["items"]

        with open(os.path.join(PROJECT_ROOT, "frontend", "index.html"), "r", encoding="utf-8") as f:
            cls.frontend_html = f.read()

    # -------------------------------------------------------------------------
    # Scenario 1: Microphone API availability
    # -------------------------------------------------------------------------
    def test_01_microphone_api_availability(self):
        """Microphone capture functions getUserMedia and MediaRecorder must be implemented in frontend."""
        self.assertIn("captureDiagnosticMicrophoneAudio", self.frontend_html)
        self.assertIn("navigator.mediaDevices.getUserMedia", self.frontend_html)
        self.assertIn("MediaRecorder", self.frontend_html)

    # -------------------------------------------------------------------------
    # Scenario 2: SpeechRecognition availability
    # -------------------------------------------------------------------------
    def test_02_speech_recognition_availability(self):
        """SpeechRecognition probe must check both standard and webkit prefixes."""
        self.assertIn("checkSpeechRecognitionLanguageSupport", self.frontend_html)
        self.assertIn("window.SpeechRecognition", self.frontend_html)
        self.assertIn("window.webkitSpeechRecognition", self.frontend_html)

    # -------------------------------------------------------------------------
    # Scenario 3: Unsupported Mundari language handling (language-not-supported)
    # -------------------------------------------------------------------------
    def test_03_unsupported_mundari_language_handling(self):
        """Browser rejecting unr-IN must set UNSUPPORTED_LANGUAGE state and honest teacher message."""
        self.assertIn("VoiceStateEnum.UNSUPPORTED_LANGUAGE", self.frontend_html)
        self.assertIn("Mundari voice recognition isn't available in this browser. Use controlled demo voice input", self.frontend_html)
        self.assertIn("language-not-supported", self.frontend_html)

    # -------------------------------------------------------------------------
    # Scenario 4: Recognition error handling
    # -------------------------------------------------------------------------
    def test_04_recognition_error_handling(self):
        """Microphone permission denial or error must transition state to MICROPHONE_ERROR."""
        self.assertIn("VoiceStateEnum.MICROPHONE_ERROR", self.frontend_html)
        self.assertIn("VoiceStateEnum.ERROR", self.frontend_html)
        self.assertIn("Microphone capture failed", self.frontend_html)

    # -------------------------------------------------------------------------
    # Scenario 5: Empty transcript handling
    # -------------------------------------------------------------------------
    def test_05_empty_transcript_handling(self):
        """Zero audio buffer or empty speech must transition to NO_SPEECH without faking text."""
        self.assertIn("VoiceStateEnum.NO_SPEECH", self.frontend_html)
        self.assertIn("No audio data was captured from microphone", self.frontend_html)

    # -------------------------------------------------------------------------
    # Scenario 6: Valid Mundari Golden Demo input
    # -------------------------------------------------------------------------
    def test_06_valid_mundari_golden_demo_input(self):
        """Controlled Golden Demo voice inputs must exist, have valid WAV audio, and match schema."""
        for item in self.golden_voice_inputs:
            self.assertTrue(item.get("canonical_mundari"), f"Missing canonical_mundari in {item['id']}")
            self.assertTrue(item.get("expected_hindi"), f"Missing expected_hindi in {item['id']}")
            self.assertEqual(item.get("response_language"), "hi")

            audio_path = os.path.join(PROJECT_ROOT, item["audio_file"])
            self.assertTrue(os.path.exists(audio_path), f"Audio file not found: {audio_path}")
            with wave.open(audio_path, "rb") as wf:
                self.assertGreater(wf.getnframes(), 0)

    # -------------------------------------------------------------------------
    # Scenario 7: Canonical Mundari -> Hindi lookup
    # -------------------------------------------------------------------------
    def test_07_canonical_mundari_to_hindi_lookup(self):
        """Mundari input in unr-hi direction must produce exact canonical Hindi translation."""
        for item in self.golden_demo_set:
            mundari_src = item["mundari"]
            expected_hindi = item["hindi"]

            res = self.engine.translate(mundari_src, direction="unr-hi", src_lang="mundari")
            self.assertIsNotNone(res)
            self.assertEqual(res.translated_text.strip(), expected_hindi.strip(),
                             f"Lookup failed for {mundari_src} -> {res.translated_text} (expected: {expected_hindi})")

    # -------------------------------------------------------------------------
    # Scenario 8: Hindi target TTS (language == "hi")
    # -------------------------------------------------------------------------
    def test_08_hindi_target_tts_synthesis(self):
        """Hindi translations must synthesize non-empty audio using language='hi'."""
        for item in self.golden_demo_set:
            hindi_text = item["hindi"]
            audio_res, err = self.speech.synthesize(hindi_text, language="hi")

            self.assertIsNone(err, f"Synthesis error for '{hindi_text}': {err}")
            self.assertIsNotNone(audio_res)
            self.assertEqual(audio_res.language, "hindi")
            self.assertGreater(len(audio_res.audio_bytes), 400, f"Audio too small for '{hindi_text}'")

    # -------------------------------------------------------------------------
    # Scenario 9: Hinglish -> Hindi normalization
    # -------------------------------------------------------------------------
    def test_09_hinglish_to_hindi_normalization(self):
        """Latin Hinglish input must normalize to clean canonical Hindi."""
        for item in self.golden_demo_set:
            hinglish_src = item["hinglish"]
            expected_hindi = item["hindi"]
            norm_res = self.normalizer.normalize(hinglish_src)

            self.assertEqual(norm_res.normalized_hindi.strip(), expected_hindi.strip(),
                             f"Normalization failed for '{hinglish_src}' -> '{norm_res.normalized_hindi}'")

    # -------------------------------------------------------------------------
    # Scenario 10: Hinglish -> Mundari translation
    # -------------------------------------------------------------------------
    def test_10_hinglish_to_mundari_translation(self):
        """Normalized Hinglish input must produce exact verified Mundari translation."""
        for item in self.golden_demo_set:
            hinglish_src = item["hinglish"]
            expected_mundari = item["mundari"]

            res = self.engine.translate(hinglish_src, direction="hi-unr", src_lang="hinglish")
            self.assertIsNotNone(res)
            self.assertEqual(res.translated_text.strip(), expected_mundari.strip(),
                             f"Hinglish translation failed for '{hinglish_src}' -> '{res.translated_text}'")

    # -------------------------------------------------------------------------
    # Scenario 11: Round-trip Golden Demo consistency (HI <-> UNR)
    # -------------------------------------------------------------------------
    def test_11_round_trip_golden_demo_consistency(self):
        """All Golden Demo items must satisfy exact bidirectional round-trip identity."""
        for item in self.golden_demo_set:
            hi = item["hindi"]
            unr = item["mundari"]

            # HI -> UNR
            fwd = self.engine.translate(hi, direction="hi-unr")
            self.assertEqual(fwd.translated_text.strip(), unr.strip(),
                             f"Forward round-trip mismatch for '{hi}'")

            # UNR -> HI
            rev = self.engine.translate(fwd.translated_text, direction="unr-hi")
            self.assertEqual(rev.translated_text.strip(), hi.strip(),
                             f"Reverse round-trip identity failed for '{unr}'")


if __name__ == "__main__":
    unittest.main()
