# Vernacular FLN Assistant (BHASHA SETU)

> **Mother-Tongue Primary Education & Classroom Translation Prototype (Hindi ↔ Mundari)**
> Aligned with NIPUN Bharat Foundational Literacy and Numeracy (FLN) & MTB-MLE Principles.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Pytest Tests](https://img.shields.io/badge/tests-245%20passed-brightgreen.svg)]()
[![Git LFS](https://img.shields.io/badge/Git%20LFS-Enabled-orange.svg)]()
[![Platform: Web + Android](https://img.shields.io/badge/Platform-Web%20%7C%20Android-green.svg)]()
[![License: KPL & Open Source](https://img.shields.io/badge/License-KPL%20%26%20Open%20Source-orange.svg)]()

---

## 1. Problem Statement & Purpose

In primary schools across tribal regions of Eastern India (predominantly Jharkhand, Odisha, and West Bengal), a significant pedagogical barrier exists between **Hindi-speaking teachers** and **tribal mother-tongue learners** entering Grade 1. Children who speak indigenous Austroasiatic languages like **Mundari** (*Mundari jagar*, ISO 639-3: `unr`) often face severe comprehension challenges when instruction occurs exclusively in standard regional languages.

The **Vernacular FLN Assistant** provides an offline-first, dual-surface platform that enables:
1. **Teachers** to conduct lessons in Hindi while delivering verified, contextually accurate mother-tongue (Mundari) translations, interactive visual aids, and synthesized pronunciation directly to student devices.
2. **Students** to learn foundational numeracy and literacy in their mother tongue through visual ten-frames, interactive flashcards, bilingual worksheets, and real-time classroom audio.

---

## 2. Core Architecture & Capabilities

### A. Dual-Surface User Interface
* **Teacher Command Center**:
  * **Overview Dashboard**: Clean teacher command center displaying active classroom sessions, system health, rapid FLN action launchers, and foundational literacy statistics.
  * **Continuous Voice Orb Mode**: Full-screen voice workspace with real-time listening, state transitions (READY, LISTENING, PROCESSING, TRANSLATING, SPEAKING, INTERRUPTED, ERROR), and barge-in voice interruption.
  * **Curriculum Translation**: Segment-by-segment bilingual lesson preparation with review gates.
  * **Educational Learning Modules**: 10 FLN categories (Animals, Birds, Body Parts, Colors, Family, Flowers, Food, Insects, Vegetables, Vehicles) displaying Mundari terms, Devanagari script, phonetics, and high-resolution visuals.
  * **Printable FLN Worksheets**: 5 canonical exercise generators (`recognition`, `counting`, `matching`, `sequencing`, `missing_numbers`) with responsive A4 printable styling.
  * **Flashcards Visualizer**: Interactive ten-frame dot counters, phonetics, and root etymologies for foundational numeracy.
  * **Practice Arena**: Student progress review, quiz accuracy records, and mastery tracking.
* **Student Learning Space**:
  * **Live Classroom Receiver**: Synchronized real-time display of teacher's instruction, Mundari text, ten-frame visualizers, prototype audio playback, and quick Mundari replies/reactions (👍, ✋, ❤️, 💡).
  * **Self-Paced Practice Quiz**: Child-friendly multiple-choice questions with instant auditory feedback and score tracking.
  * **Zero Technical Exposure**: Developer metrics, loss values, token likelihoods, and internal models are completely hidden from learners and teachers.

### B. 4-Tier Hybrid Translation Engine
1. **Tier 1 (Exact Canonical Lookup)**: Deterministic dictionary mapping for 20 foundational numerals, 16 core classroom commands, and verified custom vocabulary. Latency < 5ms, 1.0 confidence, instantly safe for classroom broadcast.
2. **Tier 2 (Neural Machine Translation)**: Custom sequence-to-sequence Transformer with Byte-Pair Encoding (BPE) trained on 17,863 parallel sentence pairs. Routed through a strict *Teacher Review Gate* before broadcast.
3. **Tier 3 (Corpus TF-IDF Retrieval)**: Exact and fuzzy retrieval matching attested corpus pairs when neural output requires verification.
4. **Tier 4 (Safe Refusal)**: Out-of-vocabulary terms and non-pedagogical inputs are rejected safely without hallucination.

### C. Offline Multi-Device Synchronization
* Browser-based local testing uses the HTML5 `BroadcastChannel` API (`vfln_classroom_bus`) for instant zero-latency message distribution across multiple tabs/windows on the same origin without external server dependency.
* Android deployment utilizes local peer-to-peer / Wi-Fi Direct networking contracts.

---

## 3. Technology Stack

| Component | Stack |
|---|---|
| **Neural Machine Translation** | PyTorch (Seq2Seq Transformer), TorchScript JIT export, Hugging Face Tokenizers (BPE), scikit-learn |
| **Edge Speech Classifier** | ONNX Runtime, TensorFlow Lite (TFLite Float16 & Float32) |
| **Web Application** | Vanilla HTML5, CSS3, ES6 JavaScript (Zero external CDN/framework dependencies, 100% offline runnable) |
| **Local Bridge Server** | Python `http.server` with JSON REST API routes (`/api/translate`, `/api/health`, `/api/content`) |
| **Android Application** | Kotlin, Android SDK 34, AndroidX, Gradle 8.7 |
| **Test Framework** | Pytest (245 automated test suites), Node.js CDP runner, JUnit 4 |

---

## 4. Documentation Index

For deep-dive documentation, consult the guides in `docs/`:

* 📘 [**Team Development & Collaboration Guide**](docs/TEAM_DEVELOPMENT_GUIDE.md): Developer onboarding, virtual environments, Git LFS, branching conventions, and contribution rules.
* 🏛️ [**System Architecture**](docs/ARCHITECTURE.md): Dual-surface design, translation tier flowcharts, voice orb state machine, and sync protocols.
* 📊 [**Educational Dataset & Multimodal Assets Guide**](docs/DATASET_GUIDE.md): Catalog of 159 educational pairs, 130 image assets, schemas, and governance rules.
* 🧠 [**AI/ML Model Guide**](docs/AI_MODEL_GUIDE.md): Seq2Seq Transformer architecture, BPE tokenization, quality gates, and edge classifiers.
* 📦 [**Model Inventory & Verification Manifest**](models/MODEL_MANIFEST.md): Parameter specifications, checksums, and Git LFS tracking details.

---

## 5. Repository Structure

```text
.
├── ai/                         # AI models, tokenizers, translation & educational content
│   ├── educational_content.py  # High-performance educational catalog manager
│   ├── ml_translation/         # NMT Seq2Seq Transformer model, training & inference
│   ├── speech/                 # Edge speech classifier & acoustic feature extractor
│   └── translation/            # 4-tier hybrid engine & Hindi normalizer
├── android/                    # Native Android application
│   ├── app/src/main/           # Kotlin source code, assets, contracts & UI layouts
│   └── build.gradle.kts        # Android build configuration
├── content/                    # Canonical educational curriculum & assets
│   ├── audio/prototype_tts/    # Pre-rendered 16 kHz WAV pronunciation audio
│   ├── flashcards/             # Flashcard generators & SVG assets
│   ├── fln/                    # Foundational Literacy & Numeracy model definitions
│   ├── translations/           # Numerals 1–20 & classroom phrasebook JSON
│   ├── worksheets/             # Printable HTML worksheet templates
│   └── content_registry.json   # Ground-truth content registry with provenance
├── data/                       # Datasets, multimodal assets & governance
│   ├── custom/                 # Cleaned team educational dataset & 130 images
│   ├── governance/             # Intake contracts & dataset audit reports
│   ├── metadata/               # Speech & translation resource inventories
│   ├── processed/              # NMT train, validation, and test splits (17.8k pairs)
│   ├── test_vectors/           # Challenge sets & held-out vocabulary benchmarks
│   └── schemas/                # JSON schemas for data contracts & manifests
├── docs/                       # Architectural guides, developer manuals & reports
├── frontend/                   # Web application prototype
│   └── index.html              # Standalone teacher & student single-page app
├── models/                     # Exported models & tokenizers
│   ├── edge/                   # TFLite and ONNX speech classifiers
│   └── nmt/                    # Tokenizers, TorchScript, and production Transformer
│       └── final/              # Production checkpoint (best_transformer.pt via Git LFS)
├── tests/                      # Automated test suite (245 passing tests)
├── tools/                      # Data intake, validation & linting scripts
├── server.py                   # Local development server & API bridge
├── requirements.txt            # Python dependencies
├── .gitattributes              # Git LFS tracking configuration (*.pt)
├── .gitignore                  # Git exclusion rules
└── README.md                   # Project overview & quickstart
```

---

## 6. Quickstart Guide

### Prerequisites
* Git & **Git LFS** (`git lfs version`)
* Python 3.10+
* JDK 17+ and Android SDK 34 (for Android builds)

### 1. Clone & Initialize Git LFS
```bash
git clone https://github.com/Ashu-pixel08/sih.git
cd sih

# Pull large model weights tracked by Git LFS
git lfs install
git lfs pull
```

### 2. Python Environment Setup
```bash
# Windows (PowerShell):
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS:
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies:
pip install -r requirements.txt
```

### 3. Launch the Local Development Server
```bash
python server.py 8080
```

* **Main Interface**: Open `http://localhost:8080/` (Teacher password: `1234`)
* **Evaluator / Demo Mode**: Open `http://localhost:8080/?demo=1`

### 4. Execute Automated Tests (245 Tests)
```bash
pytest tests/ -v
```

---

## 7. Data Governance & Licensing

* **Application Code**: Released under open-source terms.
* **Parallel Corpus**: Governed by the **KPL BY-NC-SA-FS 1.0** license (Karya Public License Non-Commercial Share-Alike Free Software). Any derivative models retain non-commercial copyleft terms.
* **Educational Assets**: Curated educational vocabulary and non-commercial photographic visuals for primary tribal literacy development.
