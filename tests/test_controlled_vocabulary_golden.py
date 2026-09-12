"""
tests/test_controlled_vocabulary_golden.py
=============================================================================
SIH260042: AI-Powered Vernacular Pedagogy & Real-Time Translation
Phase 9 Golden Test Set: Controlled-Vocabulary Speech Pipeline Hardening
=============================================================================

PURPOSE & METHODOLOGICAL POLICY:
- Validates the deterministic end-to-end pipeline:
    Stored WAV Fixture
    -> Preprocessing (16 kHz, Hann, 512-FFT, 64-Mel, Log-Mel [101, 64])
    -> Edge TFLite / Speech Classifier (21 classes)
    -> Canonical Educational Registry Mapping
    -> Hybrid Retrieval Translation
    -> Audio Playback Resolution
- Evaluates regression behavior using stored WAV audio assets.
- POLICY NOTICE: In accordance with project anti-hallucination governance,
  all audio test fixtures are strictly labeled as SYNTHETIC/PROTOTYPE REGRESSION
  FIXTURES. They validate software execution and contract stability, NOT
  native-speaker field accuracy.
- ZERO GENERAL ASR CLAIM: Edge classifier is strictly limited to the controlled
  21-class demo vocabulary (1–20 numerals + background).
=============================================================================
"""

import json
import os
import sys
import unittest
import wave
from typing import Tuple
import numpy as np

cur_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.normpath(os.path.join(cur_dir, ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from ai.integration_pipeline import VernacularPedagogyPipeline
from ai.preprocessing.audio_preprocessor import AudioPreprocessor
from ai.speech.speech_recognition_engine import (
    CAPABILITY_CONTROLLED_VOCABULARY,
    CAPABILITY_GENERAL_SPEECH_RECOGNITION,
    CAPABILITY_TEXT_TRANSLATION,
    SpeechRecognitionManager,
    VocabularySpeechRecognizer,
)


class TestControlledVocabularyGolden(unittest.TestCase):
    """Deterministic golden regression test suite for controlled-vocabulary speech pipeline."""

    @classmethod
    def setUpClass(cls):
        cls.workspace_root = workspace_root
        cls.registry_path = os.path.join(cls.workspace_root, "content", "content_registry.json")
        cls.tflite_path = os.path.join(cls.workspace_root, "models", "edge", "speech_classifier_float32.tflite")
        cls.audio_dir = os.path.join(cls.workspace_root, "content", "audio", "prototype_tts", "numbers")
        cls.pipeline = VernacularPedagogyPipeline()
        cls.preprocessor = AudioPreprocessor()
        cls.vocab_recognizer = VocabularySpeechRecognizer(use_tflite=os.path.exists(cls.tflite_path))
        cls.speech_manager = SpeechRecognitionManager()

        with open(cls.registry_path, "r", encoding="utf-8") as f:
            cls.registry_data = json.load(f)

    def _load_wav_pcm16(self, wav_path: str) -> Tuple[np.ndarray, int]:
        """Loads a mono 16-bit PCM WAV into float32 array [-1.0, 1.0]."""
        with wave.open(wav_path, "rb") as wf:
            sample_rate = wf.getframerate()
            num_channels = wf.getnchannels()
            num_frames = wf.getnframes()
            pcm_bytes = wf.readframes(num_frames)
            audio_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
            if num_channels > 1:
                audio_int16 = audio_int16[::num_channels]
            audio_float = audio_int16.astype(np.float32) / 32768.0
            return audio_float, sample_rate

    def test_capability_boundary_constants(self):
        """Verify explicit architectural separation of the three system capabilities."""
        self.assertIn("GENERAL_SPEECH_RECOGNITION", CAPABILITY_GENERAL_SPEECH_RECOGNITION)
        self.assertIn("Requires ~50-100h corpus", CAPABILITY_GENERAL_SPEECH_RECOGNITION)
        self.assertIn("CONTROLLED_VOCABULARY_SPEECH_RECOGNITION", CAPABILITY_CONTROLLED_VOCABULARY)
        self.assertIn("21-class", CAPABILITY_CONTROLLED_VOCABULARY)
        self.assertIn("TEXT_TRANSLATION", CAPABILITY_TEXT_TRANSLATION)
        self.assertIn("Deterministic retrieval", CAPABILITY_TEXT_TRANSLATION)

    def test_stored_wav_audio_fixtures_exist_and_valid(self):
        """Verify all 20 canonical number WAV assets physically exist and are valid 16kHz mono WAVs."""
        self.assertTrue(os.path.isdir(self.audio_dir), f"Audio directory missing: {self.audio_dir}")
        for i in range(1, 21):
            wav_file = os.path.join(self.audio_dir, f"num_{i:02d}.wav")
            self.assertTrue(os.path.isfile(wav_file), f"Canonical WAV fixture missing: {wav_file}")
            self.assertGreater(os.path.getsize(wav_file), 44, f"WAV fixture too small: {wav_file}")

            audio_float, sr = self._load_wav_pcm16(wav_file)
            self.assertEqual(sr, 16000, f"Sample rate must be 16kHz, got {sr} for num_{i:02d}")
            self.assertGreater(len(audio_float), 4000, f"Audio fixture unexpectedly short for num_{i:02d}")

    def test_stored_wav_end_to_end_pipeline(self):
        """
        Deterministic End-to-End Test:
        Stored WAV -> Preprocessing -> TFLite -> Registry -> Translation -> Audio Resolution
        """
        test_numbers = [1, 5, 10, 15, 20]
        for num in test_numbers:
            wav_file = os.path.join(self.audio_dir, f"num_{num:02d}.wav")
            audio_float, sr = self._load_wav_pcm16(wav_file)

            # Step 1: Preprocessing Log-Mel Spectrogram extraction [101, 64]
            _, log_mel = self.preprocessor.preprocess_signal(audio_float, sr)
            self.assertEqual(log_mel.shape, (101, 64), f"Log-mel shape mismatch for num_{num:02d}")

            # Step 2: Edge Vocabulary Recognizer Inference
            spec_4d = self.preprocessor.format_for_model(log_mel)
            speech_result = self.vocab_recognizer.recognize_spectrogram(spec_4d)

            self.assertIsNotNone(speech_result)
            self.assertIn(speech_result.decision, ("ACCEPTED", "REJECTED_LOW_CONFIDENCE", "REJECTED_BACKGROUND"))
            self.assertGreaterEqual(speech_result.confidence, 0.0)
            self.assertLessEqual(speech_result.confidence, 1.0)
            self.assertGreaterEqual(speech_result.second_best_confidence, 0.0)
            self.assertGreaterEqual(speech_result.margin, 0.0)

            # Step 3: Canonical Registry Lookup & Audio Resolution
            item = next(it for it in self.registry_data["items"] if it["number"] == num)
            audio_path, audio_id, audio_status = self.pipeline._resolve_audio_asset(
                content_id=item["label_id"],
                hindi_text=item["hindi_text"],
                number=num
            )
            self.assertIsNotNone(audio_path, f"Audio asset resolution failed for numeral {num}")
            self.assertTrue(os.path.isfile(audio_path))
            self.assertEqual(audio_status, "SYNTHETIC_PROTOTYPE")
            self.assertEqual(audio_id, item["label_id"])

    def test_silence_rejection_and_rms_check(self):
        """Verifies pure silence audio is rejected with silence status and low RMS."""
        silent_audio = np.zeros(16000, dtype=np.float32)
        speech_res = self.speech_manager.process_raw_audio(silent_audio, sample_rate=16000)

        self.assertEqual(speech_res.rms_energy, 0.0)
        self.assertFalse(speech_res.is_confident)
        self.assertIn(speech_res.status, ("BACKGROUND_NOISE", "SILENCE", "LOW_CONFIDENCE_REJECTED"))
        self.assertIn(speech_res.decision, ("REJECTED_BACKGROUND", "REJECTED_LOW_CONFIDENCE", "REJECTED"))

    def test_noise_rejection(self):
        """Verifies high ambient white noise is rejected by the confidence/margin threshold."""
        rng = np.random.RandomState(1337)
        noise_audio = rng.randn(16000).astype(np.float32) * 0.1
        speech_res = self.speech_manager.process_raw_audio(noise_audio, sample_rate=16000)

        self.assertFalse(speech_res.is_confident, "Noise audio should not be marked confident")
        self.assertIn(speech_res.decision, ("REJECTED_BACKGROUND", "REJECTED_LOW_CONFIDENCE", "REJECTED"))

    def test_unsupported_speech_safe_fallback(self):
        """
        Verifies unsupported/OOV speech input yields:
        'This phrase is not available in the verified classroom vocabulary.'
        with ZERO hallucinated Mundari text.
        """
        res = self.pipeline.process_teacher_input("कल सभी बच्चे समय पर स्कूल आएंगे")
        self.assertFalse(res.is_success)
        self.assertEqual(res.translation_status, "OUT_OF_VOCABULARY_UNVERIFIED")
        self.assertIsNone(res.mundari_text, "System must refuse to hallucinate Mundari text")
        self.assertEqual(res.audio_status, "MISSING")
        self.assertTrue(res.fallback_recommended)

    def test_diagnostic_info_structure_in_pipeline(self):
        """Verifies PedagogySessionResponse includes complete diagnostic instrumentation."""
        # Using a valid numeral input
        res = self.pipeline.process_direct_card_selection(5)
        self.assertTrue(res.is_success)
        self.assertEqual(res.audio_status, "SYNTHETIC_PROTOTYPE")
        self.assertIn("total_end_to_end_ms", res.latency_breakdown)

        # Voice interaction diagnostics check
        ref_audio = self.pipeline.hindi_asr.synthesize_reference_signal("पांच")
        voice_res = self.pipeline.process_teacher_speech(ref_audio, sample_rate=16000)
        self.assertTrue(voice_res.is_success)
        self.assertIsNotNone(voice_res.diagnostic_info)
        diag = voice_res.diagnostic_info
        self.assertIn("audio_duration_sec", diag)
        self.assertIn("rms", diag)
        self.assertIn("predicted_class", diag)
        self.assertIn("confidence", diag)
        self.assertIn("second_best_confidence", diag)
        self.assertIn("margin", diag)
        self.assertIn("final_decision", diag)
        self.assertIn("translation_status", diag)
        self.assertIn("audio_provenance", diag)
        self.assertEqual(diag["audio_provenance"], "SYNTHETIC_PROTOTYPE")


if __name__ == "__main__":
    unittest.main()
