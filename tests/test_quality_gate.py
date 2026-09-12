"""
tests/test_quality_gate.py
=============================================================================
SIH260042: Quality Gate & Linguistic Guardrails Verification Tests
=============================================================================
Verifies that TranslationQualityGate reliably catches:
  1. Empty or near-empty translations
  2. Missing Devanagari script
  3. Excessive punctuation ratio or repeated punctuation runs
  4. Consecutive duplicate words (across Unicode representations)
  5. Low lexical diversity (vocabulary collapse)
  6. Runaway character repetition
  7. Excessive source copying (untranslated echoes)
  8. Degenerate model scores
And verifies graceful fallback routing in TranslationEngine.
=============================================================================
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ai.ml_translation.quality_gate import TranslationQualityGate, QualityGateResult
from ai.ml_translation.inference import NeuralTranslationResult
from ai.translation.translation_engine import TranslationEngine


class TestTranslationQualityGate(unittest.TestCase):

    def setUp(self):
        self.qg = TranslationQualityGate()

    def test_empty_or_near_empty_rejection(self):
        """Verify empty or single-character outputs are rejected."""
        r1 = self.qg.validate("", "नमस्ते", 0.5)
        self.assertFalse(r1.is_valid)
        self.assertIn("EMPTY_OR_NEAR_EMPTY", r1.rejection_reasons)

        r2 = self.qg.validate(" ", "नमस्ते", 0.5)
        self.assertFalse(r2.is_valid)
        self.assertIn("EMPTY_OR_NEAR_EMPTY", r2.rejection_reasons)

        r3 = self.qg.validate("अ", "नमस्ते", 0.5)
        self.assertFalse(r3.is_valid)
        self.assertIn("EMPTY_OR_NEAR_EMPTY", r3.rejection_reasons)

    def test_missing_devanagari_rejection(self):
        """Verify Latin/English output for Devanagari source is rejected."""
        res = self.qg.validate("Hello world from nowhere", "नमस्ते बच्चों", 0.5)
        self.assertFalse(res.is_valid)
        self.assertIn("MISSING_DEVANAGARI_SCRIPT", res.rejection_reasons)

    def test_excessive_punctuation_rejection(self):
        """Verify outputs composed mostly of punctuation are rejected."""
        res = self.qg.validate("मेनाः । , ? ! : ; ।", "क्या हाल है?", 0.5)
        self.assertFalse(res.is_valid)
        self.assertIn("EXCESSIVE_PUNCTUATION_RATIO", res.rejection_reasons)

    def test_pathological_punctuation_run(self):
        """Verify consecutive punctuation runs (e.g. ':::') are rejected."""
        res = self.qg.validate("मेनाः ::: तना", "कहाँ हैं?", 0.5)
        self.assertFalse(res.is_valid)
        self.assertIn("PATHOLOGICAL_PUNCTUATION_RUN", res.rejection_reasons)

    def test_consecutive_word_repetition_rejection(self):
        """Verify consecutive identical words are rejected."""
        res = self.qg.validate("होड़ोको होड़ोको होड़ोको मेनाः", "लोग कहाँ हैं?", 0.5)
        self.assertFalse(res.is_valid)
        self.assertIn("CONSECUTIVE_WORD_REPETITION", res.rejection_reasons)

    def test_low_lexical_diversity_rejection(self):
        """Verify vocabulary collapse / repetition loops are rejected."""
        res = self.qg.validate("काजि ओड़ो काजि ओड़ो काजि ओड़ो", "बातचीत करो", 0.5)
        self.assertFalse(res.is_valid)
        self.assertIn("LOW_LEXICAL_DIVERSITY", res.rejection_reasons)

    def test_runaway_character_repetition_rejection(self):
        """Verify runaway character loops (e.g. 'कककक') are rejected."""
        res = self.qg.validate("होनको ककककक मेनाः", "बच्चे कहाँ हैं?", 0.5)
        self.assertFalse(res.is_valid)
        self.assertIn("RUNAWAY_CHARACTER_REPETITION", res.rejection_reasons)

    def test_excessive_source_copying_rejection(self):
        """Verify verbatim echo of source Hindi text is rejected."""
        src = "हम आज स्कूल जा रहे हैं।"
        res = self.qg.validate(src, src, 0.5)
        self.assertFalse(res.is_valid)
        self.assertIn("EXCESSIVE_SOURCE_COPYING", res.rejection_reasons)

    def test_degenerate_score_rejection(self):
        """Verify near-zero token probability is rejected."""
        res = self.qg.validate("होनको इसकुल सेनोः तना।", "बच्चे स्कूल जा रहे हैं।", model_score=0.01)
        self.assertFalse(res.is_valid)
        self.assertIn("DEGENERATE_MODEL_SCORE", res.rejection_reasons)

    def test_low_confidence_score_rejection(self):
        """Verify scores below calibrated threshold (0.16) are rejected."""
        res = self.qg.validate("साइबर रे रेः जरूड़ी मियुद बोरो तना।", "साइबर सिक्योरिटी एक खतरनाक सब्जेक्ट है।", model_score=0.093)
        self.assertFalse(res.is_valid)
        self.assertIn("LOW_GENERATION_CONFIDENCE", res.rejection_reasons)

    def test_valid_translation_accepted(self):
        """Verify genuine, well-formed translation passes all gates."""
        res = self.qg.validate("चिलका मेनाः चि आम होड़ोको", "कैसे हैं आप लोग?", model_score=0.25)
        self.assertTrue(res.is_valid)
        self.assertEqual(len(res.rejection_reasons), 0)

    def test_engine_fallback_when_quality_gate_fails(self):
        """Verify TranslationEngine catches gate failure and routes to fallback."""
        engine = TranslationEngine(enable_neural=True)
        # Mock neural output that fails quality gate
        engine.neural_engine.translate = MagicMock(return_value=NeuralTranslationResult(
            translated_text="होड़ोको होड़ोको होड़ोको",
            source_text="लोग",
            normalized_source="लोग",
            model_score=0.1,
            latency_ms=10.0,
            quality_gate_passed=False,
            quality_gate_reasons=["CONSECUTIVE_WORD_REPETITION"]
        ))

        res = engine.translate("लोग")
        self.assertNotEqual(res.status, "NEURAL_TRANSLATION_GENERATED")
        self.assertTrue(res.metadata.get("fallback_from_neural"))
        self.assertIn("CONSECUTIVE_WORD_REPETITION", res.metadata.get("neural_rejection_reasons", []))


if __name__ == "__main__":
    unittest.main()
