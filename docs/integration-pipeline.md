# End-to-End System Integration Pipeline Documentation

**Project Code**: SIH260042  
**Component**: `VernacularPedagogyPipeline` (`ai/integration_pipeline.py`)  
**Domain**: Grade 1 Foundational Literacy and Numeracy (FLN) — Bilingual Hindi ↔ Mundari (`hi` ↔ `unr`)  
**Deployment Target**: Low-Cost Android Device (ARM Cortex-A53 / A55 @ 1.8GHz, 2–3 GB RAM, Offline Edge)

---

## 1. System Overview & Core Architecture

The `VernacularPedagogyPipeline` connects the system's modular AI, speech, translation, and curriculum assets into a single unified interaction engine.

```
[Teacher Hindi Voice]
         │
         ▼
[Audio Preprocessor] (16 kHz mono, Hann window, 64-bin Log-Mel)
         │
         ▼
[Constrained Hindi Educational Speech Recognizer] (Lexicon Correlation & Acoustic Gating)
         │
         ├── Low Confidence / Silence / High Noise ──► [Interactive Touch & Card Fallback Mode]
         ▼
    (Recognized Hindi Text)
         │
         ▼
[Bilingual Translation Engine] (Tier 1 Verified Educational Retrieval + Tier 2 Corpus Retrieval)
         │
         ├── Similarity < 0.60 ──► [Refusal to Hallucinate / Safe Unverified Fallback]
         ▼
    (Verified Mundari Text)
         │
         ▼
[FLN Content Engine] (Numerals 1–20, Lesson Plans, Worksheets, TPR Activities)
         │
         ▼
[Mundari Audio Resolution] (Pre-rendered Synthetic Prototype Audio / Fallback to Visual & Text)
         │
         ▼
[PedagogySessionResponse] (Structured Multi-Modal Educational Output)
```

---

## 2. Terminology & Scope Boundary

### Constrained Hindi Educational Speech Recognition
- **Identity**: `HindiASRRecognizer` (`ai/speech/hindi_asr_engine.py`)
- **Scope**: Constrained offline acoustic recognition specifically optimized for classroom management commands (सुनो, बैठो, खड़े हो जाओ, किताब खोलो, शाबाश, etc.) and canonical FLN numbers 1–20 (एक .. बीस).
- **Classification**: `CONSTRAINED HINDI EDUCATIONAL SPEECH RECOGNITION`
- **Important Boundary**: This component does **not** claim general unrestricted Hindi ASR capabilities. Any future unrestricted Whisper-based or large-vocabulary model resides in a separate research module (`ai/speech/general_hindi_asr.py`) and is not conflated with this lightweight edge recognizer.

### General Mundari ASR Separation
- **Edge Runtime**: Constrained Speech Recognition -> Translation -> FLN Engine.
- **Research / Desktop**: Foundation Multilingual ASR (Meta MMS-1B `unr`). Excluded from low-RAM Android runtime due to 4.5 GB RAM footprint.

---

## 3. Four Operating Pathways

| Pathway | Trigger Modality | Primary Use Case | Fail-Safe & Fallback |
| :--- | :--- | :--- | :--- |
| **Pathway A: Student Numeral Speech** | Spoken audio waveform (Mundari numerals) | Child practices counting aloud in Mundari | If confidence $< 0.65$, prompts touch card selection |
| **Pathway B: Teacher Hindi Text** | Text input (Hindi words/phrases) | Teacher types instructions or uses tablet assistant | Out-of-vocabulary terms marked `UNVERIFIED`; zero hallucination |
| **Pathway C: Direct Touch Card Mode** | Digital card tap (Numerals 1–20) | Guaranteed presentation fallback; 0 ms speech compute | Deterministic 100% verified retrieval |
| **Pathway D: Teacher Voice Interaction** | Spoken teacher Hindi voice | End-to-end voice-activated bilingual teaching | Quality gates reject silence, noise, and low-margin vocalizations |

---

## 4. Quality Gates & Safety Mechanisms

1. **Acoustic Energy Floor (Silence Gate)**:
   - Signals with RMS < -45.0 dBFS or duration < 0.15 s are immediately rejected as `SILENCE_DETECTED_FALLBACK`.
2. **Signal-to-Noise Ratio (Noise Gate)**:
   - Signals with SNR < 8.0 dB are rejected as `HIGH_NOISE_FALLBACK`.
3. **Discriminative Margin Gate**:
   - Audio must exceed confidence threshold >= 0.65 and margin >= 0.04 over the second-best candidate.
4. **Zero-Hallucination Translation Gate**:
   - If Hindi input does not match verified phrasebook or corpus with cosine similarity $\ge 0.60$, the system returns `OUT_OF_VOCABULARY_UNVERIFIED` and refuses to invent words.
5. **Missing Audio Fallback Gate**:
   - If audio asset is missing from disk, pedagogy still succeeds: text, flashcard SVG, worksheet, and activity are delivered, while `audio_status = "MISSING"`.

---

## 5. Audio Status & TTS Verification Policy

All pre-rendered Mundari educational audio assets (`content/audio/prototype_tts/`) are strictly marked:
```json
{
  "verification_status": "SYNTHETIC_PROTOTYPE (PENDING HUMAN VALIDATION)",
  "is_synthetic": true
}
```
**Strict Policy**:
- May be used for prototype playback and software verification.
- Must **NOT** be called native recordings.
- Must **NOT** be used as speech model training data.
- Must **NOT** be used as linguistic ground truth.
- Must **NOT** be described as native-speaker verified pronunciation.

---

## 6. End-to-End Latency & Hardware Profile

### Latency Breakdown (Desktop Measured)
*Benchmarked on Python 3.13 CPU (x86_64):*
- Audio Preprocessing: **1.20 ms**
- Hindi Recognition: **2.15 ms**
- Translation Lookup: **0.05 ms**
- FLN Content Retrieval: **0.15 ms**
- Audio Asset Lookup: **0.05 ms**
- **Total End-to-End Latency**: **3.60 ms**

### Edge Android Projection (ARM Cortex-A53 @ 1.8 GHz)
- Projected Latency: **58.5 ms** (Well within 350 ms classroom target)
- Projected Peak RAM: **< 65 MB** (Well within 2–3 GB device constraints)
- Physical Device Status: `PENDING_PHYSICAL_DEVICE_DEPLOYMENT`

---

## 7. Automated Test Verification

Full test suite verified across 17 test modules (**116 / 116 tests passing**):
- `tests/test_end_to_end_voice_pipeline.py`: 10 comprehensive tests covering all 9 operational scenarios:
  1. Teacher says known classroom command
  2. Teacher says known numeracy instruction
  3. Teacher says known 1–20 number
  4. Teacher says unsupported sentence
  5. Audio is silent
  6. Audio is noisy
  7. Hindi text has low-confidence translation
  8. Mundari audio asset exists
  9. Mundari audio asset is missing
  10. Latency breakdown & status separation
