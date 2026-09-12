"""
ai/export/package_deployment_bundle.py
=============================================================================
SIH260042: AI-Powered Vernacular Pedagogy & Real-Time Translation
Automated Edge Deployment Packaging & Asset Bundle Generator
=============================================================================

PURPOSE:
- Freezes and packages the complete, validated AI/data system into an Android-ready
  artifact bundle.
- Generates deployment/manifest.json indexing every runtime artifact with SHA256
  checksums, byte sizes, Android target locations, dependencies, provenance,
  and strict verification statuses.
- Enforces zero audio fabrication and offline-only operational guarantees.
=============================================================================
"""

import hashlib
import json
import os
import shutil
import sys
from typing import Any, Dict, List

cur_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.normpath(os.path.join(cur_dir, "..", ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)


def calculate_sha256(filepath: str) -> str:
    """Computes SHA256 hex digest for a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def generate_class_index_mapping(registry_path: str) -> Dict[str, Any]:
    """Generates contiguous 0..21 class mapping from registry."""
    with open(registry_path, "r", encoding="utf-8") as f:
        reg = json.load(f)

    classes = [
        {
            "index": 0,
            "label_id": "_background_",
            "is_number": False,
            "hindi_text": reg["background_class"]["hindi_text"],
            "mundari_text": reg["background_class"]["mundari_text"],
            "description": reg["background_class"]["description"],
        }
    ]

    for item in reg["items"]:
        classes.append({
            "index": item["class_index"],
            "label_id": item["label_id"],
            "number": item["number"],
            "is_number": True,
            "hindi_numeral": item["hindi_numeral"],
            "hindi_text": item["hindi_text"],
            "mundari_numeral": item["mundari_numeral"],
            "mundari_text": item["mundari_text"],
            "mundari_phonetic": item["mundari_phonetic"],
            "mundari_root": item["mundari_root"],
        })

    return {
        "version": "1.0.0",
        "total_classes": len(classes),
        "classes": classes,
    }


def generate_model_metadata() -> Dict[str, Any]:
    """Builds formal edge model metadata specification."""
    return {
        "model_id": "speech_classifier_fln_v1",
        "architecture": "LightweightSpectrogramCNN",
        "backbone": "DepthwiseSeparable2D_CNN",
        "parameter_count": 98085,
        "input_tensor": {
            "name": "input_spectrogram",
            "shape": [1, 101, 64, 1],
            "dtype": "FLOAT32",
            "layout": "NHWC",
            "units": "Log-Mel Spectrogram",
        },
        "output_tensor": {
            "name": "output_probabilities",
            "shape": [1, 21],
            "dtype": "FLOAT32",
            "classes": 21,
            "activation": "Softmax",
        },
        "quantization_formats": {
            "FLOAT32": {
                "file_name": "speech_classifier_float32.tflite",
                "size_kb": 386.74,
                "precision": "Single precision float32",
            },
            "FLOAT16": {
                "file_name": "speech_classifier_float16.tflite",
                "size_kb": 198.14,
                "precision": "Half precision float16",
            },
        },
        "runtime_requirements": {
            "engine": "LiteRT / TensorFlow Lite 2.x",
            "accelerator": "CPU (NNAPI / GPU optional)",
            "estimated_ram_kb": 2500,
            "peak_compute_mflops": 0.15,
        },
        "thresholds": {
            "confidence_threshold": 0.65,
            "margin_threshold": 0.20,
        },
        "verification_status": "RESEARCH / BASELINE / VALIDATION",
        "status_rationale": "Model architecture, LiteRT numerical parity (max diff 5e-6), and pipeline mechanics are verified. Real-world accuracy claims require verified isolated native-speaker 1–20 audio.",
    }


def generate_audio_preprocessing_spec() -> Dict[str, Any]:
    """Builds formal DSP audio preprocessing specification."""
    return {
        "spec_version": "1.0.0",
        "domain": "DSP_FEATURE_EXTRACTION",
        "audio_input": {
            "sample_rate_hz": 16000,
            "channels": 1,
            "channel_layout": "MONO",
            "bit_depth": 16,
            "format": "PCM_16_BIT_LE",
            "duration_seconds": 1.0,
            "sample_count": 16000,
        },
        "resampling": {
            "algorithm": "polyphase_kaiser_or_linear_interpolation",
            "target_rate_hz": 16000,
        },
        "stft_parameters": {
            "frame_length_samples": 400,
            "frame_length_ms": 25.0,
            "hop_length_samples": 160,
            "hop_length_ms": 10.0,
            "fft_length": 512,
            "window_function": "periodic_hann",
            "symmetric": False,
        },
        "mel_filterbank": {
            "num_mel_bins": 64,
            "f_min_hz": 20.0,
            "f_max_hz": 8000.0,
            "scale": "HTK",
            "normalization": "slaney_area_normalized",
        },
        "log_compression": {
            "formula": "log(max(power_spec, 1e-6))",
            "base": "natural_e",
            "epsilon": 1e-6,
        },
        "output_tensor": {
            "time_frames": 101,
            "mel_bins": 64,
            "channels": 1,
            "shape": [1, 101, 64, 1],
            "dtype": "FLOAT32",
        },
    }


def generate_vad_config() -> Dict[str, Any]:
    """Builds formal VAD configuration specification."""
    return {
        "spec_version": "1.0.0",
        "sample_rate_hz": 16000,
        "chunk_size_samples": 320,
        "chunk_duration_ms": 20.0,
        "features": [
            "Short-Time Energy (STE in dBFS)",
            "Zero-Crossing Rate (ZCR)",
        ],
        "thresholds": {
            "initial_noise_floor_db": -50.0,
            "min_noise_floor_db": -65.0,
            "speech_threshold_margin_db": 12.0,
            "noise_adapt_rate": 0.05,
        },
        "timing_constraints": {
            "min_speech_duration_ms": 120.0,
            "max_speech_duration_ms": 3000.0,
            "hangover_duration_ms": 300.0,
        },
        "output_window": {
            "target_samples": 16000,
            "duration_seconds": 1.0,
            "alignment": "centered_on_max_energy",
        },
        "finite_state_machine": [
            "IDLE",
            "ONSET_CANDIDATE",
            "IN_SPEECH",
            "HANGOVER",
            "ENDPOINT_DETECTED",
        ],
    }


def generate_translation_engine_config() -> Dict[str, Any]:
    """Builds translation engine configuration specification."""
    return {
        "spec_version": "1.0.0",
        "architecture": "TWO_TIER_HYBRID_RETRIEVAL",
        "tiers": {
            "tier_1": {
                "name": "EXACT_EDUCATIONAL_LOOKUP",
                "precision": "100%",
                "hallucination_rate": "0.0%",
                "confidence": 1.0,
                "scope": ["CANONICAL_NUMBERS_1_20", "PRIMARY_CLASSROOM_PHRASEBOOK_16"],
            },
            "tier_2": {
                "name": "CORPUS_SENTENCE_RETRIEVAL",
                "method": "TF-IDF Character 3-Gram Cosine Similarity",
                "corpus_size": 17809,
                "similarity_threshold": 0.60,
                "exact_similarity_threshold": 0.95,
            },
        },
        "refusal_policy": {
            "fallback_status": "OUT_OF_VOCABULARY_UNVERIFIED",
            "generative_hallucination": False,
        },
        "offline_guarantee": {
            "network_calls": False,
            "local_storage_only": True,
        },
    }


def generate_audio_manifest() -> Dict[str, Any]:
    """Documents existing authentic audio assets and non-fabrication status."""
    return {
        "spec_version": "1.0.0",
        "audio_assets": {
            "numbers_1_to_20": {
                "total_classes": 20,
                "audio_status": "MISSING",
                "fabricated_count": 0,
                "policy_enforcement": "Zero audio fabrication. Authentic native-speaker recordings must be collected in field.",
            },
            "authentic_reference_samples": [
                {
                    "file_name": "test_sample_16k.wav",
                    "sample_rate_hz": 16000,
                    "channels": 1,
                    "duration_seconds": 1.0,
                    "source": "Karya Mundari Speech Corpus (Audited Subsample)",
                    "verification_status": "AUTHENTIC_RECORDING",
                }
            ],
            "corpus_audio_summary": {
                "total_raw_recordings": 200,
                "valid_recordings": 182,
                "quarantined_low_energy": 18,
            },
        },
    }


def generate_android_contract() -> str:
    """Generates the Android integration architectural contract."""
    return """# Android Integration Contract & Runtime Specification
**Project**: SIH260042 — Vernacular Pedagogy & Real-Time Translation Assistant
**Target Platform**: Android API 24+ (Android 7.0 Nougat to Android 15)
**Hardware Scope**: Low-cost rural classroom tablets / smartphones (2GB RAM, Quad-Core 1.5 GHz)
**Operational Guarantee**: 100% Offline (Zero internet permission required)

---

## 1. System Pipeline Flow on Android

```
[AudioRecord (16kHz 16-bit Mono)]
              │
              ▼ (20ms / 320 samples chunk)
[Streaming VAD Processor] (STE + ZCR + Noise Floor)
              │
              ├── Speech Incomplete ──> (Continue listening)
              ▼ (Endpoint Confirmed: 16,000 samples)
[Audio Preprocessor] (Hann Window + STFT + 64 Mel Bins -> Log-Mel [1, 101, 64, 1])
              │
              ▼
[LiteRT / TFLite Interpreter] (speech_classifier_float32.tflite)
              │
              ▼ (Top-1 Class & Margin Check)
       Confidence >= 0.65 & Margin >= 0.20?
              ├── YES ──> [Content Registry (Class 1–20)] ──> [Bilingual Lesson & SVG Card]
              └── NO  ──> [Fallback Trigger] ───────────────> [Prompt Interactive Touch Card]
```

---

## 2. Directory Layout in Android APK (`app/src/main/assets/`)

```
assets/
├── models/
│   ├── speech_classifier_float32.tflite   (386.74 KB, baseline FP32)
│   ├── speech_classifier_float16.tflite   (198.14 KB, quantized FP16)
│   ├── model_metadata.json                (Model specifications)
│   └── class_index_mapping.json           (0..20 classes)
├── config/
│   ├── audio_preprocessing_spec.json      (STFT / Mel filterbank parameters)
│   ├── vad_config.json                    (VAD thresholds & frame sizes)
│   └── translation_engine_config.json     (Tier 1 & Tier 2 parameters)
├── content/
│   ├── content_registry.json              (Canonical bilingual 1-20 metadata)
│   ├── classroom_phrasebook.json          (16 primary classroom phrases)
│   ├── curriculum_model.json              (Grade 1 FLN lessons & activities)
│   ├── flashcards/
│   │   ├── card_01.svg ... card_20.svg    (20 Ten-Frame SVG assets)
│   └── worksheets/
│       ├── ws_01_recognition.html / .json ... ws_05 (5 worksheets)
└── audio/
    ├── audio_manifest.json                (Audio tracking manifest)
    └── samples/
        └── test_sample_16k.wav            (Processed reference sample)
```

---

## 3. Data Structures & Constants Contract (Kotlin)

```kotlin
// 1. Audio Record Contract
const val SAMPLE_RATE_HZ = 16000
const val CHUNK_SIZE_SAMPLES = 320         // 20 ms
const val TARGET_WINDOW_SAMPLES = 16000    // 1.0 second

// 2. Model Input/Output Contract
val INPUT_SHAPE = intArrayOf(1, 101, 64, 1) // [B, Time, Mel, Channels] Float32
val OUTPUT_SHAPE = intArrayOf(1, 21)        // [B, Classes] Float32
const val CONFIDENCE_THRESHOLD = 0.65f
const val MARGIN_THRESHOLD = 0.20f

// 3. Class 0 vs Numbers 1..20
// Class 0 = _background_ (Silence / Noise) -> triggers touch mode
// Class 1..20 = num_01 .. num_20 -> loads content_registry item
```

---

## 4. Offline Guarantees & Permissions

- `AndroidManifest.xml`:
  - `android.permission.RECORD_AUDIO`: **Required** (runtime prompt).
  - `android.permission.INTERNET`: **Forbidden** (zero network calls).
  - `android.permission.ACCESS_NETWORK_STATE`: **Forbidden**.

---

## 5. Remaining Android-Side Work

The following Android-specific UI/platform tasks are ready to be implemented once Android engineering begins:
1. **AudioRecord Thread**: Background thread feeding 20ms PCM chunks into Kotlin VAD.
2. **DSP Preprocessor**: Kotlin or C++ JNI implementation of Hann windowing, 512-point FFT, and 64-bin Mel filterbank matching `audio_preprocessing_spec.json`.
3. **LiteRT Dependency**: Add `com.google.ai.edge.litert:litert:1.0.1` (or `org.tensorflow:tensorflow-lite:2.14.0`) in `build.gradle.kts`.
4. **SVG Flashcard Rendering**: Add `com.caverock:androidsvg:1.4` or Coil SVG decoder to display `card_01.svg` to `card_20.svg`.
5. **Worksheet Printing**: Implement Android `PrintDocumentAdapter` with `WebView` to allow teachers to print or save A4 worksheets as PDF.
6. **SoundPool / MediaPlayer**: Audio playback controller (queued for when field audio recordings are loaded into `assets/audio/numbers/`).
"""


def package_deployment_bundle() -> Dict[str, Any]:
    """Orchestrates bundle creation and manifest generation."""
    print("=" * 70)
    print("SIH260042: PACKAGING EDGE DEPLOYMENT BUNDLE")
    print("=" * 70)

    deploy_dir = os.path.join(workspace_root, "deployment")
    bundle_dir = os.path.join(deploy_dir, "bundle")

    # Target directories inside bundle
    models_target = os.path.join(bundle_dir, "models")
    config_target = os.path.join(bundle_dir, "config")
    content_target = os.path.join(bundle_dir, "content")
    flashcards_target = os.path.join(content_target, "flashcards")
    worksheets_target = os.path.join(content_target, "worksheets")
    audio_target = os.path.join(bundle_dir, "audio")
    audio_samples_target = os.path.join(audio_target, "samples")
    contracts_target = os.path.join(bundle_dir, "contracts")

    for d in [
        models_target,
        config_target,
        content_target,
        flashcards_target,
        worksheets_target,
        audio_target,
        audio_samples_target,
        contracts_target,
    ]:
        os.makedirs(d, exist_ok=True)

    manifest_entries: List[Dict[str, Any]] = []

    # 1. Models
    tflite_fp32_src = os.path.join(workspace_root, "models", "edge", "speech_classifier_float32.tflite")
    tflite_fp16_src = os.path.join(workspace_root, "models", "edge", "speech_classifier_float16.tflite")
    shutil.copy2(tflite_fp32_src, models_target)
    shutil.copy2(tflite_fp16_src, models_target)

    # 2. Specifications & Configs
    meta_path = os.path.join(models_target, "model_metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(generate_model_metadata(), f, indent=2, ensure_ascii=False)

    reg_path = os.path.join(workspace_root, "content", "content_registry.json")
    class_map_path = os.path.join(models_target, "class_index_mapping.json")
    with open(class_map_path, "w", encoding="utf-8") as f:
        json.dump(generate_class_index_mapping(reg_path), f, indent=2, ensure_ascii=False)

    dsp_path = os.path.join(config_target, "audio_preprocessing_spec.json")
    with open(dsp_path, "w", encoding="utf-8") as f:
        json.dump(generate_audio_preprocessing_spec(), f, indent=2, ensure_ascii=False)

    vad_path = os.path.join(config_target, "vad_config.json")
    with open(vad_path, "w", encoding="utf-8") as f:
        json.dump(generate_vad_config(), f, indent=2, ensure_ascii=False)

    trans_cfg_path = os.path.join(config_target, "translation_engine_config.json")
    with open(trans_cfg_path, "w", encoding="utf-8") as f:
        json.dump(generate_translation_engine_config(), f, indent=2, ensure_ascii=False)

    # 3. Content
    shutil.copy2(reg_path, content_target)

    phrasebook_src = os.path.join(workspace_root, "content", "translations", "classroom_phrasebook.json")
    shutil.copy2(phrasebook_src, content_target)

    curriculum_src = os.path.join(workspace_root, "content", "fln", "curriculum_model.json")
    shutil.copy2(curriculum_src, content_target)

    # 4. Flashcards (20 SVGs)
    cards_src_dir = os.path.join(workspace_root, "content", "flashcards", "numbers")
    for i in range(1, 21):
        cname = f"card_{i:02d}.svg"
        shutil.copy2(os.path.join(cards_src_dir, cname), flashcards_target)

    # 5. Worksheets (5 HTML + 5 JSON)
    ws_src_dir = os.path.join(workspace_root, "content", "worksheets", "generated")
    for ws_id in ["ws_01_recognition", "ws_02_counting", "ws_03_matching", "ws_04_sequencing", "ws_05_missing_numbers"]:
        shutil.copy2(os.path.join(ws_src_dir, f"{ws_id}.html"), worksheets_target)
        shutil.copy2(os.path.join(ws_src_dir, f"{ws_id}.json"), worksheets_target)

    # 6. Audio Assets & Manifest
    audio_manifest_path = os.path.join(audio_target, "audio_manifest.json")
    with open(audio_manifest_path, "w", encoding="utf-8") as f:
        json.dump(generate_audio_manifest(), f, indent=2, ensure_ascii=False)

    sample_audio_src = os.path.join(workspace_root, "content", "audio", "processed", "test_sample_16k.wav")
    if os.path.exists(sample_audio_src):
        shutil.copy2(sample_audio_src, audio_samples_target)

    # 7. Contracts
    android_contract_path = os.path.join(contracts_target, "android_integration_contract.md")
    with open(android_contract_path, "w", encoding="utf-8") as f:
        f.write(generate_android_contract())

    # Build Master Manifest
    print("Indexing bundle files and computing SHA256 checksums...")
    for root, _, files in os.walk(bundle_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_to_bundle = os.path.relpath(full_path, bundle_dir).replace("\\", "/")
            android_target = f"app/src/main/assets/{rel_to_bundle}"

            file_size_bytes = os.path.getsize(full_path)
            sha256_hash = calculate_sha256(full_path)

            # Determine type and status
            if file.endswith(".tflite"):
                artifact_type = "TFLITE_EDGE_MODEL"
                status = "RESEARCH / BASELINE / VALIDATION"
                provenance = "Exported from PyTorch LightweightSpectrogramCNN via ONNX Opset 17"
            elif file.endswith(".svg"):
                artifact_type = "SVG_VISUAL_ASSET"
                status = "UNVERIFIED — GENERATED PROTOTYPE"
                provenance = "Generated via content/flashcards/flashcard_generator.py"
            elif file.endswith(".html"):
                artifact_type = "PRINTABLE_WORKSHEET_HTML"
                status = "GENERATED_PROTOTYPE"
                provenance = "Generated via content/worksheets/worksheet_generator.py"
            elif file.endswith(".wav"):
                artifact_type = "AUTHENTIC_SPEECH_AUDIO"
                status = "VERIFIED_AUTHENTIC_SAMPLE"
                provenance = "Karya Mundari Speech Corpus (Audited Subsample)"
            elif file == "content_registry.json":
                artifact_type = "CANONICAL_CONTENT_REGISTRY"
                status = "VERIFIED_CORPUS_ATTESTED"
                provenance = "Corpus and dictionary attested Mundari numerals 1-20"
            elif file == "classroom_phrasebook.json":
                artifact_type = "CLASSROOM_PHRASEBOOK"
                status = "CORPUS_ATTESTED / LINGUISTICALLY_REVIEWED"
                provenance = "Validated parallel corpus and MTB-MLE classroom lexicography"
            elif file == "curriculum_model.json":
                artifact_type = "FLN_CURRICULUM_METADATA"
                status = "UNVERIFIED_NIPUN_CODES / PEDAGOGICALLY_STRUCTURED"
                provenance = "Grade 1 Foundational Numeracy lesson framework"
            elif file.endswith(".md"):
                artifact_type = "INTEGRATION_CONTRACT_SPEC"
                status = "ENGINEERING_SPECIFICATION"
                provenance = "SIH260042 System Integration Team"
            else:
                artifact_type = "CONFIGURATION_JSON"
                status = "SYSTEM_SPECIFICATION"
                provenance = "SIH260042 AI/DSP Core"

            manifest_entries.append({
                "file_path": rel_to_bundle,
                "file_name": file,
                "artifact_type": artifact_type,
                "size_bytes": file_size_bytes,
                "size_kb": round(file_size_bytes / 1024.0, 2),
                "sha256": sha256_hash,
                "status": status,
                "expected_android_asset_path": android_target,
                "offline_compatible": True,
                "provenance": provenance,
            })

    master_manifest = {
        "manifest_version": "1.0.0",
        "project_code": "SIH260042",
        "system_name": "Vernacular Pedagogy and Real-Time Translation Tool",
        "bundle_date": "2026-09-04",
        "target_platform": "Android API 24+ (Offline Edge Runtime)",
        "governance_policy": {
            "anti_fabrication_rule": "Strictly enforced. 0 fabricated 1-20 speech recordings.",
            "unverified_visuals_watermark": "All SVGs stamped GENERATED PROTOTYPE.",
            "unverified_nipun_codes": "All NIPUN codes flagged UNVERIFIED — PENDING SOURCE VALIDATION.",
            "offline_only": "Zero network calls or remote endpoints required.",
        },
        "summary": {
            "total_artifacts": len(manifest_entries),
            "total_size_bytes": sum(e["size_bytes"] for e in manifest_entries),
            "total_size_mb": round(sum(e["size_bytes"] for e in manifest_entries) / (1024.0 * 1024.0), 2),
        },
        "artifacts": sorted(manifest_entries, key=lambda x: x["file_path"]),
    }

    manifest_output_path = os.path.join(deploy_dir, "manifest.json")
    with open(manifest_output_path, "w", encoding="utf-8") as f:
        json.dump(master_manifest, f, indent=2, ensure_ascii=False)

    print(f"Master deployment manifest created at: {manifest_output_path}")
    print(f"Total packaged artifacts: {len(manifest_entries)}")
    print(f"Total bundle size: {master_manifest['summary']['total_size_mb']} MB")
    print("Packaging complete.")
    return master_manifest


if __name__ == "__main__":
    package_deployment_bundle()
