"""
tests/test_general_mundari_asr.py
=============================================================================
SIH260042: Unit Test Suite for Phase C: General Mundari ASR Benchmark
=============================================================================
"""

import os
import sys
import unittest

cur_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.normpath(os.path.join(cur_dir, ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from ai.speech.general_mundari_asr_benchmark import GeneralMundariASRBenchmark


class TestGeneralMundariASRBenchmark(unittest.TestCase):
    """Verifies General Mundari ASR model evaluation and error metric calculations."""

    @classmethod
    def setUpClass(cls):
        cls.benchmark = GeneralMundariASRBenchmark()

    def test_model_profile_technical_contract(self):
        """Verifies MMS-1B model profile specifications and edge unfeasibility."""
        profile = self.benchmark.get_model_profile()
        self.assertEqual(profile["model_name"], "facebook/mms-1b-all")
        self.assertEqual(profile["parameters"], 1_000_000_000)
        self.assertEqual(profile["adapter_language"], "unr")
        self.assertIn("UNFEASIBLE_ON_LOW_COST_ANDROID", profile["edge_feasibility"])
        self.assertGreaterEqual(profile["active_ram_desktop_mb"], 4000.0)

    def test_cer_and_wer_mathematical_precision(self):
        """Verifies Levenshtein CER and WER implementations against reference cases."""
        # Exact match
        self.assertEqual(self.benchmark.calculate_cer("मिअद", "मिअद"), 0.0)
        self.assertEqual(self.benchmark.calculate_wer("मिअद बारिया", "मिअद बारिया"), 0.0)

        # Substitution
        cer = self.benchmark.calculate_cer("मिअद", "मियद")
        self.assertAlmostEqual(cer, 1.0 / 4.0)

        # Deletion
        cer_del = self.benchmark.calculate_cer("बारिया", "बारि")
        self.assertAlmostEqual(cer_del, 2.0 / 6.0)

        # Completely empty hypothesis
        self.assertEqual(self.benchmark.calculate_cer("मिअद", ""), 1.0)
        self.assertEqual(self.benchmark.calculate_wer("मिअद बारिया", ""), 1.0)

    def test_evaluation_on_local_sample(self):
        """Verifies benchmark execution on authentic local speech recordings."""
        res = self.benchmark.evaluate_local_sample(max_samples=10)
        self.assertNotIn("error", res)
        self.assertGreaterEqual(res["total_samples_evaluated"], 2)
        self.assertGreater(res["total_audio_duration_sec"], 0.0)
        self.assertGreaterEqual(res["average_cer"], 0.0)
        self.assertLessEqual(res["average_cer"], 1.0)
        self.assertGreaterEqual(res["average_wer"], 0.0)
        self.assertLessEqual(res["average_wer"], 1.0)
        self.assertGreater(res["average_rtf"], 0.0)
        self.assertGreaterEqual(len(res["failure_modes_identified"]), 3)


if __name__ == "__main__":
    unittest.main()
