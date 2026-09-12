# Android Architecture & Kotlin Integration Contract

**Project Code**: SIH260042  
**Component**: Offline AI/ML Speech, Translation & Vernacular Pedagogy Engine  
**Target Platform**: Low-Cost Android Tablets & Smartphones (ARM Cortex-A53 / A55 @ 1.8 GHz, 2–3 GB RAM, Android 8.0+ / API 26+)  
**Operating Mode**: 100% Offline Edge Execution (Zero Cloud API Dependencies, Zero Network Required)

---

## 1. System Overview & Offline Guarantee

This document defines the formal integration contract between the Python AI/data backend and the Android application (Kotlin).
The entire core interaction path runs strictly on-device without internet access:

$$\text{AudioRecord} \xrightarrow{\text{PCM}} \text{Streaming VAD} \xrightarrow{\text{Chunk}} \text{Audio Preprocessor} \xrightarrow{\text{Tensor}} \text{TFLite / LiteRT} \xrightarrow{\text{Text}} \text{Translation} \xrightarrow{\text{Content}} \text{Bilingual FLN Output}$$

### Offline Guarantee
- **Cloud API Dependencies**: None. Zero external HTTP/gRPC endpoints.
- **Model Execution**: Local TensorFlow Lite / Google Play services LiteRT runtime.
- **Data Repositories**: Read-only JSON/TSV indexed directly from APK assets (`app/src/main/assets/`).
- **Audio Assets**: Pre-rendered uncompressed 16-bit PCM WAV assets bundled in assets.

---

## 2. Kotlin Data Models Specification

All data structures are defined in `android/contract/`:

### 2.1 Speech Capture Models (`SpeechModels.kt`)
```kotlin
data class AudioInputConfig(
    val sampleRate: Int = 16000,
    val channelCount: Int = 1,
    val bitDepth: Int = 16,
    val bufferSizeBytes: Int = 1280, // 40 ms chunk at 16 kHz
    val targetDurationSec: Float = 1.0f,
    val targetSamples: Int = 16000
)

data class AudioBuffer(
    val pcmData: ShortArray,
    val sampleRate: Int = 16000,
    val channelCount: Int = 1,
    val durationSec: Float = pcmData.size.toFloat() / sampleRate.toFloat(),
    val timestampMs: Long = System.currentTimeMillis()
)
```

### 2.2 Speech Recognition Result (`SpeechModels.kt`)
```kotlin
data class SpeechRecognitionResult(
    val recognizedText: String?,
    val classIndex: Int?,            // 0 to 20 for numerals (0 = background/unknown)
    val confidence: Float,          // 0.0 to 1.0
    val margin: Float,              // Difference over runner-up class
    val status: String,             // "RECOGNIZED", "SILENCE", "LOW_CONFIDENCE", "HIGH_NOISE"
    val isConfident: Boolean,
    val durationSec: Float,
    val latencyMs: Float,
    val engineName: String,
    val fallbackRecommended: Boolean,
    val fallbackReason: String? = null
)
```

### 2.3 Translation Result (`TranslationModels.kt`)
```kotlin
data class TranslationResult(
    val sourceLanguage: String = "hi",
    val targetLanguage: String = "unr",
    val sourceText: String,
    val normalizedSource: String,
    val translatedText: String?,
    val phoneticText: String? = null,
    val confidence: Float,
    val matchType: String,          // "EXACT_VERIFIED_LOOKUP", "CORPUS_RETRIEVAL_MATCH", "OUT_OF_VOCABULARY"
    val status: String,             // "VERIFIED_EDUCATIONAL_LOOKUP", "CORPUS_RETRIEVAL_MATCH", "OUT_OF_VOCABULARY_UNVERIFIED"
    val provenance: String,
    val verificationStatus: String, // "CORPUS_ATTESTED", "LINGUISTICALLY_REVIEWED", "UNVERIFIED"
    val metadata: Map<String, Any> = emptyMap()
)
```

### 2.4 Educational Content Model (`EducationalModels.kt`)
```kotlin
data class EducationalContent(
    val contentId: String,          // e.g. "num_01", "PHR_MGMT_01"
    val category: String,           // "NUMBER", "CLASSROOM_INSTRUCTION", "GREETING", "PRAISE"
    val grade: Int = 1,
    val subject: String = "Mathematics",
    val flnDomain: String = "Foundational Numeracy",
    val topic: String,
    val learningOutcome: String,
    val nipunCompetencyCode: String,
    val nipunStatus: String = "UNVERIFIED — PENDING SOURCE VALIDATION",
    
    // Bilingual Text
    val hindiText: String,
    val hindiNumeral: String? = null,
    val mundariText: String,
    val mundariNumeral: String? = null,
    val mundariPhonetic: String,
    
    // Media Assets
    val flashcardAssetPath: String? = null,
    val flashcardStatus: String = "GENERATED_PROTOTYPE (PENDING HUMAN VALIDATION)",
    val audioAssetPath: String? = null,
    val audioId: String? = null,
    val audioStatus: String = "SYNTHETIC_PROTOTYPE",
    
    // Pedagogical Exercises
    val worksheetId: String? = null,
    val recommendedActivityId: String? = null,
    val activityTitle: String? = null,
    val activityInstructionHi: String? = null,
    val activityInstructionUnr: String? = null
)
```

### 2.5 Unified Session Response (`SessionModels.kt`)
```kotlin
data class PedagogySessionResponse(
    val sessionId: String,
    val inputMode: String,          // "TEACHER_HINDI_VOICE", "TEACHER_HINDI_TEXT", "DIRECT_CARD_SELECTION", "SPOKEN_SPEECH"
    val inputContent: String,
    val isSuccess: Boolean,
    val statusCode: String,
    val message: String,
    val speechResult: SpeechRecognitionResult? = null,
    val translationStatus: String,
    val hindiText: String? = null,
    val mundariText: String? = null,
    val mundariPhonetic: String? = null,
    val confidence: Float,
    val contentId: String? = null,
    val content: EducationalContent? = null,
    val audioAssetPath: String? = null,
    val audioId: String? = null,
    val audioStatus: String,        // "SYNTHETIC_PROTOTYPE" or "MISSING"
    val fallbackRecommended: Boolean,
    val fallbackPathway: String = "PATHWAY_C_DIRECT_CARD_SELECTION",
    val latencyBreakdownMs: Map<String, Float> = emptyMap(),
    val hardwareProfileStatus: String = "ANDROID_MEASURED_PENDING"
)
```

---

## 3. End-to-End Android Pipeline Specification

| Pipeline Step | Input | Output | Thread / Dispatcher | Failure Behavior | Expected Latency (ARM Cortex-A53) | Memory Footprint |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Audio Capture** | Mic input (16 kHz 16-bit) | `AudioBuffer` (40 ms chunks) | Dedicated `HandlerThread` | Hardware failure / permission denied $	o$ Trigger Touch Card Mode | $< 1.0\text{ ms}$ per chunk | $< 2.0\text{ MB}$ circular buffer |
| **2. Streaming VAD** | 40 ms PCM chunk | Speech start/end events | Dedicated Audio Thread | Energy $< -45.0\text{ dBFS}$ $	o$ Reset buffer | $< 0.5\text{ ms}$ per chunk | $< 500\text{ KB}$ |
| **3. Audio Preprocessor** | 1.0s audio buffer (16,000 samples) | Log-Mel tensor `[1, 101, 64, 1]` | `Dispatchers.Default` | Signal error $	o$ Return `AUDIO_DEFECT` | $8.00\text{ ms}$ | $< 1.5\text{ MB}$ |
| **4. Speech Recognizer** | Log-Mel tensor `[1, 101, 64, 1]` | `SpeechRecognitionResult` | `Dispatchers.Default` | Conf $< 0.65$ or Margin $< 0.04$ $	o$ Recommend Touch Card | $47.50\text{ ms}$ | $< 15.0\text{ MB}$ (TFLite interpreter) |
| **5. Translation Engine** | Recognized Hindi text | `TranslationResult` | `Dispatchers.Default` | Sim $< 0.60$ $	o$ `OUT_OF_VOCABULARY_UNVERIFIED` (Refuse output) | $3.10\text{ ms}$ | $< 8.0\text{ MB}$ (Corpus index) |
| **6. Content Registry** | Content ID or Numeral | `EducationalContent` | `Dispatchers.Default` | ID not found $	o$ Fallback to raw text translation | $1.25\text{ ms}$ | $< 3.5\text{ MB}$ (In-memory JSON) |
| **7. Audio Resolver** | Content ID | Asset path + `audioStatus` | `Dispatchers.IO` | Asset missing $	o$ Set status `MISSING`, proceed with visual pedagogy | $1.10\text{ ms}$ | $< 1.0\text{ MB}$ |
| **8. UI & Audio Output** | `PedagogySessionResponse` | Compose / Views + Audio | `Dispatchers.Main` | Media error $	o$ Show visual toast, keep lesson active | $< 5.0\text{ ms}$ | UI memory pool |
| **Total Pipeline** | **Teacher Speech** | **Verified Pedagogy** | **Coordinated** | **Zero-Hallucination Safe Fallback** | **~67.45 ms** | **< 35.0 MB Total RAM** |

---

## 4. TFLite / LiteRT Contract

### 4.1 Speech Model (`models/speech_model.tflite`)
- **Input Tensor**:
  - Name: `input_spectrogram`
  - Shape: `[1, 101, 64, 1]` (Batch=1, TimeFrames=101, MelBins=64, Channels=1)
  - Data Type: `Float32`
  - Normalization: Raw natural log Mel energies (centered and normalized prior to correlation).
- **Output Tensor**:
  - Name: `output_probabilities`
  - Shape: `[1, 21]`
  - Data Type: `Float32`
  - Activation: Softmax probabilities ($\sum p_i = 1.0$)
- **Class Indexing Order**:
  - `0`: `_background_` (Silence, ambient noise, out-of-lexicon vocalizations)
  - `1`..`20`: `num_01`..`num_20` (Numerals 1 to 20)

### 4.2 Confidence & Margin Decision Logic
```kotlin
val CONFIDENCE_THRESHOLD = 0.65f
val MARGIN_THRESHOLD = 0.04f

fun evaluatePrediction(probabilities: FloatArray): SpeechRecognitionResult {
    val top1Index = probabilities.indices.maxByOrNull { probabilities[it] } ?: 0
    val top1Score = probabilities[top1Index]
    
    val sortedScores = probabilities.sortedDescending()
    val top2Score = if (sortedScores.size > 1) sortedScores[1] else 0.0f
    val margin = top1Score - top2Score

    val isConfident = top1Index > 0 && top1Score >= CONFIDENCE_THRESHOLD && margin >= MARGIN_THRESHOLD

    return SpeechRecognitionResult(
        recognizedText = if (isConfident) getClassWord(top1Index) else null,
        classIndex = if (isConfident) top1Index else null,
        confidence = top1Score,
        margin = margin,
        status = if (isConfident) "RECOGNIZED" else "LOW_CONFIDENCE",
        isConfident = isConfident,
        durationSec = 1.0f,
        latencyMs = 0.0f,
        engineName = "TFLiteNumeralClassifier",
        fallbackRecommended = !isConfident,
        fallbackReason = if (!isConfident) "Confidence $top1Score < $CONFIDENCE_THRESHOLD or margin $margin < $MARGIN_THRESHOLD" else null
    )
}
```

---

## 5. Android Preprocessing Specification (DSP Contract)

The Kotlin DSP pipeline implemented in `android/contract/AudioPreprocessor.kt` must match Python `AudioPreprocessor` exactly:

1. **Audio Resampling**: Target rate = 16,000 Hz. Mono channel.
2. **PCM Conversion**: 16-bit signed little-endian PCM normalized to Float32: $x_{\text{float}} = x_{\text{int16}} / 32768.0$.
3. **Fixed Window**: 16,000 samples (1.00 s).
4. **Symmetric Center Padding**: 200 samples prepended and appended ($400 / 2 = 200$), totaling 16,400 samples.
5. **Framing**: 101 frames, window length = 400 samples (25 ms), hop length = 160 samples (10 ms).
6. **Periodic Hann Window**:
   $$w[n] = 0.5 \cdot \left(1.0 - \cos\left(\frac{2\pi n}{N - 1}\right)\right), \quad n = 0, \dots, 399$$
7. **Zero-Padded 512-Point FFT**: Windowed 400 samples padded with 112 zeros $\to$ Cooley-Tukey Radix-2 FFT $\to$ 257 unique frequency bins ($N/2 + 1$).
8. **Power Spectrogram**: $|X[k]|^2 = \text{real}[k]^2 + \text{imag}[k]^2$.
9. **Triangular Mel Filterbank**: 64 bins spanning 20 Hz to 8,000 Hz.
10. **Log Compression**: Natural logarithm $\ln(\text{mel\_energy} + 10^{-6})$.
11. **Tensor Shape**: Output formatted into a direct `ByteBuffer` of size $101 \times 64 \times 4 = 25,856\text{ bytes}$ for TFLite `[1, 101, 64, 1]`.

---

## 6. Android Asset Packaging (`app/src/main/assets/`)

```
app/src/main/assets/
├── models/
│   └── speech_model.tflite                # TFLite edge model (198 KB)
├── registry/
│   ├── content_registry.json              # Canonical 1-20 FLN curriculum metadata
│   └── audio_manifest.json                # Master cryptographic audio manifest
├── translation/
│   └── translation-hi-unr.tsv             # 17,809 validated parallel sentence pairs
├── flashcards/
│   └── numbers/
│       ├── card_01.svg                    # SVG flashcard numeral 1
│       └── ... (card_02.svg to card_20.svg)
├── worksheets/
│   └── templates/
│       ├── ws_01_recognition.json         # Recognition worksheet template
│       ├── ws_02_counting.json            # Counting worksheet template
│       └── ws_03_writing.json             # Writing worksheet template
└── audio/
    └── prototype_tts/
        ├── numbers/
        │   ├── num_01.wav                 # Pre-rendered synthetic prototype (16 kHz mono)
        │   └── ... (num_02.wav to num_20.wav)
        └── phrases/
            ├── PHR_GREET_01.wav           # "नमस्ते" -> "जोहार"
            ├── PHR_MGMT_01.wav            # "बैठो" -> "दुबपे"
            ├── PHR_MGMT_02.wav            # "खड़े हो जाओ" -> "तिंगुपे"
            ├── PHR_MGMT_06.wav            # "किताब खोलो" -> "पुथी ओड़ाःपे"
            ├── PHR_ENCR_01.wav            # "बहुत अच्छा" -> "खूब बुगी"
            ├── PHR_ENCR_02.wav            # "शाबाश" -> "बुगी कामी"
            ├── PHR_NUM_01.wav             # "गिनो" -> "लेकापे"
            └── ... (16 prototype phrases total)
```

---

## 7. Threading, Coroutines & Lifecycle Management

### 7.1 Threading Architecture
- **Audio Capture Loop**: Runs in a dedicated background coroutine using `Dispatchers.IO` or a separate `HandlerThread` with `Process.THREAD_PRIORITY_AUDIO`.
- **Ring Buffer & VAD**: In-memory ring buffer evaluated in the audio capture thread.
- **DSP Preprocessing & Model Inference**: Executed on `Dispatchers.Default` (CPU-bound worker thread pool). Never executed on the Main thread.
- **UI State Dispatch**: Emits state via Kotlin `StateFlow<PedagogyUiState>` observed on `Dispatchers.Main`.
- **Audio Playback**: Executed asynchronously using `MediaPlayer` / `ExoPlayer` on background threads.

### 7.2 Lifecycle States
- **`onResume`**: Verify `RECORD_AUDIO` permission; if granted and session active, start capture thread.
- **`onPause`**: Immediately call `audioRecord.stop()`, release microphone hardware, pause ongoing playback.
- **`onDestroy`**: Close TFLite interpreter, release memory buffers, terminate coroutine scopes.
- **Microphone Hardware Failure / Disconnect**: Catch `IllegalStateException`, post user-friendly toast, automatically activate **Pathway C: Direct Touch Card Mode**.

---

## 8. Five-Level Fallback & Safety Rules

1. **Silence Fallback**: If $\text{RMS} < -45.0\text{ dBFS}$, return `SILENCE_DETECTED_FALLBACK`. Do not run model inference.
2. **Noise Fallback**: If $\text{SNR} < 8.0\text{ dB}$, return `HIGH_NOISE_FALLBACK`. Prompt teacher to move closer or reduce room noise.
3. **Ambiguous Speech Fallback**: If model confidence $< 0.65$ or margin $< 0.04$, return `AMBIGUOUS_AUDIO_FALLBACK_RECOMMENDED`. Prompt user to tap the visual flashcard directly.
4. **Zero-Hallucination Translation Fallback**: If translation similarity $< 0.60$, mark as `OUT_OF_VOCABULARY_UNVERIFIED`. Refuse to invent words.
5. **Missing Audio Fallback**: If an audio file is absent from disk, set `audioStatus = "MISSING"`. Deliver bilingual text, flashcard SVG, worksheet, and activity without crashing.

---

## 9. Performance Metric Classifications

| Metric Category | Label | Android Handling Rule |
| :--- | :--- | :--- |
| **Desktop Workstation Measured** | `DESKTOP_MEASURED` | Historical engineering benchmark on x86_64; do not present as Android performance. |
| **Android Estimated Projection** | `ANDROID_ESTIMATED` | Mathematical projection for ARM Cortex-A53; explicitly labeled as estimate. |
| **Physical Android Measured** | `ANDROID_MEASURED` | **Must be reported as `PENDING_PHYSICAL_DEVICE_DEPLOYMENT`** until profiled on real hardware. |

---

## 10. Scope & Extensibility

The system is **NOT** restricted to "1–20 number recognition."
- **Numerals 1–20**: Serves as the first standardized, controlled FLN mathematical competency benchmark.
- **Classroom Commands**: Extensible MTB-MLE phrasebook (20+ commands and daily routines).
- **Parallel Corpus**: 17,809 parallel sentence pairs for broader conversational classroom translation.

---

## 11. Known Limitations & Integrity Stamping

1. **Real Mundari 1–20 Speech Accuracy**: `UNVERIFIED` (Native field data collection was decoupled).
2. **Native Linguistic Validation**: `PENDING` validation by certified Mundari community educators.
3. **Classroom Acoustic Recordings**: Authentic multi-child classroom acoustic recordings remain unavailable.
4. **Physical Android Performance**: `PENDING` on-device hardware profiling.
5. **Mundari TTS Audio**: Stamped strictly as `SYNTHETIC_PROTOTYPE (PENDING HUMAN VALIDATION)`. Never described as certified native pronunciation.
