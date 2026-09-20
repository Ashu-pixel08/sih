# Model Inventory & Verification Manifest

This manifest documents all production, exported, and edge machine learning artifacts in the **Vernacular FLN Assistant** (`sih`) repository, including parameter counts, architectural configurations, checksums, and Git LFS tracking policies.

---

## 1. Production Model Manifest

### `models/nmt/final/best_transformer.pt`
* **Model Identifier**: `cand_a_transformer_bpe_fln_v1`
* **Model Name**: Candidate A (Refined BPE Seq2Seq Transformer)
* **Status**: `PROMOTED_PRODUCTION_MODEL`
* **Promotion Date**: 2026-09-17
* **Architecture**: Sequence-to-Sequence Transformer Encoder-Decoder
  * Embedding Dimension ($d_{\text{model}}$): 256
  * Feed-Forward Dimension ($d_{\text{ff}}$): 512
  * Attention Heads ($n_{\text{head}}$): 4
  * Encoder Layers: 3
  * Decoder Layers: 3
  * Dropout: 0.10
  * Positional Encodings: Sinusoidal
* **Total Parameters**: **9,725,760**
* **File Size**: **115,781,300 bytes (110.42 MB)**
* **SHA-256 Checksum**:
  ```
  40ed8c77dfa7c4664644a94d375ebd276886249f996d6006475cfd1f2e17a54a
  ```
* **Storage Protocol**: **Git Large File Storage (Git LFS)**

---

## 2. Exported Edge & TorchScript Models

### `models/nmt/exported/hindi_mundari_nmt.torchscript.pt`
* **Format**: TorchScript JIT Graph
* **File Size**: 39,054,558 bytes (~39.05 MB)
* **Purpose**: Embedded and mobile execution without full Python/PyTorch runtime dependencies.
* **Target Runtime**: Android C++ / Java PyTorch Mobile wrapper.

---

## 3. Tokenizer Artifacts

| Path | Vocabulary Size | Script / Language | Subword Algorithm |
|---|---|---|---|
| `models/nmt/tokenizer/hindi_bpe.json` | 6,000 | Devanagari (Hindi) | Hugging Face BPE |
| `models/nmt/tokenizer/mundari_bpe.json` | 8,000 | Devanagari (Mundari) | Hugging Face BPE |

Both tokenizers were audited against the combined curriculum dataset and held-out test splits, achieving **0.0% unknown token (<unk>) rate**.

---

## 4. Edge Acoustic & Speech Models

| Path | Format | Size | Purpose |
|---|---|---|---|
| `models/edge/speech_vad.tflite` | TensorFlow Lite | 1.8 MB | On-device Voice Activity Detection (VAD) |
| `models/edge/speech_classifier.onnx` | ONNX | 4.2 MB | Multi-class acoustic keyword spotting |

---

## 5. Git LFS Tracking & Verification Policy

GitHub enforces a strict **100 MB hard file size limit** on direct Git commits. The production model (`best_transformer.pt`) is **110.42 MB**, requiring Git LFS.

### `.gitattributes` Configuration:
```gitattributes
models/nmt/final/*.pt filter=lfs diff=lfs merge=lfs -text
*.pt filter=lfs diff=lfs merge=lfs -text
```

### Verification Commands:
```bash
# Verify Git LFS is active
git lfs status

# Confirm real binary file size (not pointer text)
# On Windows PowerShell:
(Get-Item models/nmt/final/best_transformer.pt).Length
# Should return 115781300

# On Linux / macOS:
ls -lh models/nmt/final/best_transformer.pt
# Should return ~111M
```

> [!NOTE]
> When cloning on a new machine, execute `git lfs pull` to populate binary weights from LFS remote storage.
