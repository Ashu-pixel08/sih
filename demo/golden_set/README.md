# Bhasha Setu — Sentence-Level Golden Demo Set

**Project:** Bhasha Setu (भाषा सेतु) — AI-Powered Native-Language Classroom Bridge  
**Target Milestone:** Smart India Hackathon (SIH) Final Video Demonstration  
**Theme:** Early Numeracy & Counting (Numbers 1–10, Classroom Instructions, Student Responses)  
**Version:** 1.0.0 (September 2026)  
**Replay Suite:** `scripts/run_golden_demo.py` (20/20 Passing)

---

## 1. Executive Summary & Governance Mandate

This directory contains the authoritative, evidence-grounded **Sentence-Level Golden Demo Set** for Bhasha Setu. It has been constructed under strict engineering and linguistic governance to ensure that the SIH demonstration video reflects **real, verifiable, un-hardcoded system capabilities**.

### Core Governance Rules
1. **Zero Hardcoding Rule:** No mock responses, special-case string overrides, or bypass routes exist in the codebase. All outputs are produced dynamically by `TranslationEngine`, `HinglishNormalizer`, and `PronunciationService`.
2. **Anti-Hallucination & Provenance Mandate:** Every output explicitly reports its origin:
   - `Tier 1`: Curated offline phrasebook / JCERT educational registry (`LINGUISTICALLY_REVIEWED`).
   - `Tier 2 Exact`: Attested bilingual parallel corpus record (`CORPUS_ATTESTED`).
   - `Tier 2 Neural`: Transformer sequence-to-sequence model inference (`NEURAL_MODEL_ESTIMATED`).
3. **Strict Audio Transparency Mandate:** Audio assets are synthetic acoustic renderings from Meta MMS-TTS cached in `content/audio/prototype_tts/` and labeled `PROTOTYPE_ONLY_PENDING_HUMAN_VALIDATION`. **They must NEVER be described as "native-speaker verified" in video narration, screen text, or presentation slides.**
4. **Honest Triage Protocol:** Candidate inputs that fail quality gates, drop key numerals, hallucinate grammar, or lack independent attestation are labeled `NOT_DEMO_READY`. They are documented transparently rather than forced through.

---

## 2. Benchmark Summary Statistics

| Classification | Count | Definition & Filming Eligibility |
| :--- | :---: | :--- |
| **`DEMO_READY`** | **2** | Fully verified translation with independent reference AND playable, valid 16 kHz audio file in prototype registry. **Eligible for live video demonstration with audio playback.** |
| **`PROVISIONAL`** | **9** | Verified against parallel corpus or composed registry; high semantic fidelity; audio pending field recording. **Eligible for UI text/visualizer demonstration; audio must be muted or marked pending.** |
| **`NOT_DEMO_READY`** | **9** | Long candidate sentences exhibiting neural hallucination, numeral omission, OOV refusal, or unmapped conversational Hinglish. **Ineligible for demo; documented as system boundaries.** |
| **TOTAL EVALUATED** | **20** | **Complete evaluation coverage** across Hindi, Hinglish, and Mundari classroom interactions. |

---

## 3. Master Inventory of Evaluated Items

| Item ID | Scenario | Source Input | Target Output (Mundari / Hindi) | Provenance & Validation | Confidence | Audio Status | Decision |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- | :---: |
| **`SEL_HI_05`** | Teacher follow-up question | `यह कौन सी संख्या है` | `नेआ चिनाः संख्या तना` | Offline Phrasebook (`PHR_NUM_04`) | **1.00** | Playable WAV (`SEL_HI_05.wav`, 2.69s) | **`DEMO_READY`** |
| **`SEL_HING_01`** | Teacher Hinglish follow-up | `yeh kaun si sankhya hai` | `नेआ चिनाः संख्या तना` | Governed Lexicon → `PHR_NUM_04` | **1.00** | Playable WAV (`SEL_HING_01.wav`, 2.69s) | **`DEMO_READY`** |
| **`SEL_HI_01`** | Teacher counting prompt | `अब मैं गिनती करूँगा बारह तक` | `नअःदो अइंग लेकायाइंग गेलबर जकेद्।` | Corpus Exact (Row 16907) | **1.00** | Audio Pending Field Recording | **`PROVISIONAL`** |
| **`SEL_HI_02`** | Teacher counting drill | `एक से दस तक गिनो` | `मिअद आते गेलेया जाकेद लेकापे` | Composed Phrase (`PHR_EXP_17`) | **1.00** | Audio Pending Field Recording | **`PROVISIONAL`** |
| **`SEL_HI_03`** | Classroom learning statement | `यहाँ पढ़कर बच्चे अपना कौशल तेज करेंगे।` | `नेताः रे होनको पाड़ाओकेआते आकोआः सेए ओड़ोः बाइआ।` | Corpus Exact (Row 257) | **1.00** | Audio Pending Field Recording | **`PROVISIONAL`** |
| **`SEL_HI_04`** | Teacher pedagogical reflection | `बच्चों को पढ़ाने में गुरु का मन नहीं लगता।` | `होनको पाआड़ाओ रे गुरुआः जि का ताइना।` | Corpus Exact (Row 583) | **1.00** | Audio Pending Field Recording | **`PROVISIONAL`** |
| **`SEL_UNR_01`** | Student introduction | `आञ मिआद कोड़ाहोन तानिः ओड़ोः आञाः नुतुम राजकुमार तानाः।` | `मैं एक लड़का हूं और मेरा नाम राज कुमार है।` | Corpus Retrieval (Row 2123) | **0.85** | N/A (Source is Mundari) | **`PROVISIONAL`** |
| **`SEL_UNR_02`** | Student counting recitation | `नअःदो अइंग लेकायाइंग गेलबर जकेद्।` | `अब मैं गिनती करूँगा बारह तक` | Corpus Exact (Row 16907) | **1.00** | N/A (Source is Mundari) | **`PROVISIONAL`** |
| **`SEL_UNR_03`** | Classroom statement | `नेताः रे होनको पाड़ाओकेआते आकोआः सेए ओड़ोः बाइआ।` | `यहां पढ़कर बच्चे अपना कौशल तेज करेंगे।` | Corpus Retrieval (Row 257) | **0.82** | N/A (Source is Mundari) | **`PROVISIONAL`** |
| **`SEL_HING_02`** | Hinglish counting drill | `ek se das tak gino` | `मिअद आते गेलेया जाकेद लेकापे` | Governed Lexicon → `PHR_EXP_17` | **1.00** | Audio Pending Field Recording | **`PROVISIONAL`** |
| **`SEL_HING_03`** | Hinglish classroom attention | `dhyan se suno` | `ध्यानते आयूमपे` | Governed Lexicon → `PHR_EXP_10` | **1.00** | Audio Pending Field Recording | **`PROVISIONAL`** |
| `CAND_HI_01` | Candidate 1 (Long Hindi) | `आज हम नंबर के बारे में पढ़ेंगे...` | `तिसिङ आले नंबर बारे रे पाड़ाओ मेनते...` | Neural Inference (Low Token Logits) | 0.16 | Audio Unavailable | `NOT_DEMO_READY` |
| `CAND_HI_02` | Candidate 2 (Long Hindi) | `सब बच्चे ध्यान से सुनो...` | *(Safely Refused)* | Neural Refusal Gate (PPL Threshold) | 0.00 | Audio Unavailable | `NOT_DEMO_READY` |
| `CAND_HI_03` | Candidate 3 (Long Hindi) | `बहुत अच्छा! अब सब मिलकर...` | `बेसेगे सबेनको मिसारे मोनेया...` | Neural Inference (Truncated) | 0.28 | Audio Unavailable | `NOT_DEMO_READY` |
| `CAND_HI_04` | Candidate 4 (Long Hindi) | `श्याम, तुम खड़े हो जाओ...` | `अम काजिमे मिअद आते आपिया...` | Neural Inference (Severe Hallucination) | 0.22 | Audio Unavailable | `NOT_DEMO_READY` |
| `CAND_HI_05` | Candidate 5 (Long Hindi) | `शाबाश, सब बच्चे ताली बजाओ...` | `सबेनको को ताली साडेएपे...` | Neural Inference (Grammar Hallucination) | 0.17 | Audio Unavailable | `NOT_DEMO_READY` |
| `CAND_HI_06` | Candidate 6 (Long Hindi) | `कल हम 11 से 20 तक की संख्या...` | `आयार जाकेद गे ताइकेनाएः...` | Neural Inference (Numeral Loss) | 0.24 | Audio Unavailable | `NOT_DEMO_READY` |
| `CAND_HING_01`| Candidate 1 (Hinglish) | `aaj hum number ke baare mein...` | *(Safely Refused)* | OOV Gate (15 Unlexiconized Tokens) | 0.00 | Audio Unavailable | `NOT_DEMO_READY` |
| `CAND_HING_02`| Candidate 2 (Hinglish) | `sab bacche dhyan se suno...` | *(Safely Refused)* | OOV Gate (10 Unlexiconized Tokens) | 0.00 | Audio Unavailable | `NOT_DEMO_READY` |
| `CAND_HING_03`| Candidate 3 (Hinglish) | `bahut achha, ab batao paanch...` | *(Safely Refused)* | OOV Gate (7 Unlexiconized Tokens) | 0.00 | Audio Unavailable | `NOT_DEMO_READY` |

---

## 4. Why Candidate Sentences Failed Live Audit

During audit, the 6 user-proposed candidate Hindi sentences and 3 Hinglish sentences were fed through the true runtime pipeline. None passed the criteria for `DEMO_READY` due to three distinct architectural constraints:

1. **Neural Hallucination on Low-Resource Complex Syntax:**
   - Mundari is an agglutinative language with complex postpositional markers (`-re`, `-a:`, `-te`) and verbal incorporated subject/object agreement (`-ing`, `-pe`, `-ko`).
   - The Transformer NMT model (`models/nmt/final/best_transformer.pt`) has trained on ~17,000 sentence pairs. For multi-clause compound sentences (e.g. `CAND_HI_04` with 21 words), the beam search loses grammatical coherence, yielding token generation probabilities between 0.12 and 0.28.
   - Example (`CAND_HI_06`): The neural model translated `"कल हम 11 से 20 तक की संख्या सीखेंगे"` into `"आयार जाकेद गे ताइकेनाएः"`, completely omitting the numerals 11 and 20.
2. **Safe Refusal on Conversational Hinglish:**
   - The `HinglishNormalizer` uses a governed lexicon (`data/approved/hinglish/governed_hinglish_lexicon.json`).
   - For `CAND_HING_01`, the normalizer matched `"1 se 10 tak"`, but could not reliably map `"ke baare mein padhenge, chalo batao kaun"`.
   - Rather than passing Romanized English or unverified phonemes into the NMT engine (which causes gibberish output), `TranslationEngine` halts and returns `OUT_OF_VOCABULARY_UNVERIFIED`. This is a desirable safety guardrail, but renders the long candidate unsuited for a smooth live video.
3. **Absence of Pre-Synthesized Audio:**
   - Prototype audio requires pre-rendered audio entries in `content/audio/audio_manifest.json` because the live MMS-TTS acoustic model checkpoint is too large for on-demand edge rendering without GPU.
   - None of the 6 long Hindi candidate sentences have pre-rendered WAV assets in the registry, triggering HTTP 503 if requested.

---

## 5. Supported Classroom Alternatives (Pedagogy Preserved)

To maintain realistic classroom dialogue without risking live demonstration failure, we selected verified sentences that map directly to the same Grade 1 numeracy pedagogical flow:

1. **Counting Drill Prompt (Teacher):**
   - *Input:* `एक से दस तक गिनो` (or Hinglish: `ek se das tak gino`)
   - *Mundari:* `मिअद आते गेलेया जाकेद लेकापे` (Composed from attested roots `मिअद आते`, `गेलेया जाकेद`, `लेकापे`).
2. **Counting Recitation & Commitment (Teacher & Student):**
   - *Input:* `अब मैं गिनती करूँगा बारह तक` (Corpus Row 16907)
   - *Mundari:* `नअःदो अइंग लेकायाइंग गेलबर जकेद्।`
   - *Confidence:* **1.00** exact match.
3. **Student Identity (Student):**
   - *Input (Mundari):* `आञ मिआद कोड़ाहोन तानिः ओड़ोः आञाः नुतुम राजकुमार तानाः।` (Corpus Row 2123)
   - *Hindi Translation:* `मैं एक लड़का हूं और मेरा नाम राज कुमार है।`
   - *Pedagogical Value:* Demonstrates two-way communication where tribal students speak in their home language and the teacher UI confirms comprehension.
4. **Formative Assessment Question (Teacher):**
   - *Input:* `यह कौन सी संख्या है` (or Hinglish: `yeh kaun si sankhya hai`)
   - *Mundari:* `नेआ चिनाः संख्या तना`
   - *Audio File:* `demo/golden_set/audio/SEL_HING_01.wav` (Playable 16 kHz WAV, 2.69s).

---

## 6. Audio Asset Verification & Compliance

### Physical WAV File Specifications
The two `DEMO_READY` items link to physical audio files located in `demo/golden_set/audio/`:
- `SEL_HI_05.wav` (86,124 bytes)
- `SEL_HING_01.wav` (86,124 bytes)

Each file has been programmatically inspected using Python's standard `wave` library and verified against the following parameters:
- **Encoding:** Linear PCM
- **Channels:** 1 (Mono)
- **Sample Width:** 2 bytes (16-bit)
- **Sample Rate:** 16,000 Hz
- **Total Frames:** 43,040 frames
- **Duration:** 2.69 seconds

### Mandatory Compliance Caption
Whenever audio is played during video recording or demonstration, the following on-screen caption or equivalent presenter disclosure is mandatory:
> *"Audio Output: Prototype acoustic synthesis (Meta MMS-TTS). Field recordings with native Mundari educators are scheduled for deployment phase."*

---

## 7. Video Filming Guide

A structured 4-scene video script is provided in `demo/golden_set/video_script.json`.

- **Scene 1 (0:00 – 0:25):** Teacher Greeting & Counting Instruction (`ek se das tak gino` → `मिअद आते गेलेया जाकेद लेकापे`).
- **Scene 2 (0:25 – 0:50):** Dual-Script Classroom Board & Ten-Frame Numeracy Visualizer (`मिअद [1]` to `गेलेया [10]`).
- **Scene 3 (0:50 – 1:15):** Student Mother-Tongue Response (`नअःदो अइंग लेकायाइंग गेलबर जकेद्।` → `अब मैं गिनती करूँगा बारह तक`).
- **Scene 4 (1:15 – 1:45):** Teacher Formative Assessment & Audio Pronunciation (`yeh kaun si sankhya hai` → `नेआ चिनाः संख्या तना` with WAV audio playback).

---

## 8. Reproduction & Verification

To verify that the Golden Demo Set remains 100% reproducible and conforms to quality gates:

```powershell
# Activate project virtual environment
cd C:\Users\Lenovo\Documents\sih
.venv\Scripts\python.exe scripts\run_golden_demo.py
```

Expected output:
```text
================================================================================
  BHASHA SETU — GOLDEN DEMO VERIFICATION & REPLAY SUITE
================================================================================
Loaded 20 items from C:\Users\Lenovo\Documents\sih\demo\golden_set\golden_demo_set.json
...
================================================================================
  REPLAY SUITE SUMMARY: 20 PASSED, 0 FAILED (TOTAL: 20)
================================================================================
```
