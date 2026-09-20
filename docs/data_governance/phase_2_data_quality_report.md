# Phase 2: Controlled Data Acquisition & Profiling Quality Report

**Project ID**: SIH260042  
**Application**: APP_NAME_PENDING (Vernacular FLN Assistant — Hindi ↔ Mundari)  
**Document Type**: Data Governance & Quality Audit  
**Phase**: Phase 2 — Governed Acquisition & Acoustic/Text Profiling  
**Status**: APPROVED & ENFORCED  
**Audit Date**: 2026-09-06  

---

## 1. Acquired Sources

The following external resources were acquired into governed staging spaces under strict provenance tracking:

1. **`SRC-PB-0240` (Pratham Books Story 0240: *Haikoah Gama*)**:
   - Files acquired: `mqu/0240_haikoah-gama.md` (3,612 bytes) and `hi/0240_machhliyon-ki-baarish.md`.
   - Staged location: Staged and structured into `data/incoming/pratham_0240_haikoah_gama.json` with accompanying `data/incoming/pratham_0240_license_manifest.json`.
   - Status: `DOWNLOADED_AND_STAGED` / `CANDIDATE_FOR_VALIDATION`.
2. **`SRC-KAR-TXT` (Karya Hindi–Mundari Translation Corpus)**:
   - Raw file: `translation-hi-unr.tsv` (3,788,450 bytes).
   - Staged location: Maintained in immutable isolated scratch storage; profiled into `data/incoming/karya_translation_profile.json`.
   - Status: `DOWNLOADED_AND_PROFILED` / `RESEARCH_ONLY`.
3. **`SRC-KAR-AUD` (Karya Mundari TTS Sample Audio Corpus)**:
   - Archive acquired: `data-sample.tgz` (64,560,322 bytes).
   - Extracted samples: 200 studio recordings (100 female, 100 male) with plain-text UTF-8 Mundari transcripts.
   - Derived evaluation assets: 5 resampled 16 kHz 16-bit mono evaluation WAVs in scratch space.
   - Profile staged: `data/incoming/karya_audio_sample_profile.json`.
   - Status: `DOWNLOADED_AND_PROFILED` / `RESEARCH_ONLY`.

---

## 2. Not Acquired Sources

The following sources were deliberately **NOT downloaded** or ingested into application repositories, following governance rules:

1. **`SRC-MML-01` (MMLoSo 2025 Shared Task `mundari-train.csv`)**:
   - **Reason**: Gated behind Kaggle competition login; underlying training text declared as a *"private, permissively licensed source"* without accessible primary license documentation or copyright clearance.
   - **Status**: `NOT_DOWNLOADED` / `DO_NOT_USE`.
2. **`SRC-BV-TB01..04` (Bharatavani Primary Textbooks)**:
   - *Munda Barnamala Bahi (Class I)*, *Mesabani Pothi (Class II)*, *Abuajagar Abuaha Kahani (Class III)*, *Mo Ganita Bahi (Class IV)*.
   - **Reason**: Gated behind `Login to Read` authentication walls on `sec.bharatavani.in`. State government (OSEPA) educational copyright; no open redistribution license stated. Automated extraction prohibited.
   - **Status**: `NOT_DOWNLOADED` / `REFERENCE_ONLY`.
3. **`SRC-BV-LL01..02` (Bharatavani Early Language Primers)**:
   - *Hone Koa Sida Kitab* and *Munda Jagar Itun Puthi*.
   - **Reason**: Login-restricted; in-copyright works.
   - **Status**: `NOT_DOWNLOADED` / `REFERENCE_ONLY`.
4. **`SRC-BV-DIC1..2` (Bharatavani Dictionaries & Idioms)**:
   - *Tungkodhari* Trilingual Dictionary and *Mundari Muhavara Kosh*.
   - **Reason**: In-copyright proprietary works accessible only via single-word interactive search widgets.
   - **Status**: `NOT_DOWNLOADED` / `REFERENCE_ONLY`.
5. **Karya Full TTS Corpus (17 GB / 26,870 files)**:
   - **Reason**: Private cloud storage requiring institutional request; only the public 200-sample archive was acquired.
   - **Status**: `NOT_DOWNLOADED` / `RESEARCH_ONLY`.

---

## 3. License-Confirmed Sources

| Source ID | Resource Title | Verified License | Rights & Permissions | Restrictions |
| :--- | :--- | :--- | :--- | :--- |
| **`SRC-PB-0240`** | Pratham Books *Haikoah Gama* | **CC-BY 4.0** | Commercial & non-commercial use, adaptation, translation, model training, redistribution | Attribution to Ramendra Kumar, Delwyn Remedios, Jodheswar Barla, and Pratham Books StoryWeaver required |
| **`SRC-KAR-TXT`** | Karya Hindi-Mundari Translation Corpus | **KPL BY-NC-SA-FS 1.0** | Non-commercial research, transformation, and offline model training | Non-commercial only; ShareAlike; incorporating software must be licensed under GNU GPL |
| **`SRC-KAR-AUD`** | Karya Mundari TTS Sample Corpus | **KPL BY-NC-SA-FS 1.0** | Non-commercial acoustic research, phonetic analysis, sample derivative processing | Non-commercial only; ShareAlike; incorporating software must be GPL; cannot be labeled educational ground truth |

---

## 4. License-Unclear Sources

| Source ID | Resource Title | Declared Status | Specific Legal Gaps Identified | Governed Classification |
| :--- | :--- | :--- | :--- | :--- |
| **`SRC-MML-01`** | MMLoSo 2025 `mundari-train.csv` | `LICENSE_UNCLEAR` | ACL Anthology findings paper notes CC BY-SA 4.0, but competition website cites an undisclosed "private source", and downloads require agreeing to Kaggle-specific competition terms. Underlying source permissions cannot be legally established. | **`DO_NOT_USE`** |
| **`SRC-BV-TB01..04`** | Bharatavani / OSEPA Textbooks | `LICENSE_UNCLEAR` | State government crown copyright (OSEPA / JCERT). While permissible for classroom instruction in government schools, no open license (CC or ODC) exists for software digitization. | **`REFERENCE_ONLY`** |
| **`SRC-BV-DIC1..2`** | Bharatavani Dictionaries | `LICENSE_UNCLEAR` | Private copyright owned by authors (Victor Horo, Mansidh Baraiud) licensed exclusively to CIIL. Bulk automated extraction is legally prohibited. | **`REFERENCE_ONLY`** |

---

## 5. Number of Files

- **Pratham Books Story Files**: 2 raw markdown files (`mqu_0240_haikoah-gama.md` [3,612 bytes], `hi_0240_machhliyon-ki-baarish.md` [1,540 bytes]); 1 candidate JSON dataset (`pratham_0240_haikoah_gama.json` [8 structured bilingual records]); 1 license manifest.
- **Karya Text Files**: 1 raw TSV dataset (`translation-hi-unr.tsv` [3.78 MB]); 1 profile report (`karya_translation_profile.json`).
- **Karya Audio Files**: 1 archive (`data-sample.tgz` [61.5 MB]); 200 raw WAV files; 200 plain text transcript files; 5 derived evaluation 16 kHz mono WAVs; 1 profile report (`karya_audio_sample_profile.json`).
- **Bharatavani Scraped Metadata Catalogs**: 15 book metadata records cataloged in `extracted_catalog.json`.

---

## 6. Number of Sentences

- **Pratham Books Story**: Exactly **8 aligned narrative sections / sentence units** (1 title pair + 7 narrative scene blocks).
- **Karya Translation Dataset**: **17,809 valid parallel sentence pairs** (17,826 raw lines minus 17 malformed lines).
  - Numeracy & counting subset: **2,333 sentence pairs** (13.1%).
  - Classroom / instructional subset: **88 sentence pairs** (0.5%).
  - Daily conversation & narrative: **15,388 sentence pairs** (86.4%).
- **Total Newly Profiled Parallel Sentences**: **17,817 sentence pairs**.

---

## 7. Number of Speakers

- **Pratham Books Story**: 0 audio speakers (written text only; 1 attested human translator: Jodheswar Barla).
- **Karya Translation Dataset**: Written text corpus collected across community workers via the Karya smartphone platform (multiple anonymous native contributors).
- **Karya TTS Audio Corpus**: Exactly **2 native speakers**:
  - **Speaker 1 (Female)**: Contributed 100 sample recordings (19,868 recordings in full corpus).
  - **Speaker 2 (Male)**: Contributed 100 sample recordings (7,002 recordings in full corpus).

---

## 8. Audio Statistics

Measured directly from the 200 extracted sample recordings:
- **Total WAV Files**: 200
- **Total Duration**: 741.72 seconds (**12.36 minutes**)
- **Duration Distribution**: Min = 1.97s, Max = 7.70s, **Average = 3.71s**
- **Original Format**: 44,100 Hz, 32-bit linear PCM, 1 Channel (Mono)
- **Recording Acoustic Environment**: Sound-treated room, high-grade studio condenser microphone and preamp
- **Transcripts**: 100% available (200 / 200 WAVs have matching `.txt` transcripts in Devanagari Mundari)
- **Derived Evaluation Copies**: 5 samples downsampled to **16,000 Hz, 16-bit Mono linear PCM WAV** in `scratch/karya_audio/derived_16k_mono/`.

---

## 9. Educational Relevance Assessment

| Asset Profile | Direct FLN Alignment | Grade Level | Utility Assessment |
| :--- | :--- | :---: | :--- |
| **Pratham Books *Haikoah Gama*** | Foundational Literacy & Story Reading | Grade 1–2 (Level 2) | **Immediate Educational Match**: Engages early learners with rich animal vocabulary (*चेड़े*, *बल्लू*, *हाईकोअ:*) and repetitive narrative structures. |
| **Karya Numeracy Subset (2,333 pairs)** | Foundational Numeracy (1–20) | Balvatika – Grade 2 | **High Value for Model Training**: Provides extensive syntactic variations for counting items, quantities, and word problems in Mundari. |
| **Karya TTS Audio Samples** | Acoustic Reference & Phonetics | All Primary Grades | **Phonetic Grounding**: Essential for benchmarking natural Mundari rhythm, glottal stops (*ah* / *ः*), and vowel lengthening. |
| **Bharatavani Textbooks** | Syllabus Structure & Phonics | Balvatika – Grade 4 | **Curriculum Baseline**: Official state sequence for letter introduction and pedagogical progression. |

---

## 10. Translation Quality Status

- **Pratham Books *Haikoah Gama***: **High**. Translated by an identified native speaker (Jodheswar Barla) for Pratham Books StoryWeaver. Idiomatic Mundari phrasing with correct verbal affixes (*-तन*, *-केना*, *-ए*).
- **Karya Translation Dataset**: **Moderate to High**. Collected via mobile micro-tasks from native Mundari speakers. 99.9% syntactically well-formed, but contains:
  - 22 verbatim identical sentences (untranslated Hindi proper nouns/places).
  - 2,865 sentences with non-NFC Devanagari character compositions (remediated via Unicode NFC pass).
  - Requires native educator filtering to separate adult/general topics from child-appropriate FLN vocabulary.

---

## 11. Linguistic Validation Status

In accordance with the Data Intake Contract:
- **`pratham_0240_haikoah_gama.json`**: Marked `CANDIDATE_FOR_VALIDATION` (passes 100% automated schema and NFC checks; awaits human native-linguist sign-off on IPA transcriptions).
- **`karya_translation_profile.json`**: Marked `RESEARCH_ONLY` / `KARYA_LICENSE_RESTRICTED`. Not submitted for canonical promotion.
- **`karya_audio_sample_profile.json`**: Marked `RESEARCH_ONLY` / `NOT_EDUCATIONAL_GROUND_TRUTH`.
- **Zero records** have been promoted to `CANONICAL_LOCKED` or `BROADCAST_SAFE`.

---

## 12. Data Leakage Risks

- **Evaluation Split Contamination**: If the 17,809 Karya sentence pairs or MMLoSo sentences are used to train external translation models, none of their sentences may overlap with our 20 canonical numerals or 16 canonical classroom phrases.
- **Cross-Source Contamination**: Pratham Books stories must be held separate from phrasebook evaluation test sets.

---

## 13. Speaker Leakage Risks

- **Karya TTS Acoustic Data**: The 200 sample recordings originate from exactly 2 speakers (1 female, 1 male).
- **Leakage Prevention**: If this data is ever utilized to train an acoustic or ASR model:
  - Speaker-level partitioning must be enforced (e.g. Female in `TRAIN`, Male in `TEST` or vice versa).
  - Under no circumstances may utterances from the female speaker appear in both training and test partitions.

---

## 14. Recommended Next Dataset

**Immediate Action**: Complete linguistic validation of **`pratham_0240_haikoah_gama.json`** using [`data/templates/human_validation_form.md`](file:///./data/templates/human_validation_form.md).  
Because it is fully aligned with Hindi, released under `CC-BY 4.0`, translated by Jodheswar Barla, and child-appropriate, it is the safest and most valuable candidate to advance from `data/incoming/` to `data/validated/`.

---

## 15. Blocked Items

| Resource | Blocker Category | Reason for Block |
| :--- | :--- | :--- |
| **MMLoSo Shared Task Data** | Licensing Ambiguity | Undisclosed "private source" origin and Kaggle competition restrictions conflict with open educational deployment. |
| **Bharatavani Textbooks** | Access Wall & Copyright | Requires login authentication; no open license declared; state government crown copyright. |
| **Bharatavani Dictionaries** | Proprietary Access | In-copyright works; widget lookup only; automated scraping legally prohibited. |
| **Full Karya TTS Audio (17 GB)** | Access Protocol | Requires formal email request to `data@karya.in`; public access restricted to sample archive. |
| **Commercial LLM Mundari Translations** | Fabrication / Hallucination | Strictly prohibited under `EXTERNAL_DATA_RULES.md`. |
