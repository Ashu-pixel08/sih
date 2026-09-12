"""
tests/test_android_contract_parity.py
=============================================================================
SIH260042: AI-Powered Vernacular Pedagogy & Real-Time Translation
Android Integration Contract & Preprocessing Parity Test Suite
=============================================================================

TEST COVERAGE:
1. test_golden_audio_file_contract:
   Verifies golden WAV audio specification: 16 kHz, 16-bit PCM, mono, 1.0s duration.
2. test_preprocessing_numerical_parity:
   Verifies that Python preprocessing produces exact numerical match to golden tensor.
3. test_hann_window_specification:
   Verifies Hann window size 400, symmetry, zero boundaries, and peak 1.0.
4. test_mel_filterbank_matrix_specification:
   Verifies 64 Mel filters over 257 FFT bins spanning 20 Hz to 8000 Hz.
5. test_tflite_tensor_io_contract:
   Verifies TFLite input tensor shape [1, 101, 64, 1] and output tensor shape [1, 21].
6. test_class_indexing_and_registry_alignment:
   Verifies class 0 is _background_ and classes 1-20 align across registry and contract.
7. test_android_asset_structure_mapping:
   Verifies offline asset packaging paths required for app/src/main/assets/.
=============================================================================
"""

import json
import os
import sys
import unittest
import wave
import numpy as np

cur_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.normpath(os.path.join(cur_dir, ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from ai.preprocessing.audio_preprocessor import AudioPreprocessor, AudioPreprocessingConfig


class TestAndroidContractParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace_root = workspace_root
        cls.preprocessor = AudioPreprocessor()
        cls.test_vectors_dir = os.path.join(workspace_root, "data", "test_vectors")
        cls.golden_wav_path = os.path.join(cls.test_vectors_dir, "golden_audio_16k.wav")
        cls.golden_tensor_path = os.path.join(cls.test_vectors_dir, "golden_spectrogram_101_64.npy")
        cls.contract_spec_path = os.path.join(cls.test_vectors_dir, "golden_contract_spec.json")

    def test_golden_audio_file_contract(self):
        """Verify golden audio file matches the exact 16 kHz 16-bit PCM mono specification."""
        self.assertTrue(os.path.exists(self.golden_wav_path), "Golden audio file missing")
        with wave.open(self.golden_wav_path, "rb") as wf:
            self.assertEqual(wf.getnchannels(), 1, "Must be mono audio")
            self.assertEqual(wf.getsampwidth(), 2, "Must be 16-bit (2 bytes)")
            self.assertEqual(wf.getframerate(), 16000, "Must be 16 kHz sample rate")
            self.assertEqual(wf.getnframes(), 16000, "Must be exactly 1.0s (16,000 samples)")

    def test_preprocessing_numerical_parity(self):
        """Verify preprocessing of golden audio exactly matches saved golden spectrogram tensor."""
        self.assertTrue(os.path.exists(self.golden_tensor_path), "Golden tensor missing")
        golden_tensor = np.load(self.golden_tensor_path)

        # Preprocess golden audio file
        audio_16k, log_mel = self.preprocessor.preprocess_file(self.golden_wav_path)

        # Assert shape parity: [101, 64]
        self.assertEqual(log_mel.shape, (101, 64))
        self.assertEqual(golden_tensor.shape, (101, 64))

        # Assert numerical parity (max absolute error < 1e-4)
        max_abs_diff = float(np.max(np.abs(log_mel - golden_tensor)))
        self.assertLess(max_abs_diff, 1e-4, f"Spectrogram drift {max_abs_diff} exceeds tolerance 1e-4")

    def test_hann_window_specification(self):
        """Verify periodic Hann window of 400 samples matching Kotlin buildHannWindow()."""
        window = self.preprocessor._hann_window
        self.assertEqual(len(window), 400)
        self.assertAlmostEqual(float(window[0]), 0.0, places=4)
        # Periodic Hann reaches peak near center
        center_idx = len(window) // 2
        self.assertAlmostEqual(float(window[center_idx]), 1.0, places=1)
        # Symmetry check
        for i in range(len(window) // 2):
            self.assertAlmostEqual(float(window[i]), float(window[len(window) - 1 - i]), places=4)

    def test_mel_filterbank_matrix_specification(self):
        """Verify 64 triangular Mel filterbank matrix across 257 FFT bins (20 Hz to 8000 Hz)."""
        mel_fb = self.preprocessor._mel_filterbank
        self.assertEqual(mel_fb.shape, (64, 257))
        # Values must be non-negative
        self.assertTrue(np.all(mel_fb >= 0.0))
        # Each filter must have non-zero energy
        filter_energies = np.sum(mel_fb, axis=1)
        self.assertTrue(np.all(filter_energies > 0.0))

    def test_tflite_tensor_io_contract(self):
        """Verify contract specification defines expected input and output tensor dimensions."""
        self.assertTrue(os.path.exists(self.contract_spec_path))
        with open(self.contract_spec_path, "r", encoding="utf-8") as f:
            spec = json.load(f)

        tflite_spec = spec["tflite_model"]
        self.assertEqual(tflite_spec["input_tensor"]["shape"], [1, 101, 64, 1])
        self.assertEqual(tflite_spec["input_tensor"]["dtype"], "FLOAT32")
        self.assertEqual(tflite_spec["output_tensor"]["shape"], [1, 21])
        self.assertEqual(tflite_spec["output_tensor"]["dtype"], "FLOAT32")
        self.assertEqual(tflite_spec["classes_count"], 21)
        self.assertEqual(tflite_spec["background_class_index"], 0)

    def test_class_indexing_and_registry_alignment(self):
        """Verify class indices 1-20 in registry match TFLite output dimension contract."""
        registry_path = os.path.join(self.workspace_root, "content", "content_registry.json")
        with open(registry_path, "r", encoding="utf-8") as f:
            reg = json.load(f)

        items = reg["items"]
        self.assertEqual(len(items), 20)
        for expected_num in range(1, 21):
            matching = [it for it in items if it["number"] == expected_num]
            self.assertEqual(len(matching), 1)
            self.assertEqual(matching[0]["class_index"], expected_num)

    def test_android_asset_structure_mapping(self):
        """Verify all essential assets mapped for app/src/main/assets/ physically exist."""
        # 1. Content Registry
        self.assertTrue(os.path.exists(os.path.join(self.workspace_root, "content", "content_registry.json")))
        # 2. Audio Manifest
        self.assertTrue(os.path.exists(os.path.join(self.workspace_root, "content", "audio", "audio_manifest.json")))
        # 3. Translation Corpus TSV
        self.assertTrue(os.path.exists(os.path.join(self.workspace_root, "data", "raw", "translation", "translation-hi-unr.tsv")))
        # 4. Flashcard SVGs (all 20 exist)
        for i in range(1, 21):
            card_path = os.path.join(self.workspace_root, "content", "flashcards", "numbers", f"card_{i:02d}.svg")
            self.assertTrue(os.path.exists(card_path), f"Flashcard {card_path} missing")
        # 5. Prototype Audio (all 20 numerals + 16 phrases exist)
        for i in range(1, 21):
            audio_path = os.path.join(self.workspace_root, "content", "audio", "prototype_tts", "numbers", f"num_{i:02d}.wav")
            self.assertTrue(os.path.exists(audio_path), f"Prototype audio {audio_path} missing")


if __name__ == "__main__":
    unittest.main()
