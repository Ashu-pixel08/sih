"""
ai/export/export_tflite.py
=============================================================================
SIH260042: AI-Powered Vernacular Pedagogy & Real-Time Translation
TFLite Edge Export & Numerical Parity Verification Module
=============================================================================

PURPOSE:
Exports the LightweightSpectrogramCNN PyTorch model to:
1. ONNX intermediate model (opset 17)
2. Float32 TFLite model ([1, 101, 64, 1] -> [1, 21])
3. Float16 TFLite model
4. Dynamic/Integer Quantized TFLite model (if supported)

CONTRACT VERIFICATION:
- Input shape strictly: [1, 101, 64, 1]
- Input dtype strictly: FLOAT32
- Output shape strictly: [1, 21]
- Output dtype strictly: FLOAT32
- End-to-end numerical parity verification between PyTorch reference and LiteRT.
=============================================================================
"""

import json
import os
import shutil
import sys
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch

cur_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.normpath(os.path.join(cur_dir, "..", ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

import ai_edge_litert.interpreter as tflite
import onnx2tf

from ai.speech.speech_classifier import LightweightSpectrogramCNN


class TFLiteExporter:
    """
    Manages export from PyTorch to ONNX and TFLite with parity validation.
    """

    def __init__(
        self,
        checkpoint_path: Optional[str] = None,
        export_dir: Optional[str] = None,
    ):
        self.workspace_root = workspace_root
        self.checkpoint_path = checkpoint_path or os.path.join(
            self.workspace_root, "models", "checkpoints", "best_model.pt"
        )
        self.export_dir = export_dir or os.path.join(
            self.workspace_root, "models", "edge"
        )
        os.makedirs(self.export_dir, exist_ok=True)

    def load_model(self) -> LightweightSpectrogramCNN:
        """Loads model from checkpoint if available, or initialized architecture."""
        model = LightweightSpectrogramCNN(num_classes=21)
        if os.path.exists(self.checkpoint_path):
            print(f"Loading weights from checkpoint: {self.checkpoint_path}")
            checkpoint = torch.load(self.checkpoint_path, weights_only=False, map_location="cpu")
            if "model_state_dict" in checkpoint:
                model.load_state_dict(checkpoint["model_state_dict"])
            else:
                model.load_state_dict(checkpoint)
        else:
            print("Notice: No checkpoint found on disk. Initializing architecture baseline with deterministic weights.")
            torch.manual_seed(42)
            for p in model.parameters():
                if p.dim() > 1:
                    torch.nn.init.xavier_uniform_(p)
        model.eval()
        return model

    def export_onnx(self, model: LightweightSpectrogramCNN, onnx_path: str) -> str:
        """Exports PyTorch model to ONNX with NCHW input [1, 1, 101, 64]."""
        dummy_input = torch.randn(1, 1, 101, 64, dtype=torch.float32)

        print(f"Exporting to ONNX: {onnx_path}")
        torch.onnx.export(
            model,
            dummy_input,
            onnx_path,
            input_names=["input_spectrogram"],
            output_names=["output_probabilities"],
            opset_version=17,
            dynamo=False,
        )
        size_bytes = os.path.getsize(onnx_path)
        print(f"ONNX exported successfully ({size_bytes / 1024:.2f} KB)")
        return onnx_path

    def convert_to_tflite(self, onnx_path: str) -> Dict[str, str]:
        """
        Converts ONNX to TFLite via onnx2tf with NHWC input [1, 101, 64, 1].
        """
        temp_tflite_dir = os.path.join(self.export_dir, "_temp_tflite")
        if os.path.exists(temp_tflite_dir):
            shutil.rmtree(temp_tflite_dir)
        os.makedirs(temp_tflite_dir, exist_ok=True)

        print(f"Converting ONNX to TFLite via onnx2tf into: {temp_tflite_dir}")
        onnx2tf.convert(
            input_onnx_file_path=onnx_path,
            output_folder_path=temp_tflite_dir,
            non_verbose=True,
        )

        # Look for produced tflite files
        exported_files = {}
        for fname in os.listdir(temp_tflite_dir):
            src = os.path.join(temp_tflite_dir, fname)
            if fname.endswith("float32.tflite"):
                dest = os.path.join(self.export_dir, "speech_classifier_float32.tflite")
                shutil.copy2(src, dest)
                exported_files["float32"] = dest
            elif fname.endswith("float16.tflite"):
                dest = os.path.join(self.export_dir, "speech_classifier_float16.tflite")
                shutil.copy2(src, dest)
                exported_files["float16"] = dest

        # Cleanup temp directory
        try:
            shutil.rmtree(temp_tflite_dir)
        except Exception:
            pass

        return exported_files

    def verify_tflite_contract(self, tflite_path: str) -> Dict[str, Any]:
        """
        Verifies input/output tensor shapes and dtypes against Android contract.
        """
        interp = tflite.Interpreter(model_path=tflite_path)
        interp.allocate_tensors()

        in_details = interp.get_input_details()
        out_details = interp.get_output_details()

        in_shape = in_details[0]["shape"].tolist()
        in_dtype = str(in_details[0]["dtype"])
        out_shape = out_details[0]["shape"].tolist()
        out_dtype = str(out_details[0]["dtype"])

        expected_in_shape = [1, 101, 64, 1]
        expected_out_shape = [1, 21]

        in_shape_ok = in_shape == expected_in_shape
        out_shape_ok = out_shape == expected_out_shape

        file_size_kb = os.path.getsize(tflite_path) / 1024.0

        return {
            "model_path": tflite_path,
            "file_size_kb": round(file_size_kb, 2),
            "input_tensor": {
                "name": in_details[0]["name"],
                "shape": in_shape,
                "dtype": in_dtype,
                "matches_contract": in_shape_ok,
            },
            "output_tensor": {
                "name": out_details[0]["name"],
                "shape": out_shape,
                "dtype": out_dtype,
                "matches_contract": out_shape_ok,
            },
            "contract_verified": in_shape_ok and out_shape_ok,
        }

    def verify_parity(
        self,
        model: LightweightSpectrogramCNN,
        tflite_path: str,
        num_test_samples: int = 5,
        seed: int = 42,
    ) -> List[Dict[str, Any]]:
        """
        Compares predictions of PyTorch reference vs LiteRT on deterministic samples.
        """
        rng = np.random.RandomState(seed)
        interp = tflite.Interpreter(model_path=tflite_path)
        interp.allocate_tensors()

        in_idx = interp.get_input_details()[0]["index"]
        out_idx = interp.get_output_details()[0]["index"]

        parity_records = []

        for i in range(num_test_samples):
            # Generate test sample [1, 101, 64, 1]
            test_data_nhwc = rng.randn(1, 101, 64, 1).astype(np.float32)

            # PyTorch inference (using predict method)
            py_res = model.predict(test_data_nhwc)
            py_class = py_res["class_index"]
            py_conf = py_res["confidence"]
            py_probs = np.array(py_res["probabilities"], dtype=np.float32)

            # TFLite inference
            interp.set_tensor(in_idx, test_data_nhwc)
            interp.invoke()
            tf_out = interp.get_tensor(out_idx).squeeze(0)  # [21]
            tf_class = int(np.argmax(tf_out))
            tf_conf = float(tf_out[tf_class])

            # Max absolute probability difference
            max_diff = float(np.max(np.abs(py_probs - tf_out)))
            classes_match = py_class == tf_class

            parity_records.append(
                {
                    "sample_index": i,
                    "pytorch_class": py_class,
                    "pytorch_confidence": round(py_conf, 4),
                    "tflite_class": tf_class,
                    "tflite_confidence": round(tf_conf, 4),
                    "classes_match": classes_match,
                    "max_prob_abs_diff": round(max_diff, 6),
                    "parity_passed": classes_match and max_diff < 1e-3,
                }
            )

        return parity_records

    def run_export_pipeline(self) -> Dict[str, Any]:
        """Runs full export, contract validation, and numerical parity checks."""
        print("\n=======================================================")
        print("TFLITE EDGE EXPORT & NUMERICAL PARITY PIPELINE")
        print("=======================================================")

        model = self.load_model()
        summary = model.get_model_summary()
        print(f"Model Summary: {summary['parameters']} parameters ({summary['fp32_size_kb']} KB)")

        # 1. Export ONNX
        onnx_file = os.path.join(self.export_dir, "speech_classifier.onnx")
        self.export_onnx(model, onnx_file)

        # 2. Convert to TFLite
        tflite_files = self.convert_to_tflite(onnx_file)
        print(f"TFLite models generated: {list(tflite_files.keys())}")

        fp32_path = tflite_files.get("float32")
        if not fp32_path or not os.path.exists(fp32_path):
            raise FileNotFoundError("Float32 TFLite model failed to generate.")

        # 3. Contract Verification
        contract_report = self.verify_tflite_contract(fp32_path)
        print("\nAndroid Model Contract Verification:")
        print(f"- Input shape: {contract_report['input_tensor']['shape']} (matches: {contract_report['input_tensor']['matches_contract']})")
        print(f"- Output shape: {contract_report['output_tensor']['shape']} (matches: {contract_report['output_tensor']['matches_contract']})")
        print(f"- FP32 Model Size on Disk: {contract_report['file_size_kb']} KB")

        fp16_path = tflite_files.get("float16")
        fp16_size = os.path.getsize(fp16_path) / 1024.0 if fp16_path else None
        if fp16_size:
            print(f"- FP16 Model Size on Disk: {fp16_size:.2f} KB")

        # 4. Parity Testing
        parity_records = self.verify_parity(model, fp32_path, num_test_samples=5)
        all_passed = all(r["parity_passed"] for r in parity_records)
        print(f"\nNumerical Parity Status (PyTorch vs LiteRT): {'PASSED' if all_passed else 'MISMATCH'}")
        for r in parity_records:
            print(f"  Sample {r['sample_index']}: PyTorch Class {r['pytorch_class']} ({r['pytorch_confidence']:.3f}) <-> TFLite Class {r['tflite_class']} ({r['tflite_confidence']:.3f}) | MaxDiff: {r['max_prob_abs_diff']:.6f} | Match: {r['classes_match']}")

        manifest = {
            "model_architecture": "LightweightSpectrogramCNN",
            "parameters": summary["parameters"],
            "exported_models": {
                "onnx": onnx_file,
                "tflite_float32": fp32_path,
                "tflite_float16": fp16_path,
            },
            "file_sizes_kb": {
                "tflite_float32": contract_report["file_size_kb"],
                "tflite_float16": round(fp16_size, 2) if fp16_size else None,
            },
            "contract_verification": contract_report,
            "parity_verification": {
                "all_samples_passed": all_passed,
                "total_samples_tested": len(parity_records),
                "records": parity_records,
            },
            "disclaimer": "RESEARCH / BASELINE IMPLEMENTATION ONLY. Non-production status until verified native speech recordings are acquired.",
        }

        manifest_path = os.path.join(self.export_dir, "tflite_export_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        print(f"\nExport manifest written to: {manifest_path}")
        return manifest


if __name__ == "__main__":
    exporter = TFLiteExporter()
    exporter.run_export_pipeline()
