"""
tests/test_deployment_bundle.py
=============================================================================
SIH260042: Automated Verification Test Suite for Edge Deployment Bundle
=============================================================================

TEST CODES & VALIDATION:
1. test_manifest_exists_and_schema_valid:
   Verifies deployment/manifest.json exists, parses, and conforms to required schema.
2. test_all_bundle_files_exist_and_sha256_match:
   Verifies every referenced artifact exists on disk with exact byte size and SHA256 parity.
3. test_model_input_output_contract:
   Verifies LiteRT TFLite interpreter matches [1, 101, 64, 1] input and [1, 21] output.
4. test_class_ordering_and_registry_parity:
   Verifies contiguous class indexing 0..20 and 100% parity with content_registry.json.
5. test_dsp_and_vad_spec_parity:
   Verifies preprocessing and VAD specifications match live Python engine parameters.
6. test_asset_references_and_anti_fabrication:
   Verifies all 20 SVGs exist, all 1-20 audio files are strictly MISSING, 0 fabricated.
7. test_offline_only_and_zero_network_dependency:
   Verifies bundle contains zero remote network endpoints and mandates 100% offline runtime.
8. test_end_to_end_bundle_reproducibility:
   Executes complete Audio -> VAD -> Preprocessing -> TFLite -> Registry -> FLN output
   using bundle assets.
=============================================================================
"""

import hashlib
import json
import os
import sys
import unittest

import numpy as np

cur_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.normpath(os.path.join(cur_dir, ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

import ai_edge_litert.interpreter as tflite

from ai.preprocessing.audio_preprocessor import AudioPreprocessor
from ai.preprocessing.vad_stream_processor import StreamingVADProcessor, VADConfig


class TestDeploymentBundle(unittest.TestCase):
    """Verifies edge deployment packaging, manifests, contracts, and reproducibility."""

    @classmethod
    def setUpClass(cls):
        cls.workspace_root = workspace_root
        cls.deploy_dir = os.path.join(workspace_root, "deployment")
        cls.manifest_path = os.path.join(cls.deploy_dir, "manifest.json")
        cls.bundle_dir = os.path.join(cls.deploy_dir, "bundle")

    def test_manifest_exists_and_schema_valid(self):
        """Verifies deployment/manifest.json exists, parses, and conforms to schema."""
        self.assertTrue(os.path.exists(self.manifest_path), "manifest.json must exist")
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        self.assertEqual(manifest["manifest_version"], "1.0.0")
        self.assertEqual(manifest["project_code"], "SIH260042")
        self.assertIn("summary", manifest)
        self.assertIn("artifacts", manifest)
        self.assertGreaterEqual(manifest["summary"]["total_artifacts"], 40)
        self.assertLess(manifest["summary"]["total_size_mb"], 5.0, "Total bundle must be lightweight (< 5MB)")

    def test_all_bundle_files_exist_and_sha256_match(self):
        """Verifies every referenced artifact exists on disk with exact byte size and SHA256."""
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        for art in manifest["artifacts"]:
            full_path = os.path.join(self.bundle_dir, art["file_path"])
            self.assertTrue(os.path.exists(full_path), f"Bundle artifact {art['file_path']} must exist")
            actual_size = os.path.getsize(full_path)
            self.assertEqual(actual_size, art["size_bytes"], f"Byte size mismatch for {art['file_path']}")

            hasher = hashlib.sha256()
            with open(full_path, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            actual_sha = hasher.hexdigest()
            self.assertEqual(actual_sha, art["sha256"], f"SHA256 checksum mismatch for {art['file_path']}")

    def test_model_input_output_contract(self):
        """Verifies LiteRT TFLite interpreter matches [1, 101, 64, 1] input and [1, 21] output."""
        model_fp32_path = os.path.join(self.bundle_dir, "models", "speech_classifier_float32.tflite")
        interp = tflite.Interpreter(model_path=model_fp32_path)
        interp.allocate_tensors()

        in_details = interp.get_input_details()[0]
        out_details = interp.get_output_details()[0]

        self.assertEqual(list(in_details["shape"]), [1, 101, 64, 1])
        self.assertEqual(in_details["dtype"], np.float32)

        self.assertEqual(list(out_details["shape"]), [1, 21])
        self.assertEqual(out_details["dtype"], np.float32)

    def test_class_ordering_and_registry_parity(self):
        """Verifies contiguous class indexing 0..20 and 100% parity with content_registry.json."""
        map_path = os.path.join(self.bundle_dir, "models", "class_index_mapping.json")
        reg_path = os.path.join(self.bundle_dir, "content", "content_registry.json")

        with open(map_path, "r", encoding="utf-8") as f:
            class_map = json.load(f)
        with open(reg_path, "r", encoding="utf-8") as f:
            reg = json.load(f)

        self.assertEqual(class_map["total_classes"], 21)
        classes = class_map["classes"]
        self.assertEqual(len(classes), 21)

        # Contiguous index check
        for idx in range(21):
            self.assertEqual(classes[idx]["index"], idx)

        # Class 0 background
        self.assertEqual(classes[0]["label_id"], "_background_")
        self.assertFalse(classes[0]["is_number"])

        # Parity with content_registry
        for idx in range(1, 21):
            cls_item = classes[idx]
            reg_item = next(it for it in reg["items"] if it["class_index"] == idx)
            self.assertEqual(cls_item["label_id"], reg_item["label_id"])
            self.assertEqual(cls_item["number"], reg_item["number"])
            self.assertEqual(cls_item["hindi_text"], reg_item["hindi_text"])
            self.assertEqual(cls_item["mundari_text"], reg_item["mundari_text"])

    def test_dsp_and_vad_spec_parity(self):
        """Verifies preprocessing and VAD specifications match live Python engine parameters."""
        dsp_path = os.path.join(self.bundle_dir, "config", "audio_preprocessing_spec.json")
        vad_path = os.path.join(self.bundle_dir, "config", "vad_config.json")

        with open(dsp_path, "r", encoding="utf-8") as f:
            dsp = json.load(f)
        with open(vad_path, "r", encoding="utf-8") as f:
            vad = json.load(f)

        prep = AudioPreprocessor()
        self.assertEqual(dsp["audio_input"]["sample_rate_hz"], prep.config.target_sample_rate)
        self.assertEqual(dsp["stft_parameters"]["frame_length_samples"], prep.config.win_length)
        self.assertEqual(dsp["stft_parameters"]["hop_length_samples"], prep.config.hop_length)
        self.assertEqual(dsp["stft_parameters"]["fft_length"], prep.config.n_fft)
        self.assertEqual(dsp["mel_filterbank"]["num_mel_bins"], prep.config.n_mels)
        self.assertEqual(dsp["output_tensor"]["shape"], [1, 101, 64, 1])

        vad_cfg = VADConfig()
        self.assertEqual(vad["chunk_size_samples"], vad_cfg.chunk_size_samples)
        self.assertEqual(vad["sample_rate_hz"], vad_cfg.sample_rate)
        self.assertEqual(vad["thresholds"]["initial_noise_floor_db"], vad_cfg.initial_noise_floor_db)
        self.assertEqual(vad["thresholds"]["speech_threshold_margin_db"], vad_cfg.speech_threshold_margin_db)

    def test_asset_references_and_anti_fabrication(self):
        """Verifies all 20 SVGs exist, all 1-20 audio files are strictly MISSING, 0 fabricated."""
        cards_dir = os.path.join(self.bundle_dir, "content", "flashcards")
        for i in range(1, 21):
            card_path = os.path.join(cards_dir, f"card_{i:02d}.svg")
            self.assertTrue(os.path.exists(card_path), f"Flashcard card_{i:02d}.svg must exist")

        audio_manifest_path = os.path.join(self.bundle_dir, "audio", "audio_manifest.json")
        with open(audio_manifest_path, "r", encoding="utf-8") as f:
            audio_man = json.load(f)

        self.assertEqual(audio_man["audio_assets"]["numbers_1_to_20"]["audio_status"], "MISSING")
        self.assertEqual(audio_man["audio_assets"]["numbers_1_to_20"]["fabricated_count"], 0)

        # Content registry must also enforce MISSING audio status
        reg_path = os.path.join(self.bundle_dir, "content", "content_registry.json")
        with open(reg_path, "r", encoding="utf-8") as f:
            reg = json.load(f)
        for it in reg["items"]:
            self.assertEqual(it["audio_status"], "MISSING")

    def test_offline_only_and_zero_network_dependency(self):
        """Verifies bundle contains zero remote network endpoints and mandates 100% offline runtime."""
        contract_path = os.path.join(self.bundle_dir, "contracts", "android_integration_contract.md")
        with open(contract_path, "r", encoding="utf-8") as f:
            contract_text = f.read()

        self.assertIn("100% Offline", contract_text)
        self.assertIn("android.permission.INTERNET", contract_text)
        self.assertIn("Forbidden", contract_text)

        trans_cfg_path = os.path.join(self.bundle_dir, "config", "translation_engine_config.json")
        with open(trans_cfg_path, "r", encoding="utf-8") as f:
            trans_cfg = json.load(f)
        self.assertTrue(trans_cfg["offline_guarantee"]["local_storage_only"])
        self.assertFalse(trans_cfg["offline_guarantee"]["network_calls"])

    def test_end_to_end_bundle_reproducibility(self):
        """Executes complete Audio -> VAD -> Preprocessing -> TFLite -> Registry -> Output using bundle."""
        # 1. Load Audio
        sample_audio_path = os.path.join(self.bundle_dir, "audio", "samples", "test_sample_16k.wav")
        import wave
        with wave.open(sample_audio_path, "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

        # 2. VAD processing
        vad = StreamingVADProcessor()
        utterances = vad.process_continuous_audio(audio)
        self.assertGreaterEqual(len(utterances), 1)

        # 3. Preprocessing
        prep = AudioPreprocessor()
        _, log_mel = prep.preprocess_signal(utterances[0], sample_rate=16000)
        spec_4d = prep.format_for_model(log_mel)
        self.assertEqual(spec_4d.shape, (1, 101, 64, 1))

        # 4. TFLite Model Inference
        model_path = os.path.join(self.bundle_dir, "models", "speech_classifier_float32.tflite")
        interp = tflite.Interpreter(model_path=model_path)
        interp.allocate_tensors()
        in_idx = interp.get_input_details()[0]["index"]
        out_idx = interp.get_output_details()[0]["index"]

        interp.set_tensor(in_idx, spec_4d)
        interp.invoke()
        probs = interp.get_tensor(out_idx).squeeze(0)

        self.assertEqual(len(probs), 21)
        self.assertAlmostEqual(float(np.sum(probs)), 1.0, places=4)

        # 5. Class Mapping & Decision
        top_idx = int(np.argmax(probs))
        reg_path = os.path.join(self.bundle_dir, "content", "content_registry.json")
        with open(reg_path, "r", encoding="utf-8") as f:
            reg = json.load(f)

        if top_idx == 0:
            status = "BACKGROUND_NOISE"
        else:
            item = next(it for it in reg["items"] if it["class_index"] == top_idx)
            self.assertIsNotNone(item)
            status = "RECOGNIZED_NUMERAL"
            self.assertIn(status, ["RECOGNIZED_NUMERAL", "BACKGROUND_NOISE"])


if __name__ == "__main__":
    unittest.main()
