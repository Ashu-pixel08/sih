# Data Source Selection & Audit Analysis

**Project**: AI-Powered Vernacular Pedagogy & Real-Time Translation Tool for Primary Education  
**Document ID**: `docs/data-source-selection.md`  
**Audit Version**: `1.0.0`  
**Date**: `2026-09-04`  

---

## 1. Executive Summary & Selection Decision Matrix

This audit evaluates all candidate public data resources across Speech, Translation, Linguistic Reference, and Speech Synthesis (TTS) against our project's operational, technical, legal, and offline constraints.

### Master Evaluation Matrix

| Resource | Data Type | Language | Size / Records | Speakers | Transcripts | 1–20 Coverage | License | Training Use | Redistribution | Offline APK Use | Decision |
| :--- | :--- | :--- | ---: | ---: | :---: | :---: | :--- | :---: | :---: | :---: | :---: |
| **`dataset-hindi-mundari-translation`** | Parallel Text | Hindi ↔ Mundari | 17,804 pairs | N/A | Full Devanagari | 20/20 in text | KPL BY-NC-SA-FS 1.0 | **YES** | **YES** (NonComm) | **YES** (GPL/Open) | **`PUBLIC + USABLE`** |
| **`dataset-mundari-tts (Sample)`** | Spoken Audio | Mundari (`unr`) | 200 takes (12.36 min) | 2 (Studio) | 100% Devanagari | 0 isolated (5 contextual) | KPL BY-NC-SA-FS 1.0 | **CONDITIONAL** (Benchmark Only) | **YES** (NonComm) | **YES** (Assets) | **`PUBLIC + CONDITIONALLY USABLE`** |
| **`dataset-mundari-tts (Full)`** | Spoken Audio | Mundari (`unr`) | 26,870 takes (~35 hrs) | 2 (Studio) | Full Devanagari | Unknown isolated | KPL BY-NC-SA-FS 1.0 | **GATED** (Not locally available) | Gated | Gated | **`PUBLIC + CONDITIONALLY USABLE (GATED)`** |
| **`Kathbath / Vistaar / IndicSpeech`** | Spoken Audio | 22 Scheduled Indic | 1,000+ hrs | Thousands | Yes | 0 (Mundari absent) | CC-BY-4.0 | **NO** (Mundari Absent) | N/A | N/A | **`PUBLIC + NOT USABLE`** |
| **`Mozilla Common Voice`** | Spoken Audio | Multilingual | 0 hrs validated | 0 | None | 0 | CC-0 / Public | **NO** (No Mundari data) | N/A | N/A | **`PUBLIC + NOT USABLE`** |
| **`Encyclopaedia Mundarica (Hoffman)`** | Lexicon / Grammar | Mundari–English | 16 Volumes | N/A | Roman / IPA | 20/20 roots | Public Domain | **REFERENCE ONLY** | Public | N/A | **`REFERENCE ONLY`** |
| **`Mundari Grammar (CIIL Swaminathan)`** | Linguistics | Mundari | 1 Monograph | N/A | Phonetic / Devanagari | 20/20 | Academic / Fair Use | **REFERENCE ONLY** | Academic | N/A | **`REFERENCE ONLY`** |
| **`Pretrained Mundari TTS Checkpoint`** | Acoustic Synthesis | Mundari | Model weights | Studio | N/A | Synthetic | Research / Copyleft | **BENCHMARK ONLY** | NonComm | Prototyping Only | **`CONDITIONALLY USABLE (PROTOTYPE ONLY)`** |

---

## 2. In-Depth Domain Audit Findings

### 2.1 Speech Recognition Data (Mundari Speech)

#### Primary Candidate: `dataset-mundari-tts` (Sample vs. Full)
- **Sample Findings**:
  - We physically inspected the 64.5 MB sample (`data-sample.tgz`) in `data/raw/speech/data-sample/`.
  - Total: 200 WAV audio files (100 female, 100 male) paired with 200 `.txt` transcripts.
  - Acoustic properties: 44,100 Hz, 1-channel mono, 32-bit float PCM. Clean, sound-treated studio recording.
  - **Critical 1–20 Coverage Gap**: Searching all 200 transcripts revealed **0 isolated single-word numeral recordings**.
  - Numerals occur only embedded in multi-word sentences (e.g., *मोयोद* in a 4.59s technical sentence; *बारिया* in a 3.48s sentence).
  - Only 2 adult studio speakers are present. Primary grade school children (our core FLN demographic) have vastly different vocal tract lengths, pitch registers (250–400 Hz), and acoustic formants.
- **Full Corpus Status**:
  - While documented as containing 26,870 utterances across the same 2 speakers, access requires an individual application to `data@karya.in`. We possess only the SHA-1 checksum verification (`dataset-mundari-tts-full.sha1`).
  - **Verdict**: In accordance with scientific integrity, we do not claim access to data not physically present. The sample is classified as `PUBLIC + CONDITIONALLY USABLE` for audio preprocessor validation, VAD noise floor tuning, and pipeline integration tests. It is **unsuitable** as training data for our edge 1–20 numeral classifier.

#### Large-Scale Indian Speech Resources (Kathbath, Vistaar, Common Voice)
- We audited the official language inventories for AI4Bharat Kathbath, Vistaar, IndicSpeech, and Shruti.
- **Finding**: Mundari is an Austroasiatic (Munda) language, not an Indo-Aryan or Dravidian scheduled language. It is completely missing from these corpora.
- **Verdict**: Marked **`NOT SUFFICIENT FOR MUNDARI SPEECH`**. We strictly refuse to substitute Hindi or other languages as "pseudo-Mundari" training data.

---

### 2.2 Translation Data (Hindi ↔ Mundari)

#### Selected Primary Corpus: `dataset-hindi-mundari-translation`
- **Audit Findings**:
  - Raw TSV located at `data/raw/translation/translation-hi-unr.tsv` contains 17,826 lines.
  - Filtering malformed lines yielded 17,809 valid pairs.
  - Unicode NFC normalization and exact deduplication yielded **17,804 unique bilingual sentence pairs**.
  - Script: Consistently Devanagari for both Hindi and Mundari (`unr`).
  - Vocabulary: 16,878 distinct Hindi word types; 23,212 distinct Mundari word types.
- **Number Coverage in Translation Corpus**:
  - All numbers 1–20 are extensively represented in context (e.g., *मिअद* / *मियद* / *मोयोद* appears in 459 sentence pairs; *बारिया* in 276 pairs; *अपिया* in 143 pairs; *उपुनिया* in 98 pairs; *गेल* in 241 pairs).
- **Architectural Utilization**:
  - **Tier 1**: Does NOT rely on probabilistic corpus matching. Exact canonical forms are stored in `content/content_registry.json` for 100% deterministic lookup.
  - **Tier 2**: The 17,804 cleaned pairs form the offline TF-IDF character n-gram retrieval index. When similarity is $\ge 0.60$, attested sentences provide natural phrasing. When $< 0.60$, the engine strictly returns `OUT_OF_VOCABULARY_UNVERIFIED` with zero hallucination.
- **Decision**: **`PUBLIC + USABLE`**. Fully integrated into `data/processed/translation/clean_bilingual_corpus.tsv`.

---

### 2.3 Linguistic Reference Resources

1. **Hoffman's *Encyclopaedia Mundarica* (1930)**:
   - Evaluated for classical root validation. Confirms vigesimal structure (*mid*, *bar*, *api*, *upun*, *mōṛē*, *turui*, *ēyā*, *irili*, *ārē*, *gel*, *hisi* for 20).
   - Serves as etymological ground truth.
2. **Swaminathan's *Mundari Grammar* (CIIL Mysore, 1975)**:
   - Validates phoneme inventory: stops (/p, t, ʈ, c, k, ʔ/), nasals (/m, n, ɳ, ɲ, ŋ/), glottalization, and vowel harmony.
   - Used to formulate audio QA thresholds (duration ranges and frequency envelopes).
- **Decision**: Classified as **`REFERENCE ONLY`**.

---

### 2.4 Speech Synthesis (TTS) Resources

- **Role**: Pretrained synthetic TTS checkpoints may be utilized for prototype audio playback during development and unit test signal routing.
- **Strict Limitation**:
  - Synthetic TTS must **never** be evaluated as native ground truth.
  - Synthetic speech must **never** be used to claim speech recognition accuracy.
  - The presentation-safe 1–20 fallback strictly prioritizes certified human-reviewed native audio recordings when available.
- **Decision**: Classified as **`CONDITIONALLY USABLE (PROTOTYPE ONLY)`**.

---

## 3. What Must NOT Be Used

1. **Synthetic Speech as Model Training Data**: Forbidden. Training on synthetic audio creates acoustic artifacts and false confidence without reflecting real vocal physiology.
2. **Non-Mundari Indian Speech Corpora**: Forbidden to proxy Mundari with Santhali, Ho, or Hindi speech. Mundari has unique acoustic properties, phonemic glottal stops, and prosodic contours.
3. **Proprietary Cloud APIs Without Offline Fallback**: Cloud translation APIs cannot be the core engine for remote Jharkhand schools where internet connectivity is non-existent.
4. **Unvetted Competency Codes**: Inventing official NIPUN Bharat learning outcome codes without primary state curriculum documents is strictly forbidden.

---

## 4. Final Recommended Data Stack

The smallest, strongest, legally usable data stack for our independent system:

1. **Translation Engine (Tier 2 Corpus Retrieval)**:
   - Asset: `data/processed/translation/clean_bilingual_corpus.tsv` (17,804 verified, NFC-normalized pairs).
   - License: KPL BY-NC-SA-FS 1.0 (NonCommercial, FreeSoftware).
2. **Pedagogy & Deterministic Translation (Tier 1 Registry)**:
   - Asset: `content/content_registry.json` (21 classes, bilingual numerals, linguistic roots, attested variants).
   - Sourced from linguistic grammars, certified by educational framework.
3. **Acoustic Preprocessing & DSP Benchmarking**:
   - Asset: `data/raw/speech/data-sample/` (200 takes, studio clean, used for filterbank calibration and VAD baseline).
4. **Primary Speech Recognition Model Training**:
   - Asset: **Authentic Field Recordings Only**, collected via `ai/data_collection/field_session_packager.py` from native speakers (primary students & educators in Jharkhand).
   - *Current Status*: The model training gate is intentionally locked until authentic field bundles are ingested and reviewed.
