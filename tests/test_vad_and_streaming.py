"""
tests/test_vad_and_streaming.py
=============================================================================
SIH260042: Automated Test Suite for Streaming VAD & Classroom Phrasebook
=============================================================================

TEST CODES & VALIDATION:
1. test_vad_config_and_initial_state:
   Verifies default VAD parameters (16 kHz, 20ms chunks, IDLE state).
2. test_vad_silence_and_noise_floor_adaptation:
   Verifies low-energy background audio adapts noise floor and keeps state IDLE.
3. test_vad_transient_spike_rejection:
   Verifies short transient clicks (< 120ms) are rejected without triggering false speech.
4. test_vad_speech_endpointing_and_extraction:
   Verifies speech burst triggers IN_SPEECH, hangover, and outputs a 16,000-sample window.
5. test_vad_continuous_audio_detection:
   Verifies continuous multi-second audio with multiple speech bursts yields distinct utterances.
6. test_speech_recognition_manager_streaming_chunk:
   Verifies SpeechRecognitionManager streaming chunk endpointing and speech recognition pipeline.
7. test_classroom_phrasebook_full_coverage:
   Verifies all 16 classroom interaction phrases match Tier 1 deterministic lookup with 1.0 confidence.
8. test_pipeline_streaming_integration:
   Verifies VernacularPedagogyPipeline process_streaming_chunk and process_continuous_stream.
=============================================================================
"""

import json
import math
import os
import sys
import unittest

import numpy as np

cur_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.normpath(os.path.join(cur_dir, ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from ai.integration_pipeline import VernacularPedagogyPipeline
from ai.preprocessing.vad_stream_processor import (
    StreamingVADProcessor,
    VADConfig,
    VADState,
)
from ai.speech.speech_recognition_engine import SpeechRecognitionManager
from ai.translation.translation_engine import TranslationEngine


class TestVADAndStreaming(unittest.TestCase):
    """Test suite validating streaming VAD, speech endpointing, and classroom phrasebook."""

    @classmethod
    def setUpClass(cls):
        cls.workspace_root = workspace_root
        cls.phrasebook_path = os.path.join(
            workspace_root, "content", "translations", "classroom_phrasebook.json"
        )
        cls.translation_engine = TranslationEngine()
        cls.speech_manager = SpeechRecognitionManager()
        cls.pipeline = VernacularPedagogyPipeline()

    def test_vad_config_and_initial_state(self):
        """Verifies default VAD configuration parameters and starting state."""
        vad = StreamingVADProcessor()
        self.assertEqual(vad.state, VADState.IDLE)
        self.assertEqual(vad.config.sample_rate, 16000)
        self.assertEqual(vad.config.chunk_size_samples, 320)
        self.assertEqual(vad.config.target_window_samples, 16000)
        self.assertLess(vad.noise_floor_db, vad.threshold_db)

    def test_vad_silence_and_noise_floor_adaptation(self):
        """Verifies low-energy ambient noise adapts noise floor and emits no utterances."""
        vad = StreamingVADProcessor()
        initial_floor = vad.noise_floor_db

        # Generate 50 chunks of low-level white noise (-60 dBFS approx)
        np.random.seed(42)
        quiet_chunk = np.random.normal(0, 0.001, size=320).astype(np.float32)

        for _ in range(50):
            res = vad.process_chunk(quiet_chunk)
            self.assertIsNone(res, "VAD should not trigger an utterance on pure silence")
            self.assertEqual(vad.state, VADState.IDLE)

        # Noise floor should have adapted
        self.assertNotEqual(vad.noise_floor_db, initial_floor)

    def test_vad_transient_spike_rejection(self):
        """Verifies short transient clicks (< 120ms) are rejected without triggering false speech."""
        vad = StreamingVADProcessor()
        quiet_chunk = np.zeros(320, dtype=np.float32)
        loud_chunk = (np.sin(2 * np.pi * 300 * np.arange(320) / 16000) * 0.8).astype(np.float32)

        # 1. Warm up with quiet chunks
        for _ in range(10):
            vad.process_chunk(quiet_chunk)
        self.assertEqual(vad.state, VADState.IDLE)

        # 2. Single loud 20ms click
        res = vad.process_chunk(loud_chunk)
        self.assertIsNone(res)
        self.assertEqual(vad.state, VADState.ONSET_CANDIDATE)

        # 3. Followed immediately by silence (click is < 120 ms)
        res = vad.process_chunk(quiet_chunk)
        self.assertIsNone(res)
        self.assertEqual(vad.state, VADState.IDLE, "Transient click should be rejected and reset to IDLE")

    def test_vad_speech_endpointing_and_extraction(self):
        """Verifies speech burst triggers IN_SPEECH, hangover, and outputs a 16,000-sample window."""
        vad = StreamingVADProcessor()
        quiet_chunk = np.zeros(320, dtype=np.float32)
        # 400 Hz tone at 0.5 amplitude
        t = np.arange(320) / 16000.0
        speech_chunk = (0.5 * np.sin(2 * np.pi * 400 * t)).astype(np.float32)

        # Lead-in silence (5 chunks = 100ms)
        for _ in range(5):
            res = vad.process_chunk(quiet_chunk)
            self.assertIsNone(res)

        # Speech active (15 chunks = 300ms, well above min_speech_duration_ms=120ms)
        for _ in range(15):
            res = vad.process_chunk(speech_chunk)
            self.assertIsNone(res)
        self.assertIn(vad.state, [VADState.IN_SPEECH, VADState.HANGOVER])

        # Hangover silence (16 chunks = 320ms, exceeds hangover_duration_ms=300ms)
        captured_utterance = None
        for _ in range(16):
            res = vad.process_chunk(quiet_chunk)
            if res is not None:
                captured_utterance = res
                break

        self.assertIsNotNone(captured_utterance, "VAD should emit extracted utterance after hangover")
        self.assertEqual(len(captured_utterance), 16000, "Utterance must be exactly 16,000 samples (1.0s)")
        self.assertEqual(captured_utterance.dtype, np.float32)

    def test_vad_continuous_audio_detection(self):
        """Verifies continuous multi-second audio with multiple speech bursts yields distinct utterances."""
        vad = StreamingVADProcessor()
        sr = 16000

        # Create a 3.5s synthetic audio stream:
        # [0.0 - 0.3s] silence
        # [0.3 - 0.7s] speech burst 1 (400ms)
        # [0.7 - 1.5s] silence (800ms)
        # [1.5 - 2.0s] speech burst 2 (500ms)
        # [2.0 - 3.5s] trailing silence (1500ms)
        total_samples = int(3.5 * sr)
        audio = np.zeros(total_samples, dtype=np.float32)

        t1 = np.arange(int(0.4 * sr)) / sr
        audio[int(0.3 * sr) : int(0.7 * sr)] = (0.4 * np.sin(2 * np.pi * 350 * t1)).astype(np.float32)

        t2 = np.arange(int(0.5 * sr)) / sr
        audio[int(1.5 * sr) : int(2.0 * sr)] = (0.4 * np.sin(2 * np.pi * 500 * t2)).astype(np.float32)

        utterances = vad.process_continuous_audio(audio)
        self.assertEqual(len(utterances), 2, f"Expected exactly 2 speech events, got {len(utterances)}")
        for utt in utterances:
            self.assertEqual(len(utt), 16000)

    def test_speech_recognition_manager_streaming_chunk(self):
        """Verifies SpeechRecognitionManager streaming chunk endpointing and speech recognition."""
        mgr = SpeechRecognitionManager()
        mgr.reset_stream()

        quiet_chunk = np.zeros(320, dtype=np.float32)
        speech_chunk = (0.5 * np.sin(2 * np.pi * 440 * np.arange(320) / 16000)).astype(np.float32)

        # Feeding silence yields None
        for _ in range(5):
            res = mgr.process_streaming_chunk(quiet_chunk)
            self.assertIsNone(res)

        # Feeding speech
        for _ in range(15):
            mgr.process_streaming_chunk(speech_chunk)

        # Feeding hangover silence until completion
        final_res = None
        for _ in range(16):
            res = mgr.process_streaming_chunk(quiet_chunk)
            if res is not None:
                final_res = res
                break

        self.assertIsNotNone(final_res, "SpeechRecognitionManager should return result upon utterance endpoint")
        self.assertIn(final_res.engine_name, ["LightweightSpectrogramCNN", "GeneralMundariASR_Interface"])
        self.assertIsInstance(final_res.confidence, float)

    def test_classroom_phrasebook_full_coverage(self):
        """Verifies all 16 classroom interaction phrases match Tier 1 deterministic lookup."""
        self.assertTrue(os.path.exists(self.phrasebook_path), "classroom_phrasebook.json must exist")
        with open(self.phrasebook_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        phrases = data.get("phrases", [])
        self.assertEqual(len(phrases), 16, "Phrasebook must contain exactly 16 classroom interaction phrases")

        expected_categories = {
            "GREETING_ROUTINE",
            "CLASSROOM_MANAGEMENT",
            "ENCOURAGEMENT",
            "NUMERACY_INSTRUCTION",
        }

        found_categories = set()
        for p in phrases:
            # Check schema
            self.assertIn("phrase_id", p)
            self.assertIn("category", p)
            self.assertIn("hindi_text", p)
            self.assertIn("mundari_text", p)
            self.assertIn("mundari_phonetic", p)
            self.assertIn("mundari_root", p)
            self.assertIn("verification_level", p)
            self.assertIn(p["verification_level"], ["CORPUS_ATTESTED", "LINGUISTICALLY_REVIEWED"])
            found_categories.add(p["category"])

            # Test Tier 1 translation lookup
            res = self.translation_engine.translate(p["hindi_text"])
            self.assertEqual(
                res.status,
                "VERIFIED_EDUCATIONAL_LOOKUP",
                f"Phrase '{p['hindi_text']}' must resolve to VERIFIED_EDUCATIONAL_LOOKUP",
            )
            self.assertEqual(res.confidence, 1.0)
            self.assertEqual(res.translated_text, p["mundari_text"])
            self.assertEqual(res.metadata.get("mundari_root"), p["mundari_root"])

        self.assertEqual(found_categories, expected_categories)

    def test_pipeline_streaming_integration(self):
        """Verifies VernacularPedagogyPipeline process_streaming_chunk and process_continuous_stream."""
        pipeline = VernacularPedagogyPipeline()
        quiet_chunk = np.zeros(320, dtype=np.float32)

        # Silence returns None
        chunk_res = pipeline.process_streaming_chunk(quiet_chunk)
        self.assertIsNone(chunk_res)

        # Continuous audio simulation with 1 speech burst
        sr = 16000
        audio = np.zeros(int(2.0 * sr), dtype=np.float32)
        t = np.arange(int(0.4 * sr)) / sr
        audio[int(0.2 * sr) : int(0.6 * sr)] = (0.5 * np.sin(2 * np.pi * 400 * t)).astype(np.float32)

        stream_responses = pipeline.process_continuous_stream(audio)
        self.assertEqual(len(stream_responses), 1)
        resp = stream_responses[0]
        self.assertEqual(resp.input_mode, "SPOKEN_SPEECH")
        self.assertIsNotNone(resp.speech_result)
        # Ambient/tone sound is correctly flagged as low confidence or background noise
        if not resp.is_success:
            self.assertTrue(resp.fallback_recommended)
            self.assertEqual(resp.status_code, "AMBIGUOUS_AUDIO_FALLBACK_RECOMMENDED")


if __name__ == "__main__":
    unittest.main()
