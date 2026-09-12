# UI to Backend Integration Specification

**Project Code**: SIH260042  
**Application Identity**: APP_NAME_PENDING (Configurable Platform Identity)  
**Document Version**: 1.1.0  
**Target Operating Environment**: 100% Offline Edge Architecture (Android 8.0+ / API 26+) with Web Prototype Reference  
**Deployment Status**: OFFLINE ARCHITECTURE READY — PHYSICAL ANDROID VALIDATION PENDING  

---

## 1. System Integration Philosophy & Scope

This document defines the formal mapping between the user interface screens and the modular AI/data backend developed for SIH260042.

### 1.1 General Platform Scope & Demonstration Module Distinction
The system is designed as an expansive **Mother-Tongue Foundational Literacy and Numeracy (FLN) Educational Platform**.
Numbers 1–20 represent the **first controlled demonstration / MVP module**. It is **not** the definition of the complete platform.

```
Educational Platform Architecture
├── Numeracy
│   ├── Numbers 1–20 (Demonstration / MVP Module — Controlled Lexicon)
│   ├── Basic Arithmetic (Addition, Subtraction — Planned Module)
│   └── Shapes & Spatial Patterns (Planned Module)
├── Literacy
│   ├── Oral Vocabulary & Phonics (Planned Module)
│   ├── Word-Object Association (Planned Module)
│   └── Interactive Storytelling (Planned Module)
├── Classroom Language
│   └── Daily Classroom Commands & Routines (Reference-Derived Corpus)
└── Educational Vocabulary
    └── School, Nature, Body Parts & Community (Planned Modules)
```

### 1.2 Core Integration Principles
1. **UI is strictly the Presentation Layer**: The UI renders states and captures interactions.
2. **AI/Data Backend is the Canonical Source of Truth**: All translations, phonetics, FLN curriculum structures, audio manifests, and validation rules originate from canonical registries (`content_registry.json`, `classroom_phrasebook.json`, `curriculum_model.json`). The UI never creates its own translation database.
3. **Strict Text vs. Audio Status Separation**:
   - **Text Status**: Attested in reference lexicography (`CORPUS_ATTESTED`, `EXACT_CANONICAL_LOOKUP`, `REFERENCE_DERIVED`).
   - **Audio Status**: All generated Mundari audio files are labeled `SYNTHETIC_PROTOTYPE (PENDING HUMAN VALIDATION)`. Authentic native recordings await Jharkhand field collection.
4. **Separation of Hardware Performance Metrics**:
   - `DESKTOP_MEASURED`: 12.4 ms (x86_64 CPU)
   - `ANDROID_ESTIMATED`: ~35–65 ms (ARM Cortex-A53 @ 1.8 GHz target)
   - `ANDROID_MEASURED`: PENDING PHYSICAL DEVICE DEPLOYMENT
5. **Classroom Networking Status**:
   - `CLASSROOM SESSION CONTRACT READY`: Interfaces and data contracts are defined. Physical multi-device transport (Wi-Fi P2P / Hotspot) remains pending physical device validation.
6. **Decoupled Three-Tier Speech Architecture**:
   - **Teacher Hindi Speech**: Constrained Hindi educational recognizer -> Hindi text -> Translation Engine -> Mundari text.
   - **Mundari Educational Speech**: Controlled educational vocabulary recognizer -> Content concept.
   - **General Mundari ASR**: Broader ASR -> Mundari text (currently a research/desktop capability; not an edge Android model).

---

## 2. Complete Screen-by-Screen Integration Mapping

### 2.1 Authentication & Workspace Navigation
- **Screen**: Login / Role Selection (`login`, `showTeacherLogin`, `showStudentLogin`)
- **Backend Service**: `UserSessionService` (Local session manager)
- **Inputs**: 
  - Teacher: Local authentication PIN (prototype: `1234`, production: Keystore-encrypted teacher profile)
  - Student: Student name + Roll number (stored locally in room roster)
- **Outputs**: Active role (`TEACHER` or `STUDENT`), session token, room binding.
- **Offline Contract**: Validated strictly on-device against local SQLite user database. Zero network authentication required.

---

### 2.2 Teacher Workspace

#### A. Teacher Dashboard (`dashboard`)
- **Backend Service**: `ClassroomSessionService` + `ContentRegistryService`
- **Inputs**: Teacher session state
- **Outputs**:
  - Active Room Code (`VFLN-XXXX`)
  - Connected Students Count (Roster size)
  - System Health & Model Status (`TFLite Model: LOADED`, `Assets: 20/20 VERIFIED`)
  - Latency Metrics: `DESKTOP_MEASURED: 12.4 ms`, `ANDROID_ESTIMATED: ~35–65 ms (PENDING PHYSICAL DEVICE BENCHMARK)`
- **Actions**:
  - `startRoom()`: Initializes local classroom broadcast channel and generates room PIN.

#### B. Speak & Translate / Live Classroom (`live`)
- **Backend Service**: `VernacularPedagogyCoordinator` (Orchestrates `HindiASREngine`, `TranslationEngine`, `ContentRegistryService`, and `MundariTTSEngine`)
- **Inputs**:
  - Primary: Microphone stream (16 kHz 16-bit Mono PCM `AudioBuffer`)
  - Fallback / Manual: Hindi text transcript (e.g. "बच्चों, आज हम एक सेब के बारे में सीखेंगे।" or "एक")
- **Backend Processing Flow**:
  1. `AudioPreprocessor`: Resamples, computes 512-pt FFT, applies 64-bin Mel filterbank -> Tensor `[1, 101, 64, 1]`
  2. `HindiASREngine`: Evaluates constrained TFLite acoustic classifier -> `SpeechRecognitionResult`
  3. `TranslationEngine`: Evaluates Tier 1 bilingual lookup + Tier 2 corpus retrieval -> `TranslationResult`
  4. `ContentRegistryService`: Retrieves bilingual lesson, phonetic guide, SVG flashcard, and prototype audio path -> `EducationalContent`
- **Outputs**:
  - `recognizedHindi`: Recognized Hindi transcript
  - `mundariText`: Attested Mundari translation (e.g. "मिअद")
  - `phoneticGuide`: Pronunciation aid for non-native teachers (e.g. "Miyad")
  - `audioPath`: Path to prototype WAV pronunciation (`content/audio/prerendered/unr_num_01.wav`)
  - `textStatus`: `EXACT_CANONICAL_LOOKUP`, `CORPUS_ATTESTED`, or `OUT_OF_VOCABULARY`
  - `audioStatus`: `SYNTHETIC_PROTOTYPE (PENDING HUMAN VALIDATION)`
  - `confidenceScore`: Float value 0.0 -> 1.0
- **Teacher Review & Approval**:
  - Teacher reviews the translation preview on screen.
  - Clicking **"Broadcast to Students"** sends the approved packet to `ClassroomSessionService`.

#### C. Translate Curriculum (`curriculum`)
- **Backend Service**: `TranslationEngine` (Batch mode) + `ContentRegistryService`
- **Inputs**: Multi-sentence Hindi curriculum or textbook text
- **Backend Processing**:
  - Sentence splitter -> per-sentence normalizer
  - Fast dictionary lookup for FLN core vocabulary
  - Character 3-gram TF-IDF retrieval against the 17,809-pair bilingual corpus for complex sentences
- **Outputs**: Structured translation table with:
  - Source sentence
  - Translated Mundari text
  - Match type (`EXACT_CANONICAL_LOOKUP`, `CORPUS_RETRIEVAL_MATCH`, `UNVERIFIED`)
  - Verification badge for teacher sign-off before classroom use.

#### D. Learning Modules (`modules`)
- **Backend Service**: `FLNContentEngine` + `ContentRegistryService`
- **Inputs**: Curriculum Domain (`FOUNDATIONAL_NUMERACY`), Module ID (`NUM_1_20`), Grade (1)
- **Scope Note**: Numbers 1–20 is the first demonstration module of the broader FLN platform.
- **Outputs**: List of 20 canonical number modules with:
  - Arabic Numeral (`1` to `20`)
  - Devanagari Digit (`१` to `२०`)
  - Hindi Word (`एक` to `बीस`)
  - Mundari Word (`मिअद` to `हिसि`)
  - Phonetic Romanization (`miad` to `hisi`)
  - Linguistic Root (`मिद`, `बार`, etc.)
  - Visual Representation (Ten-Frame counter dots count)
  - Detail View (`numberDetail(n)`): Shows pedagogical card with pronunciation, counting guide, text attestation status, and prototype audio status.

#### E. Worksheet Generator (`worksheet`)
- **Backend Service**: `WorksheetGenerator` (`content/worksheets/worksheet_generator.py`)
- **Inputs**:
  - Worksheet Type: `recognition`, `counting`, `matching`, `sequencing`, or `missing_numbers`
  - Item count: 5, 10, or 20
  - Target Language: Bilingual (Hindi + Mundari)
- **Outputs**:
  - Clean printable A4 layout with school header, date, student name, and instructions
  - Structured questions with Ten-Frame counting boxes, tracing lines, and matching columns
  - Teacher answer key.

#### F. Student Progress (`progress`)
- **Backend Service**: `ProgressAnalyticsService`
- **Inputs**: Class ID, Date range
- **Outputs**:
  - Class Average Practice Completion (%)
  - Active Students Count
  - Per-student mastery matrix across Numerals 1–20
  - Label: Explicitly tagged as `LOCAL_CLASSROOM_DATA`.

#### G. Offline Content (`offline`)
- **Backend Service**: `OfflineAssetRegistry`
- **Inputs**: None (inspects local asset storage)
- **Outputs**:
  - Cached Lesson Modules count (20 Numerals [Demo module] + 31 Classroom commands)
  - Prototype Audio Assets count (20 pre-rendered WAV files labeled `SYNTHETIC_PROTOTYPE`)
  - Vector Graphics count (20 Ten-Frame SVG cards)
  - Storage consumption (~1.8 MB total)
  - Architecture Status: `OFFLINE ARCHITECTURE READY — PHYSICAL ANDROID VALIDATION PENDING`.

#### H. Settings (`settings`)
- **Backend Service**: `AppConfigService`
- **Inputs**: UI preference toggles (Language mode, audio autoplay, fallback threshold)
- **Outputs**: Saved configuration state in local storage / SharedPreferences.

---

### 2.3 Student Workspace

#### A. Student Home (`home`)
- **Backend Service**: `ClassroomSessionService` (Client)
- **Inputs**: Student profile
- **Outputs**: Quick entry to Live Classroom receiver, Numbers 1–20 module, and Practice quiz.

#### B. Live Classroom Receiver (`liveclass`)
- **Backend Service**: `ClassroomSessionService` (Receiver) + `AudioPlaybackService`
- **Inputs**: Room Code input (`joinRoom(code)`)
- **Networking Status**: `CLASSROOM SESSION CONTRACT READY`
- **Outputs**: Real-time synchronized receiver card:
  - Teacher speaking indicator
  - Teacher Hindi instruction
  - Attested Mundari translation
  - Phonetic pronunciation assistance
  - "Play Prototype Audio" button triggering local prototype WAV playback
  - Visual Ten-Frame card corresponding to the discussed concept.

#### C. Learn Mundari Modules (`modules`)
- **Backend Service**: `ContentRegistryService`
- **Inputs**: Grade 1 FLN Numerals 1–20 (Demonstration Module)
- **Outputs**: Interactive student learning grid with phonetic pronunciation for each numeral.

#### D. Flashcards (`flashcards`)
- **Backend Service**: `FlashcardGenerator` + `ContentRegistryService`
- **Inputs**: Card index (1 to 20)
- **Outputs**: High-contrast visual flashcard with:
  - Ten-frame visual counting grid
  - Devanagari numeral
  - Hindi name
  - Mundari name (`मिअद`, `बारिया`, etc.)
  - Interactive Next / Previous controls.

#### E. Practice Quiz (`practice`)
- **Backend Service**: `FLNContentEngine.generate_activity()`
- **Inputs**: Activity type (`find_successor`, `identify_number`, `count_objects`)
- **Outputs**:
  - Dynamic question prompt (e.g. "Which number comes after 7?")
  - 4 answer options with randomized distractors
  - Immediate celebratory feedback for correct answer and encouraging guidance for retries.

---

## 3. Technology Migration: Prototype vs. Production

| Subsystem | Web Prototype Reference | Android Native Production Target | Production Status |
| :--- | :--- | :--- | :--- |
| **Speech-to-Text (STT)** | `window.SpeechRecognition` (`WEB PROTOTYPE ONLY`) | `AudioRecord` -> `AudioPreprocessor` -> 198 KB TFLite CNN Classifier | Model exported & verified on desktop; physical Android benchmark pending |
| **Audio Playback** | `window.speechSynthesis` (`SYNTHETIC_PROTOTYPE`) | Bundled 16 kHz WAV assets via `MediaPlayer` / `SoundPool` | Audio labeled `SYNTHETIC_PROTOTYPE (PENDING HUMAN VALIDATION)` |
| **Real-Time Classroom Bus** | `BroadcastChannel` + `localStorage` | `ClassroomSessionService` (Local Wi-Fi P2P / Hotspot Multicast) | `CLASSROOM SESSION CONTRACT READY` (Transport implementation pending) |
| **Data Storage** | In-memory JS / `localStorage` | Encrypted Room / SQLite database + APK Assets | Contract ready; schema conforms to backend models |
| **Network Dependency** | Zero network for UI (Browser tabs) | Zero network edge execution | `OFFLINE ARCHITECTURE READY — PHYSICAL ANDROID VALIDATION PENDING` |
