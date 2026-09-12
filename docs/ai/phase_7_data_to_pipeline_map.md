# Phase 7 — Data-to-Pipeline Allocation Map

**Project Identifier:** SIH260042 (`APP_NAME_PENDING`)  
**Phase:** Phase 7 — Live Translation & Speech Pipeline Implementation  
**Document ID:** MAP-PHASE7-DATA-ALLOCATION  
**Date:** September 6, 2026  
**Governance Standard:** Evidence-Based Architecture & Zero-Fabrication Pipeline  

---

## 1. Executive Summary

This document establishes the formal mapping of every dataset, corpus, lexicon, and audio resource in the project repository to its designated operational role in the live AI prototype. 

To maintain scientific integrity and prevent data contamination, each resource is classified by:
1. Physical location and format
2. Licensing and legal authorization
3. Permitted runtime role (Inference, Training, Evaluation, Lookup, or Quarantine)
4. Explicitly prohibited uses
5. Offline edge suitability

---

## 2. Resource Allocation Matrix

| Resource Category | Repository Location | Format & Scale | License / Provenance | Permitted Operational Role | Prohibited Operational Use | Training Suitability | Eval Suitability | Runtime Inference |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| **A1. Bilingual Parallel Corpus** | `data/raw/translation/translation-hi-unr.tsv` | TSV (Tab-separated), 17,809 sentence pairs (~2.4 MB) | CC-BY-4.0 / Research permitted (IIT Madras / Karya / AI4Bharat) | Tier 2 Offline Sentence Retrieval (Character n-gram TF-IDF vector space) | Do NOT claim as general neural MT model training set without full domain filtering | Permitted (Domain adaptation) | Permitted (BLEU/chrF) | **Active (Tier 2 Retrieval)** |
| **A2. Candidate Educational Translation** | `data/incoming/pratham_0240.json` | JSON, 27 parallel records (20 sentence, 7 scene) | CC-BY-4.0 (Pratham Books / StoryWeaver #0240) | Research / Story demonstration / Linguistic consistency testing | Do NOT promote to canonical classroom content (`CANONICAL_APPROVED`) | Not recommended (Too small, 27 pairs) | Permitted (Anecdotal story test) | **Isolated (Research only)** |
| **B. Native Speech Audio Corpus** | `data/metadata/` & sample WAVs in scratch | 16 kHz 16-bit Mono WAV, 5 sample utterances (100.8s) | CC-BY-4.0 (IIT Madras / Karya) | Acoustic profiling, feature extraction validation, benchmark vectors | Do NOT claim sample audio is sufficient to train continuous ASR | Sample only (Full 50+ hr corpus needed) | Permitted (Acoustic benchmark) | **Benchmark only** |
| **C. Educational Story Data** | `data/incoming/pratham_0240.json` | Markdown / JSON, 27 records | CC-BY-4.0 (Jodheswar Barla translation) | Illustrated read-along prototype, child-directed vocabulary audit | Do NOT use as unverified ground truth in live classroom broadcast | No | Permitted (Story comprehension) | **Isolated (Research demo)** |
| **D. Historical & Modern Lexicons** | Referenced in `docs/data_governance/` | 13-vol *Encyclopaedia Mundarica* (Hoffmann), Bhaduri (1931), Osada (2008) | Public Domain / Academic Research | Reference corroboration of lexical roots, morphological rules, checked vowel verification | Do NOT ingest copyrighted modern textbooks into codebase | No (Lexicography) | Permitted (Golden dictionary) | **Active (Reference rules)** |
| **E. Controlled Classroom Vocabulary** | `content/content_registry.json` & `content/translations/` | JSON, 21 classes (Numbers 1–20 + Background) + 16 classroom phrases | JCERT / NCERT aligned, verified Munda lexicography | Tier 1 Deterministic Educational Lookup (100% precision, zero hallucination) | Do NOT expand without verified source attribution | No | Active (Accuracy target: 100%) | **Active (Tier 1 Primary)** |
| **F. Synthetic Prototype Audio** | `content/audio/prototype_tts/` | 16 kHz 16-bit Mono WAV (~680 KB total) | MIT / Apache 2.0 (Synthesized via `ai/speech/mundari_tts_engine.py`) | Prototype classroom pronunciation audio for numbers and commands | NEVER label as "native authentic speech" or use to train ASR | **STRICTLY PROHIBITED** | Not applicable | **Active (Labeled PROTOTYPE)** |

---

## 3. Detailed Data Pipeline Specification

### Category A: Hindi ↔ Mundari Parallel Translation Data
- **Dataset File:** `data/raw/translation/translation-hi-unr.tsv`
- **Cleaned Sentence Count:** 17,809 validated sentence pairs
- **Preprocessing Applied:**
  * Unicode NFC normalization
  * Stripping of ASCII control codes
  * Removal of empty or whitespace-only lines
  * Removal of identical source/target pairs (placeholder filtering)
  * Duplicate pair suppression
- **Indexing Strategy:**
  * Inverted character n-gram index (char_wb, ngrams 2 to 4)
  * Sub-linear cosine similarity search via normalized sparse matrix
  * Fits completely in memory (< 12 MB RAM footprint)
  * Bidirectional indexing: Supports both Hindi → Mundari and Mundari → Hindi retrieval!

### Category B: Mundari Speech / Audio Data
- **Sample Audio Archive:** `karya_audio/` (staged in scratch artifact directory)
- **Profile:** 16,000 Hz, 16-bit PCM, Mono channel.
- **Role:** Verifies Android and desktop DSP preprocessor parity (`AudioPreprocessor.kt` and `audio_preprocessor.py`).
- **Limitation:** The available sample audio comprises 5 distinct speakers (3 female, 2 male). While sufficient for signal-to-noise, spectral tilt, and VAD validation, it cannot train an unrestricted acoustic model. The production edge model relies on the trained 21-class vocabulary CNN (`models/edge/speech_classifier_float32.tflite`).

### Category C: Educational Story Data
- **Dataset File:** `data/incoming/pratham_0240.json` (Story #0240 *मछलियों की बारिश* / *हाईकोअ: गमा*)
- **Governance Status:** `RESEARCH_VALIDATED` (Levels 1 + 2 + 3)
- **Classroom Gate:** **QUARANTINED FROM PRODUCTION BROADCAST.**
- **Rationale:** The candidate story contains known orthographic anomalies (e.g. checked vowel colons, parenthetical Sadri glosses, and the typographical error `चोकेकोअ: गाा` in Record 19). It serves as an evaluation and story-reading demonstration module, not broadcast-safe classroom instruction.

### Category D: Linguistic Reference Authorities
- **Primary References:**
  1. Rev. John Hoffmann & Arthur van Emelen, *Encyclopaedia Mundarica* (1930–1950) — Public Domain
  2. Manindra Bhusan Bhaduri, *A Mundari-English Dictionary* (1931) — Public Domain
  3. Rev. John Hoffmann, *Mundari Grammar* (1903) — Public Domain
  4. Toshiki Osada, *A Reference Grammar of Mundari* (1992/2008) — Academic reference
- **Role:** Ground truth verification for morphological clitics (`-tan-a`, `-ked-a`, `-pe`, `-kin`) and lexical roots in Tier 1 translation rules.

### Category E: Controlled Classroom Registry
- **Files:** `content/content_registry.json` and `content/translations/classroom_phrasebook.json`
- **Content:**
  * 20 canonical number classes (Numerals 1 to 20, words, phonetic transcriptions, roots, and dialectal variants)
  * 1 background noise class
  * 16 classroom interaction commands (`जोहार`, `दुबपे`, `तिंगुपे`, `लेकापे`, `ओलपे`, `पाड़ावपे`, `आयूमपे`, `खूब बुगीन`, आदि)
- **Operational Role:** Tier 1 deterministic lookup with 100% precision and zero latency (< 0.2 ms).

### Category F: Pre-Rendered Prototype Audio
- **Directory:** `content/audio/prototype_tts/`
- **Generation Source:** `ai/speech/mundari_tts_engine.py` using Meta MMS-TTS parameterization.
- **Audio Specification:** 16 kHz Mono WAV, duration 0.6s to 1.8s per utterance.
- **Labeling Standard:** All assets are explicitly tagged:
  `"verification_status": "SYNTHETIC_PROTOTYPE (PENDING HUMAN VALIDATION)"`
