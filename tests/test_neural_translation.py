"""
tests/test_neural_translation.py
=============================================================================
SIH260042: Neural Machine Translation & 4-Tier Architecture Verification Tests
=============================================================================
"""

import os
import sys
import unittest
import torch

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ai.ml_translation.tokenizer import NMTTokenizer
from ai.ml_translation.model import Seq2SeqTransformer
from ai.ml_translation.inference import NeuralTranslationEngine
from ai.translation.translation_engine import TranslationEngine, TranslationResult


class TestNeuralTranslation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tok_dir = os.path.join(BASE_DIR, "models", "nmt", "tokenizer")
        cls.ckpt_path = os.path.join(BASE_DIR, "models", "nmt", "checkpoints", "best_transformer.pt")
        cls.engine_neural = TranslationEngine(enable_neural=True)
        cls.engine_retrieval = TranslationEngine(enable_neural=False)

    def test_tokenizers_available_and_valid(self):
        """Verify BPE tokenizers exist and encode/decode cleanly."""
        hi_path = os.path.join(self.tok_dir, "hindi_bpe.json")
        unr_path = os.path.join(self.tok_dir, "mundari_bpe.json")
        self.assertTrue(os.path.exists(hi_path), "Hindi tokenizer file must exist")
        self.assertTrue(os.path.exists(unr_path), "Mundari tokenizer file must exist")

        hi_tok = NMTTokenizer(hi_path)
        unr_tok = NMTTokenizer(unr_path)

        self.assertEqual(hi_tok.vocab_size, 6000)
        self.assertEqual(unr_tok.vocab_size, 8000)

        # Roundtrip check
        sample_hi = "नमस्ते बच्चों"
        enc = hi_tok.encode(sample_hi)
        self.assertGreater(len(enc), 2)
        dec = hi_tok.decode(enc)
        self.assertTrue(len(dec) > 0)

    def test_checkpoint_exists_and_parameters(self):
        """Verify trained PyTorch model checkpoint exists and matches architecture specifications."""
        self.assertTrue(os.path.exists(self.ckpt_path), "Trained checkpoint must exist")
        ckpt = torch.load(self.ckpt_path, map_location="cpu", weights_only=False)
        self.assertIn("model_state_dict", ckpt)
        self.assertIn("config", ckpt)
        cfg = ckpt["config"]
        self.assertEqual(cfg["d_model"], 256)
        self.assertEqual(cfg["nhead"], 4)
        self.assertEqual(cfg["num_encoder_layers"], 3)
        self.assertEqual(cfg["num_decoder_layers"], 3)

    def test_tier1_educational_registry_precedence(self):
        """Verify Tier 1 exact educational entries take precedence over neural generation."""
        res = self.engine_neural.translate("पाँच")
        self.assertEqual(res.status, "VERIFIED_EDUCATIONAL_LOOKUP")
        self.assertEqual(res.translation_source, "EDUCATIONAL_REGISTRY")
        self.assertEqual(res.confidence, 1.0)
        self.assertFalse(res.requires_validation)
        self.assertEqual(res.translated_text, "मोड़ेया")

        res_g = self.engine_neural.translate("नमस्ते")
        self.assertEqual(res_g.status, "VERIFIED_EDUCATIONAL_LOOKUP")
        self.assertEqual(res_g.translation_source, "EDUCATIONAL_REGISTRY")
        self.assertEqual(res_g.translated_text, "जोहार")

    def test_tier2_neural_generation_on_unseen_query(self):
        """Verify unseen conversational queries route to Tier 2 Neural Model and generate translations."""
        query = "कैसे हैं आप लोग?"
        res = self.engine_neural.translate(query)

        self.assertEqual(res.status, "NEURAL_TRANSLATION_GENERATED")
        self.assertEqual(res.translation_source, "NEURAL_MODEL")
        self.assertEqual(res.match_type, "TIER_2_NEURAL_GENERATED")
        self.assertTrue(res.requires_validation)
        self.assertEqual(res.provenance_label, "AI-GENERATED — REQUIRES LINGUISTIC VALIDATION")
        self.assertTrue(res.translated_text and len(res.translated_text.strip()) > 0)
        self.assertGreater(res.confidence, 0.0)
        self.assertIn("latency_ms", res.metadata)

    def test_tier3_retrieval_fallback_when_neural_disabled(self):
        """Verify system falls back to Tier 3 Corpus Retrieval when neural is disabled."""
        query = "सुधार के लिए आठ महीने"
        res = self.engine_retrieval.translate(query)
        self.assertEqual(res.status, "CORPUS_RETRIEVAL_MATCH")
        self.assertEqual(res.translation_source, "CORPUS_RETRIEVAL")
        self.assertGreaterEqual(res.confidence, 0.55)

    def test_tier4_safe_rejection_of_gibberish(self):
        """Verify non-Devanagari / ASCII gibberish is safely rejected without hallucination."""
        gibberish = "xyz123abc random gibberish"
        res = self.engine_neural.translate(gibberish)
        self.assertEqual(res.status, "OUT_OF_VOCABULARY_UNVERIFIED")
        self.assertEqual(res.translation_source, "SAFE_FALLBACK")
        self.assertIsNone(res.translated_text)

    def test_exported_torchscript_model(self):
        """Verify exported TorchScript model loads and runs inference offline."""
        ts_path = os.path.join(BASE_DIR, "models", "nmt", "exported", "hindi_mundari_nmt.torchscript.pt")
        self.assertTrue(os.path.exists(ts_path), "TorchScript model must exist")
        loaded_ts = torch.jit.load(ts_path, map_location="cpu")
        dummy_src = torch.randint(1, 1000, (1, 8), dtype=torch.long)
        dummy_tgt = torch.randint(1, 1000, (1, 8), dtype=torch.long)
        with torch.no_grad():
            out = loaded_ts(dummy_src, dummy_tgt)
        self.assertEqual(out.shape, torch.Size([1, 8, 8000]))


if __name__ == "__main__":
    unittest.main()
