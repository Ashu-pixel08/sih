# Vernacular FLN Assistant (APP_NAME_PENDING)

> **Mother-Tongue Primary Education & Classroom Translation Prototype (Hindi ↔ Mundari)**

---

## 1. Project Overview

The **Vernacular FLN Assistant** is an offline-capable pedagogical tool designed to bridge classroom communication between Hindi-speaking primary school teachers and tribal-language primary school learners in Eastern India (Jharkhand, Odisha, West Bengal).

The current implementation targets **Mundari** (ISO 639-3: `unr`, Devanagari script) aligned with the **NIPUN Bharat** Foundational Literacy and Numeracy (FLN) framework and Mother-Tongue Based Multilingual Education (MTB-MLE) principles.

The application operates as a dual-surface system:
1. **Teacher Workspace**: Speech-to-text / text classroom translation, bilingual curriculum segmentation, interactive flashcards, printable bilingual worksheets, and student attendance/progress tracking.
2. **Student Learning Space**: Real-time broadcast receiver, numbers 1–20 exploration with ten-frame visual aids, flashcard drills, and gamified practice quizzes.

---

## 2. Current Prototype Capabilities

* **4-Tier Hybrid Translation Engine**:
  * **Tier 1 (Verified Educational Registry)**: Exact deterministic lookup for approved numerals (1–20) and classroom command phrases. Verified against attested bilingual dictionaries; broadcastable to students.
  * **Tier 2 (Neural Machine Translation)**: Custom sequence-to-sequence Transformer with Byte-Pair Encoding (BPE) trained on the approved Hindi–Mundari parallel corpus. Generates translations for general conversational queries. Outputs are strictly flagged as *Requires Review* and blocked from unverified broadcast.
  * **Tier 3 (Corpus Retrieval)**: TF-IDF vector retrieval fallback matching attested parallel sentence pairs when neural translation is bypassed.
  * **Tier 4 (Safe Rejection)**: Out-of-vocabulary and non-Devanagari inputs are safely rejected without hallucinations.
* **Teacher Review & Broadcast Gate**: AI-generated translations cannot be broadcast directly to student devices without teacher confirmation.
* **Demonstration & Audit Mode (`?demo=1`)**: Evaluator interface displaying live 5-stage pipeline tracing (Audio/Text Input → Normalization → 4-Tier Routing → Mundari Output → Teacher Review Gate) with 8 verified evaluation presets.
* **Student Interface**: Zero technical jargon, model scores, or AI telemetry; shows only lesson content, visual ten-frames, audio playback, and pedagogical drills.
* **Android Native App**: Offline Android build (Kotlin + AndroidX + Gradle) with local contract parity and Vosk / TFLite edge model readiness.

---

## 3. Technology Stack

| Layer | Technologies |
|---|---|
| **Machine Learning / NMT** | Python 3.11+, PyTorch (Seq2Seq Transformer), TorchScript export, Hugging Face Tokenizers (BPE), scikit-learn |
| **Edge Speech Classifier** | ONNX Runtime, TensorFlow Lite (TFLite Float16/Float32) |
| **Web Frontend** | Vanilla HTML5, CSS3, ES6 JavaScript (Zero external CDN/framework dependencies, 100% offline runnable) |
| **Local Bridge Server** | Python `http.server` with JSON REST API routes (`/api/translate`, `/api/health`, `/api/content`) |
| **Android Application** | Kotlin, Android SDK 34, AndroidX, Gradle 8.7 |
| **Testing** | Pytest (213 automated test suites), JUnit 4, Gradle `testDebugUnitTest` |

---

## 4. Project Structure

```text
├── ai/                         # Machine learning & translation modules
│   ├── ml_translation/         # NMT Transformer architecture, training & inference
│   ├── speech/                 # Edge speech classifier & feature extraction
│   └── translation/            # 4-tier translation engine & Hindi normalizer
├── android/                    # Native Android application
│   ├── app/src/main/           # Kotlin source code, assets & UI layouts
│   └── build.gradle.kts        # Android build configuration
├── content/                    # Pedagogical curriculum & offline assets
│   ├── audio/prototype_tts/    # Pre-rendered 16 kHz WAV pronunciation files
│   ├── flashcards/             # Flashcard generators & SVG assets
│   ├── translations/           # Canonical numerals 1–20 & classroom phrasebook
│   ├── worksheets/             # Printable HTML worksheet generators
│   └── content_registry.json   # Ground-truth content registry with provenance
├── data/                       # Dataset governance & split metadata
│   ├── governance/             # Intake contracts & dataset audit reports
│   ├── metadata/               # Speech & translation resource inventories
│   └── schemas/                # JSON schemas for data contracts & manifests
├── docs/                       # Architectural documentation & validation reports
├── frontend/                   # Web application prototype
│   └── index.html              # Standalone teacher & student single-page app
├── models/                     # Model artifacts & exported inference packages
│   ├── edge/                   # TFLite and ONNX speech classifiers
│   └── nmt/                    # Tokenizers, export manifests & TorchScript models
├── tests/                      # Automated test suites (213 tests)
├── tools/                      # Data validation & ingestion scripts
└── server.py                   # Local development server & API bridge
```

---

## 5. Getting Started

### Prerequisites

* Python 3.10, 3.11, or 3.12 (Python 3.13 supported)
* Node.js 18+ (optional, for browser automation tests)
* JDK 17+ and Android SDK (for Android builds)

### Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd vernacular-fln-assistant

# Create and activate a virtual environment
python -m venv .venv

# On Linux / macOS:
source .venv/bin/activate

# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# Install required dependencies
pip install torch numpy scikit-learn pytest
```

### Running the Browser Prototype

```bash
# Start the local development server
python server.py 8080
```

* **Standard Classroom Portal**: Open `http://localhost:8080/` in your browser.
  * Teacher sign-in password: `1234`
  * Student sign-in: Enter any student name and roll number.
* **Evaluator / Demo Mode**: Open `http://localhost:8080/?demo=1` for the live pipeline inspector and judge presets.

---

## 6. Running Tests

The test suite covers data contracts, translation engine tiers, audio preprocessing, UI parity, and browser runtime execution:

```bash
# Run the complete Python test suite (213 tests)
pytest tests/

# Run specific validation modules
pytest tests/test_neural_translation.py
pytest tests/test_ui_backend_integration.py
pytest tests/test_phase_8_browser_prototype.py
```

---

## 7. Building the Android Application

```bash
# Navigate to the Android directory
cd android

# Run native Android unit tests
./gradlew testDebugUnitTest

# Assemble the debug APK
./gradlew assembleDebug
```

The compiled APK will be generated at `android/app/build/outputs/apk/debug/app-debug.apk`.

---

## 8. Dataset & Resource Provenance

All language resources used in this prototype adhere to strict intake and provenance guidelines:

1. **Foundational Numerals (1–20) & Classroom Phrases**:
   * Sourced from authentic bilingual lexicography (Bhaduri 1931, Hoffman & van Emelen *Encyclopaedia Mundarica*, SEAlang Munda Languages Project).
   * Verified by educational domain specialists; mapped to NIPUN Bharat primary competencies.
2. **Parallel Training Corpus**:
   * 17,809 Hindi–Mundari sentence pairs created through open academic collaborations (Microsoft Research India, IIT Kharagpur, Karya, and the FAIR Forward initiative).
   * Licensed under the **KPL BY-NC-SA-FS 1.0** license (Karya Public License Non-Commercial Share-Alike Free Software).
3. **Reference Lexicons**:
   * SEAlang Munda Lexicon and ASJP Swadesh wordlists are utilized strictly as read-only phonological and dialectological references.
4. **Quarantined / Gated Datasets**:
   * Datasets requiring specific authentication or commercial redistribution agreements (e.g. Karya ELR-1000, Endangered Recipes) are strictly quarantined in metadata-only manifests and are **not** redistributed in this repository.

---

## 9. Important Licensing Notes

* **Software**: The application architecture, Android codebase, web interface, and training pipeline are released under open-source terms.
* **Parallel Corpus & Speech Samples**: Governed by the **KPL BY-NC-SA-FS 1.0** license. Any derivative models or adaptations incorporating this material inherit non-commercial and copyleft (ShareAlike) obligations. Commercial deployment requires separate licensing from the respective rights holders.
* **No Redistribution of Gated Datasets**: Only open or legally cleared metadata manifests are tracked.

---

## 10. Current Limitations & Linguistic Integrity

1. **Distinction Between Verified Content and Neural Output**:
   * **Verified Educational Registry**: Numerals 1–20 and classroom commands are human-vetted and guaranteed safe for early-grade instruction.
   * **Neural Model Translations**: The neural model is an experimental low-resource Seq2Seq Transformer. While it demonstrates generalization across diverse Hindi inputs, its outputs **must not** be treated as certified pedagogical ground-truth without human review.
2. **Audio Status**:
   * All pronunciation audio WAV files in `content/audio/prototype_tts/` are **pre-rendered synthetic prototype audio** explicitly classified as `SYNTHETIC_PROTOTYPE (PENDING HUMAN VALIDATION)`.
   * Authentic native-speaker audio recordings require scheduled field collection in Jharkhand with community consent.
3. **Speech Recognition (STT)**:
   * The browser prototype utilizes the Web Speech API for Hindi input (which requires an active network connection in standard browsers).
   * Offline speech recognition on Android uses on-device acoustic models (Vosk / TFLite edge models).

---

## 11. Contributions & Ethics

When contributing to this repository:
* Never commit hardcoded personal machine paths or local environment credentials.
* Never commit datasets or audio without verifying license compatibility and provenance manifests.
* Preserve linguistic honesty: do not fabricate translation accuracy metrics or present unverified model outputs as community-validated translations.
