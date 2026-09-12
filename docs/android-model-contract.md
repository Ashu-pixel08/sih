# Android Model & Preprocessing Contract

## 1. Specification Overview
This contract defines the exact interface and preprocessing pipeline between the AI/ML speech and translation components and the Android mobile client application (targeting low-cost Android tablets with ~2 GB RAM). 

The Android application (Kotlin) and the Python AI pipeline **MUST adhere to identical preprocessing logic** down to floating-point tolerances.

---

## 2. Audio Capture & Preprocessing Contract

| Parameter | Specification | Note / Verification |
| :--- | :--- | :--- |
| **Audio Source** | Built-in Microphone / Classroom Mic | Handled via Android `AudioRecord` |
| **Target Sample Rate** | **16,000 Hz (16 kHz)** | Standard FLN speech processing |
| **Channel Count** | **1 (Mono)** | Single-channel capture |
| **Audio Encoding / Format** | **Linear PCM 16-bit** | Converted to Float32 `[-1.0, 1.0]` |
| **Capture Window Duration** | **1.00 second** (Fixed window) | 16,000 samples exactly |
| **Window Type** | Hann Window | Size = 400 samples (25 ms) |
| **FFT Size (`n_fft`)** | 512 | Zero-padded from 400 |
| **Hop Length (`hop_length`)** | 160 samples (10 ms) | 50% overlap |
| **Mel Filterbank Bins** | **64 bins** | Spanning 20 Hz to 8,000 Hz |
| **Log Compression** | `log(mel + 1e-6)` | Natural log of power spectrogram |
| **Spectrogram Output Shape**| `[1, 101, 64, 1]` | `[Batch, TimeFrames, MelBins, Channels]` |
| **Tensor Dtype** | `FLOAT32` (or `INT8` quantized for edge) | Standard TFLite tensor |

---

## 3. TFLite Model Specifications

### 3.1 Speech Recognition Model (Vocabulary Classifier)
- **Model Filename**: `speech_model.tflite`
- **Model Type**: Lightweight 2D Convolutional Neural Network (MobileNetV3-Small / SqueezeNet backbone adapted for 1D/2D audio spectrograms)
- **Target Size**: `< 4.5 MB` (Unquantized FP32) / `< 1.5 MB` (INT8 Quantized)
- **Input Tensor**:
  - Name: `input_spectrogram`
  - Shape: `[1, 101, 64, 1]`
  - Dtype: `kTfLiteFloat32`
- **Output Tensor**:
  - Name: `output_probabilities`
  - Shape: `[1, 21]` (Classes 0 through 20)
  - Dtype: `kTfLiteFloat32`
  - Activation: Softmax (probabilities summing to 1.0)

---

## 4. Class Ordering & Index Mapping

The class indices must be identical across the Python data pipeline, model training, TFLite export, and Android runtime registry:

| Class Index | Label ID | Hindi Numeral | Hindi Word | Mundari Numeral | Mundari Word (Devanagari) | Mundari Phonetic / Latin |
| :---: | :--- | :---: | :--- | :---: | :--- | :--- |
| **0** | `_background_` | - | मौन / अन्य | - | मौन / एटाः | Silence / Noise / Out of Vocab |
| **1** | `num_01` | १ | एक | 1 | मिअद (मिद) | miad / mid |
| **2** | `num_02` | २ | दो | 2 | बारिया (बार) | baria / bar |
| **3** | `num_03` | ३ | तीन | 3 | अपिया (अपि) | apia / api |
| **4** | `num_04` | ४ | चार | 4 | उपुनिया (उपुन) | upunia / upun |
| **5** | `num_05` | ५ | पाँच | 5 | मोड़ेया (मोड़े) | môṛẽa / môṛẽ |
| **6** | `num_06` | ६ | छह | 6 | तुरिया (तुरुइ) | turia / turui |
| **7** | `num_07` | ७ | सात | 7 | एयाएया (एयाए) | ēyāēa / ēyāē |
| **8** | `num_08` | ८ | आठ | 8 | इरालिया (इरल) | iralia / iral |
| **9** | `num_09` | ९ | नौ | 9 | अरेया (अरे) | area / arē |
| **10** | `num_10` | १० | दस | 10 | गेलेया (गेल) | geleya / gel |
| **11** | `num_11` | ११ | ग्यारह | 11 | गेल मिद | gel mid |
| **12** | `num_12` | १२ | बारह | 12 | गेल बार | gel bar |
| **13** | `num_13` | १३ | तेरह | 13 | गेल अपि | gel api |
| **14** | `num_14` | १४ | चौदह | 14 | गेल उपुन | gel upun |
| **15** | `num_15` | १५ | पंद्रह | 15 | गेल मोड़े | gel môṛẽ |
| **16** | `num_16` | १६ | सोलह | 16 | गेल तुरुइ | gel turui |
| **17** | `num_17` | १७ | सत्रह | 17 | गेल एयाए | gel ēyāē |
| **18** | `num_18` | १८ | अठारह | 18 | गेल इरल | gel iral |
| **19** | `num_19` | १९ | उन्नीस | 19 | गेल अरे | gel arē |
| **20** | `num_20` | २० | बीस | 20 | हिसि (बार गेल) | hisi / bar gel |

---

## 5. Confidence Thresholds & Decision Logic

```kotlin
// Android Client Decision Contract
val CONFIDENCE_THRESHOLD = 0.65f
val TOP_MARGIN_THRESHOLD = 0.20f // Top 1 must exceed Top 2 by this margin

fun evaluatePrediction(probs: FloatArray): PredictionResult {
    val top1Index = probs.indices.maxByOrNull { probs[it] } ?: 0
    val top1Confidence = probs[top1Index]
    
    // Sort to find runner up
    val sortedProbs = probs.sortedDescending()
    val top2Confidence = if (sortedProbs.size > 1) sortedProbs[1] else 0.0f
    
    if (top1Index == 0 || top1Confidence < CONFIDENCE_THRESHOLD || (top1Confidence - top2Confidence) < TOP_MARGIN_THRESHOLD) {
        return PredictionResult.LowConfidenceOrUnknown(
            classIndex = top1Index,
            confidence = top1Confidence
        )
    }
    
    return PredictionResult.Match(
        classIndex = top1Index,
        confidence = top1Confidence,
        registryItem = ContentRegistry.lookupByIndex(top1Index)
    )
}
```

---

## 6. Offline Content Registry Format

The Android application stores a local JSON asset: `assets/content/content_registry.json`.

Schema:
```json
{
  "version": "1.0.0",
  "generated_date": "2026-09-04",
  "language_pair": "hi-unr",
  "domain": "FLN_NUMERACY_GRADE1",
  "items": [
    {
      "class_index": 1,
      "number": 1,
      "hindi_numeral": "१",
      "hindi_text": "एक",
      "mundari_numeral": "1",
      "mundari_text": "मिअद",
      "mundari_root": "मिद",
      "mundari_phonetic": "miad",
      "translation_status": "VERIFIED",
      "audio_asset": "audio/numbers/num_01.wav",
      "audio_status": "VERIFIED",
      "flashcard_asset": "flashcards/numbers/card_01.png",
      "flashcard_status": "VERIFIED",
      "grade": 1,
      "subject": "Mathematics",
      "fln_domain": "Foundational Numeracy",
      "topic": "Numbers 1-20",
      "nipun_competency_code": "M1.1",
      "learning_outcome": "Count, recognize, and vocalize number 1 in mother tongue"
    }
  ]
}
```
