# Android Integration Contract & Runtime Specification
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
