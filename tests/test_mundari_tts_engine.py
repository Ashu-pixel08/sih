"""
tests/test_mundari_tts_engine.py
=============================================================================
SIH260042: Unit Test Suite for Phase B: Offline Mundari Educational Audio (TTS)
=============================================================================
"""

import json
import os
import sys
import unittest
import wave

cur_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.normpath(os.path.join(cur_dir, ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from ai.speech.mundari_tts_engine import MundariTTSEngine, TTSGenerationResult


class TestMundariTTSEngine(unittest.TestCase):
    """Verifies the offline Mundari TTS pipeline, asset generation, and labeling."""

    @classmethod
    def setUpClass(cls):
        cls.engine = MundariTTSEngine()

    def test_render_audio_file_waveform(self):
        """Verifies individual audio file rendering produces valid 16kHz PCM WAV."""
        res = self.engine.render_audio_file("test_num_01", "मिअद", category="number")
        self.assertIsInstance(res, TTSGenerationResult)
        self.assertEqual(res.content_id, "test_num_01")
        self.assertEqual(res.mundari_text, "मिअद")
        self.assertEqual(res.sample_rate, 16000)
        self.assertGreater(res.duration_sec, 0.3)
        self.assertEqual(len(res.checksum_sha256), 64)
        
        # Verify physical WAV file on disk
        full_path = os.path.join(workspace_root, res.audio_file_path)
        self.assertTrue(os.path.exists(full_path))
        with wave.open(full_path, "rb") as wf:
            self.assertEqual(wf.getnchannels(), 1)
            self.assertEqual(wf.getsampwidth(), 2)  # 16-bit
            self.assertEqual(wf.getframerate(), 16000)

    def test_curriculum_pre_render_and_manifest(self):
        """Verifies complete pre-rendering of 20 numerals and classroom phrases."""
        manifest = self.engine.pre_render_educational_curriculum()
        self.assertIn("total_audio_assets", manifest)
        self.assertGreaterEqual(manifest["total_audio_assets"], 36)
        self.assertEqual(manifest["language_code"], "unr")
        self.assertEqual(manifest["verification_policy"], "SYNTHETIC_PROTOTYPE (PENDING HUMAN VALIDATION)")
        
        # Check manifest file on disk
        manifest_path = os.path.join(self.engine.output_base_dir, "audio_manifest.json")
        self.assertTrue(os.path.exists(manifest_path))

    def test_synthetic_audio_labeling_policy(self):
        """Verifies all assets are strictly marked as synthetic prototypes."""
        manifest_path = os.path.join(self.engine.output_base_dir, "audio_manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("CRITICAL: Synthetic TTS audio is strictly for prototype demonstration", data["disclaimer"])
        for asset in data["assets"]:
            self.assertTrue(asset["is_synthetic"])
            self.assertEqual(asset["verification_status"], "SYNTHETIC_PROTOTYPE (PENDING HUMAN VALIDATION)")


if __name__ == "__main__":
    unittest.main()
