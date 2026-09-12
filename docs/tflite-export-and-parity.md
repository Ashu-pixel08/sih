# TFLite Edge Export & Numerical Parity Verification Report

**Pipeline Component**: Edge Model Export & Cross-Platform Parity  
**Model**: `LightweightSpectrogramCNN`  
**Execution Runtime**: Google LiteRT (`ai_edge_litert` 2.1.2 / 2.2.0)  
**Status**: `RESEARCH / BASELINE IMPLEMENTATION / EXPORT VALIDATED`

---

## 1. Export Pipeline Overview

The export workflow converts the PyTorch neural network into an edge-optimized TFLite FlatBuffer ready for Android embedding:

$$\text{PyTorch (.pt)} \xrightarrow[\text{opset 17}]{\text{torch.onnx.export}} \text{ONNX (.onnx)} \xrightarrow[\text{flatbuffer\_direct}]{\text{onnx2tf}} \text{TFLite (.tflite)}$$

- **Static Dimension Optimization**: Static Average Pooling (`13x8`) prevents dynamic loop lowering, producing clean, direct execution subgraphs in TFLite.
- **Layout Adaptation**: PyTorch NCHW (`[1, 1, 101, 64]`) is automatically transposed to Android contract NHWC (`[1, 101, 64, 1]`) by the lowering pass.

---

## 2. Generated Edge Model Artifacts

| Artifact Name | File Path | Format | Precision | File Size on Disk |
| :--- | :--- | :---: | :---: | :---: |
| **Intermediate ONNX** | `models/edge/speech_classifier.onnx` | ONNX | FP32 | **387.73 KB** |
| **Primary TFLite Edge Model** | `models/edge/speech_classifier_float32.tflite` | FlatBuffer | FP32 | **386.74 KB** |
| **Compressed TFLite Edge Model** | `models/edge/speech_classifier_float16.tflite` | FlatBuffer | FP16 | **198.14 KB** |

---

## 3. Android Model Contract Verification

Verified via `ai/export/export_tflite.py` and automated test `test_tflite_contract_and_model_size`:

| Contract Attribute | Specification in `android-model-contract.md` | Measured in Exported `.tflite` | Status |
| :--- | :---: | :---: | :---: |
| **Input Tensor Name** | `input_spectrogram` | `input_spectrogram` | `VERIFIED` |
| **Input Shape** | `[1, 101, 64, 1]` | `[1, 101, 64, 1]` | `VERIFIED` |
| **Input Dtype** | `FLOAT32` (`numpy.float32`) | `FLOAT32` | `VERIFIED` |
| **Output Tensor Name** | `output_probabilities` | `output_probabilities` | `VERIFIED` |
| **Output Shape** | `[1, 21]` | `[1, 21]` | `VERIFIED` |
| **Output Dtype** | `FLOAT32` (`numpy.float32`) | `FLOAT32` | `VERIFIED` |
| **Activation Function** | Softmax ($\sum p_i = 1.0$) | Softmax ($\sum p_i = 1.0$) | `VERIFIED` |
| **Maximum File Size** | < 1,500 KB | **386.74 KB** | `VERIFIED` |

---

## 4. Golden Parity Test Results: PyTorch Reference vs. LiteRT

We evaluated deterministic test samples through both the PyTorch reference model and the LiteRT `.tflite` interpreter:

| Sample Index | PyTorch Predicted Class | PyTorch Confidence | LiteRT Predicted Class | LiteRT Confidence | Max Absolute Difference | Class Match | Status |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0** | Class 19 | 0.0621 | Class 19 | 0.0621 | **0.000005** | **MATCH** | `PASSED` |
| **1** | Class 6 | 0.0827 | Class 6 | 0.0827 | **0.000005** | **MATCH** | `PASSED` |
| **2** | Class 6 | 0.0734 | Class 6 | 0.0734 | **0.000005** | **MATCH** | `PASSED` |
| **3** | Class 6 | 0.0662 | Class 6 | 0.0662 | **0.000005** | **MATCH** | `PASSED` |
| **4** | Class 6 | 0.0849 | Class 6 | 0.0849 | **0.000005** | **MATCH** | `PASSED` |

- **Numerical Precision**: Maximum probability error across all 21 classes is $5 \times 10^{-6}$ (far below the $1 \times 10^{-4}$ tolerance).
- **Label Consistency**: 100% agreement between Python development model and edge runtime.

---

## 5. Performance Attribution & Benchmarking Disclaimer

> [!CAUTION]
> **Performance Reporting Policy**:
> The performance numbers below represent **BENCHMARK / ESTIMATE / MODEL-LEVEL TEST** under desktop/host CPU simulation.
> They MUST NOT be labeled as **REAL ANDROID END-TO-END PERFORMANCE** until measured on physical target Android hardware (e.g. Samsung Galaxy Tab A7 Lite / Lenovo Tab M8).

| Stage | Metric Type | Benchmark / Estimated Value | Real Android Hardware Target |
| :--- | :--- | :---: | :---: |
| **Audio Capture** | I/O Latency | *N/A (hardware dependent)* | < 20 ms (AudioRecord buffer) |
| **Audio Preprocessing** | CPU Latency | 1.19 ms | < 5.0 ms |
| **TFLite Inference** | CPU Latency | 0.02 ms (Host CPU) | < 10.0 ms (ARM CPU) |
| **Total Mic-to-Result** | Pipeline Latency | **~1.21 ms (Model-level test)** | **< 35.0 ms** |
| **RAM Footprint** | Memory Allocation | **< 10.0 MB** | **< 15.0 MB** |
| **Model Size on Disk** | Storage | **386.74 KB** | **386.74 KB** |
