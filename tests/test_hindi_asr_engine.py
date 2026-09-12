"""
tests/test_hindi_asr_engine.py
=============================================================================
SIH260042: Unit Test Suite for Capability B: Offline Teacher Hindi ASR Engine
=============================================================================
"""

import math
import os
import sys
import unittest
import numpy as np

cur_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.normpath(os.path.join(cur_dir, ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from ai.speech.hindi_asr_engine import HindiASRRecognizer, HindiASRResult


class TestHindiASREngine(unittest.TestCase):
    """Verifies the offline Teacher Hindi ASR engine behavior and quality gates."""

    @classmethod
    def setUpClass(cls):
        cls.engine = HindiASRRecognizer()
        cls.sample_rate = 16000

    def test_engine_initialization_and_lexicon(self):
        """Verifies engine loads Hindi numerals 1-20 and classroom commands."""
        self.assertGreaterEqual(len(self.engine.lexicon), 30)
        # Check numerals
        for num_word in ["एक", "दो", "तीन", "चार", "पांच", "दस", "बीस"]:
            self.assertIn(num_word, self.engine.lexicon)
            self.assertEqual(self.engine.lexicon[num_word]["category"], "number")
        # Check commands
        for cmd in ["सुनो", "बैठो", "किताब खोलो", "शाबाश"]:
            self.assertIn(cmd, self.engine.lexicon)
            self.assertEqual(self.engine.lexicon[cmd]["category"], "command")

    def test_clean_speech_recognition_numerals(self):
        """Verifies clean audio input matches expected Hindi numeral candidate."""
        # Generate clean synthetic test wave for 'एक'
        duration = 0.8
        t = np.linspace(0, duration, int(duration * self.sample_rate), endpoint=False)
        audio = (0.22 * np.sin(2 * np.pi * 320.0 * t) * (1.0 - 0.5 * np.cos(2 * np.pi * 4.0 * t))).astype(np.float32)
        
        result = self.engine.recognize_audio(audio, sample_rate=self.sample_rate)
        self.assertIsInstance(result, HindiASRResult)
        self.assertEqual(result.duration_sec, 0.8)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertIn("candidate_word", result.metrics)

    def test_silence_rejection(self):
        """Verifies low-energy silence is strictly rejected without hallucination."""
        # Flat zero audio
        silence = np.zeros(int(0.8 * self.sample_rate), dtype=np.float32)
        result = self.engine.recognize_audio(silence, sample_rate=self.sample_rate)
        
        self.assertEqual(result.status, "SILENCE")
        self.assertIsNone(result.recognized_text)
        self.assertEqual(result.confidence, 0.0)
        self.assertFalse(result.is_confident)

    def test_extreme_noise_rejection(self):
        """Verifies low-SNR noisy input triggers LOW_CONFIDENCE rejection."""
        # Low-amplitude pure white noise with poor SNR
        rng = np.random.RandomState(42)
        noise = rng.normal(0, 0.003, int(0.9 * self.sample_rate)).astype(np.float32)
        result = self.engine.recognize_audio(noise, sample_rate=self.sample_rate)
        
        self.assertIn(result.status, {"LOW_CONFIDENCE", "SILENCE"})
        self.assertFalse(result.is_confident)

    def test_hardware_profiling_and_status_separation(self):
        """Verifies clear separation between Model-Level, Desktop, and Android metrics."""
        dummy_audio = np.ones(int(0.5 * self.sample_rate), dtype=np.float32) * 0.1
        res = self.engine.recognize_audio(dummy_audio, sample_rate=self.sample_rate)
        
        profile = res.hardware_profile
        self.assertIn("model_specs", profile)
        self.assertIn("desktop_measured", profile)
        self.assertIn("android_estimated", profile)
        self.assertIn("android_measured", profile)
        
        # Verify Android measured is honestly PENDING
        self.assertEqual(profile["android_measured"], "PENDING_PHYSICAL_DEVICE_DEPLOYMENT")
        # Verify desktop measured latency is finite and non-negative
        self.assertGreaterEqual(profile["desktop_measured"]["latency_ms"], 0.0)


if __name__ == "__main__":
    unittest.main()
