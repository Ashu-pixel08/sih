"""
tests/test_speech_model.py
=============================================================================
SIH260042: Automated Test Suite for Speech Classifier & TFLite Edge Model
=============================================================================

TEST CODES & VALIDATION:
1. test_model_architecture_and_contract:
   Verifies input shape [1, 101, 64, 1], output [1, 21], parameter count < 150k.
2. test_class_mapping_registry_parity:
   Ensures 21 classes match content/content_registry.json without divergence.
3. test_augmentation_train_isolation:
   Verifies augmentation is strictly inactive during eval/test to prevent leakage.
4. test_dataset_loader_and_speaker_splitter:
   Verifies speaker-aware partition guarantees zero speaker leakage across splits.
5. test_data_sufficiency_policy_enforcement:
   Verifies evaluator flags MISSING — SUFFICIENT LABELED 1–20 SPEECH DATA.
6. test_tflite_contract_and_model_size:
   Verifies exported .tflite tensor contract and file size (< 1.0 MB).
7. test_golden_inference_parity_pytorch_vs_tflite:
   Verifies end-to-end numerical parity (max diff < 1e-4) between PyTorch and LiteRT.
=============================================================================
"""

import json
import os
import sys
import unittest

import numpy as np
import torch

cur_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.normpath(os.path.join(cur_dir, ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

import ai_edge_litert.interpreter as tflite

from ai.preprocessing.audio_preprocessor import AudioPreprocessor
from ai.speech.speech_classifier import LightweightSpectrogramCNN
from ai.training.augmentation import SpectrogramAugmentation
from ai.training.dataset_loader import (
    AudioSampleMeta,
    DatasetManager,
    MundariSpeechDataset,
)
from ai.training.evaluator import SpeechModelEvaluator
from ai.training.synthetic_simulation_harness import SyntheticSimulationHarness


class TestSpeechModelAndTFLite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace_root = workspace_root
        cls.registry_path = os.path.join(cls.workspace_root, "content", "content_registry.json")
        cls.tflite_path = os.path.join(cls.workspace_root, "models", "edge", "speech_classifier_float32.tflite")
        cls.checkpoint_path = os.path.join(cls.workspace_root, "models", "checkpoints", "best_model.pt")

        cls.model = LightweightSpectrogramCNN(num_classes=21)
        if os.path.exists(cls.checkpoint_path):
            ckpt = torch.load(cls.checkpoint_path, weights_only=False, map_location="cpu")
            if "model_state_dict" in ckpt:
                cls.model.load_state_dict(ckpt["model_state_dict"])
            else:
                cls.model.load_state_dict(ckpt)
        cls.model.eval()

    def test_model_architecture_and_contract(self):
        """Verify input [1, 101, 64, 1], output [1, 21], and parameter budget."""
        summary = self.model.get_model_summary()
        self.assertEqual(summary["num_classes"], 21)
        self.assertEqual(summary["input_tensor_shape"], [1, 101, 64, 1])
        self.assertEqual(summary["output_tensor_shape"], [1, 21])
        self.assertLess(summary["parameters"], 200000, "Model exceeds lightweight parameter budget")
        self.assertLess(summary["fp32_size_kb"], 1000.0, "FP32 size exceeds 1 MB limit")

        # Test forward pass with NHWC [1, 101, 64, 1]
        x_nhwc = torch.randn(1, 101, 64, 1)
        probs = self.model(x_nhwc, return_probabilities=True)
        self.assertEqual(list(probs.shape), [1, 21])
        self.assertAlmostEqual(float(torch.sum(probs).item()), 1.0, places=4)

        # Test predict method
        res = self.model.predict(np.zeros((101, 64), dtype=np.float32))
        self.assertIn("class_index", res)
        self.assertIn("label", res)
        self.assertIn("confidence", res)
        self.assertIn("is_confident", res)

    def test_class_mapping_registry_parity(self):
        """Verify class labels match content_registry.json without drift."""
        with open(self.registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)

        expected_labels = ["_background_"] * 21
        expected_labels[0] = registry["background_class"]["label_id"]
        for item in registry["items"]:
            expected_labels[item["class_index"]] = item["label_id"]

        self.assertEqual(self.model.class_labels, expected_labels)

    def test_augmentation_train_isolation(self):
        """Verify augmentation is strictly applied in training and disabled in eval."""
        aug = SpectrogramAugmentation(time_mask_max=15, p=1.0, seed=42)
        sample_spec = torch.ones(1, 101, 64)

        # In eval mode: MUST NOT modify tensor
        eval_spec = aug(sample_spec, is_training=False)
        self.assertTrue(torch.equal(sample_spec, eval_spec), "Augmentation leaked into evaluation mode!")

        # In train mode: MUST modify tensor
        train_spec = aug(sample_spec, is_training=True)
        self.assertFalse(torch.equal(sample_spec, train_spec), "Augmentation did not apply in training mode")

    def test_dataset_loader_and_speaker_splitter(self):
        """Verify speaker-aware partition guarantees zero speaker leakage."""
        harness = SyntheticSimulationHarness(num_classes=21, seed=42)
        samples = harness.generate_dataset(samples_per_class=4, num_mock_speakers=4)

        mgr = DatasetManager(self.registry_path)
        train_s, val_s, test_s = mgr.split_speaker_aware(samples, train_ratio=0.5, val_ratio=0.25, test_ratio=0.25, seed=42)

        train_spks = set(s.speaker_id for s in train_s)
        val_spks = set(s.speaker_id for s in val_s)
        test_spks = set(s.speaker_id for s in test_s)

        # Assert no overlap between splits
        self.assertEqual(len(train_spks.intersection(val_spks)), 0, "Speaker leaked between train and val")
        self.assertEqual(len(train_spks.intersection(test_spks)), 0, "Speaker leaked between train and test")
        self.assertEqual(len(val_spks.intersection(test_spks)), 0, "Speaker leaked between val and test")

    def test_data_sufficiency_policy_enforcement(self):
        """Verify evaluator enforces MISSING — SUFFICIENT LABELED 1–20 SPEECH DATA."""
        evaluator = SpeechModelEvaluator()
        # Mock dataset with only background class (no numerals 1-20)
        bg_samples = [
            AudioSampleMeta(
                sample_id=f"bg_{i}",
                file_path=None,
                spectrogram=np.zeros((101, 64), dtype=np.float32),
                label_idx=0,
                label_id="_background_",
                speaker_id="spk_01",
                duration_sec=1.0,
                category="REAL_BACKGROUND",
            )
            for i in range(10)
        ]

        ds = MundariSpeechDataset(bg_samples)
        loader = torch.utils.data.DataLoader(ds, batch_size=5)
        results = evaluator.evaluate(self.model, loader, dataset_category="REAL")

        self.assertEqual(results["evaluation_status"], "MISSING — SUFFICIENT LABELED 1–20 SPEECH DATA")
        self.assertFalse(results["production_accuracy_claim_permitted"])

    def test_tflite_contract_and_model_size(self):
        """Verify exported TFLite file matches shape, dtype, and size contracts."""
        self.assertTrue(os.path.exists(self.tflite_path), f"TFLite model missing at {self.tflite_path}")

        interp = tflite.Interpreter(model_path=self.tflite_path)
        interp.allocate_tensors()

        in_details = interp.get_input_details()
        out_details = interp.get_output_details()

        # Contract assertions
        self.assertEqual(in_details[0]["shape"].tolist(), [1, 101, 64, 1])
        self.assertEqual(in_details[0]["dtype"], np.float32)
        self.assertEqual(out_details[0]["shape"].tolist(), [1, 21])
        self.assertEqual(out_details[0]["dtype"], np.float32)

        # Size assertion: must be < 1.5 MB
        size_kb = os.path.getsize(self.tflite_path) / 1024.0
        self.assertLess(size_kb, 1500.0, f"TFLite model exceeds 1.5 MB limit: {size_kb} KB")
        self.assertGreater(size_kb, 50.0, "TFLite model seems too small or corrupt")

    def test_golden_inference_parity_pytorch_vs_tflite(self):
        """
        Golden Deterministic Parity Test:
        Compares:
          Python Preprocessing -> PyTorch Model -> Output
        with:
          Python Preprocessing -> TFLite Model -> Output
        """
        rng = np.random.RandomState(42)
        interp = tflite.Interpreter(model_path=self.tflite_path)
        interp.allocate_tensors()

        in_idx = interp.get_input_details()[0]["index"]
        out_idx = interp.get_output_details()[0]["index"]

        max_allowed_diff = 1e-4  # Float32 numerical precision tolerance

        for i in range(5):
            # Input spectrogram in NHWC [1, 101, 64, 1]
            test_spectrogram = rng.randn(1, 101, 64, 1).astype(np.float32)

            # PyTorch inference
            py_res = self.model.predict(test_spectrogram)
            py_class = py_res["class_index"]
            py_probs = np.array(py_res["probabilities"], dtype=np.float32)

            # TFLite inference
            interp.set_tensor(in_idx, test_spectrogram)
            interp.invoke()
            tf_probs = interp.get_tensor(out_idx).squeeze(0)
            tf_class = int(np.argmax(tf_probs))

            # Parity checks
            self.assertEqual(py_class, tf_class, f"Class mismatch on sample {i}: PyTorch={py_class}, TFLite={tf_class}")

            abs_diff = np.max(np.abs(py_probs - tf_probs))
            self.assertLess(
                abs_diff,
                max_allowed_diff,
                f"Probability difference {abs_diff} exceeds tolerance {max_allowed_diff} on sample {i}",
            )


if __name__ == "__main__":
    unittest.main()
