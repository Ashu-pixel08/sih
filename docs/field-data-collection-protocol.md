# SIH260042: Field Data Collection Protocol
**Project**: AI-Powered Vernacular Pedagogy and Real-Time Translation Tool for Mother Tongue-Based Primary Education  
**Target Language**: Mundari (`unr`) — Jharkhand Primary Education (Ranchi, Khunti, West Singhbhum)  
**Domain**: Foundational Literacy & Numeracy (FLN) Speech Data Acquisition  
**Document Version**: 1.0.0  
**Status**: APPROVED FIELD SPECIFICATION  

---

## 1. Objectives & Scope of Field Collection

The primary objective is to acquire high-fidelity, native-speaker acoustic data for the Mundari language to replace baseline/pipeline models with an authentically trained edge speech component.

### 1.1 First Controlled Vocabulary Scope (MVP)
The immediate focus is the Grade 1 FLN Numeracy domain:
- **Numerals 1 to 20** in isolated single-word utterances.
- **Numerals 1 to 20** embedded in pedagogical carrier phrases.
- **Class 0 (`_background_`)**: Classroom environmental noise, desk sounds, fan hum, and non-target speech.

### 1.2 Extensible Multi-Domain Architecture
The collection framework is explicitly structured to expand into future vernacular educational domains without altering metadata schemas or pipeline tooling:
- **Domain 2**: Primary Classroom Instructions (*दुबपे*, *तिंगुपे*, *नेलपे*, *लेकापे*, *ओलपे*, *काजी आलोपे*).
- **Domain 3**: Basic Colors & Geometric Shapes (Mundari descriptive vocabulary).
- **Domain 4**: Common Animals, Plants, and Daily Life objects (Tribal context).
- **Domain 5**: Continuous conversational Mundari speech for general ASR.

---

## 2. Prompt Lists & Candidate Mundari Lexical Forms

### 2.1 Numerals 1–20 (Candidate Forms from Validated Corpus)

> [!CAUTION]
> **Linguistic Status Note**: All forms below are **CORPUS_ATTESTED** candidate forms. Final educational canonicalization must be performed by local Mundari primary educators prior to final model release.

| Class Index | Label ID | Numeral | Candidate Mundari Text | Attested Root | Phonetic (IPA/Latin) | Known Morphological Variants | Carrier Prompt Example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 1 | `num_01` | 1 | मिअद | मिद | `miad` | मियद, मिद, मोयोद, मोसा | नेआ मिअद तना (*This is one*) |
| 2 | `num_02` | 2 | बारिया | बार | `baria` | बरिया, बार, बारे | नेआ बारिया तना (*This is two*) |
| 3 | `num_03` | 3 | आपिया | आपि | `apia` | अपिया, आपि, आपे | नेआ आपिया तना (*This is three*) |
| 4 | `num_04` | 4 | उपुनिय़ा | उपुन | `upunia` | उपूनिया, उपुन | नेआ उपुनिय़ा तना (*This is four*) |
| 5 | `num_05` | 5 | मोड़ेया | मोड़े | `modea` | मोंड़ेया, मोड़े | नेआ मोड़ेया तना (*This is five*) |
| 6 | `num_06` | 6 | तुरूइया | तुरूइ | `turuia` | तुरुइया, तुरूइ | नेआ तुरूइया तना (*This is six*) |
| 7 | `num_07` | 7 | एय़ा | एय़ा | `eya` | एया, एइया | नेआ एय़ा तना (*This is seven*) |
| 8 | `num_08` | 8 | इरलिय़ा | इरल | `iralia` | इरिलिया, इरल | नेआ इरलिय़ा तना (*This is eight*) |
| 9 | `num_09` | 9 | अरेया | अरे | `area` | आरेया, अरे | नेआ अरेया तना (*This is nine*) |
| 10 | `num_10` | 10 | गेलिय़ा | गेल | `gelia` | गेलिया, गेल | नेआ गेलिय़ा तना (*This is ten*) |
| 11 | `num_11` | 11 | गेल मिअद | गेल | `gel miad` | गेलमियद, गेलमिद | नेआ गेल मिअद तना |
| 12 | `num_12` | 12 | गेल बारिया | गेल | `gel baria` | गेलबरिया, गेलबार | नेआ गेल बारिया तना |
| 13 | `num_13` | 13 | गेल आपिया | गेल | `gel apia` | गेलापिया, गेलापि | नेआ गेल आपिया तना |
| 14 | `num_14` | 14 | गेल उपुनिय़ा | गेल | `gel upunia` | गेलउपुन | नेआ गेल उपुनिय़ा तना |
| 15 | `num_15` | 15 | गेल मोड़ेया | गेल | `gel modea` | गेलमोड़े | नेआ गेल मोड़ेया तना |
| 16 | `num_16` | 16 | गेल तुरूइया | गेल | `gel turuia` | गेलतुरुइ | नेआ गेल तुरूइया तना |
| 17 | `num_17` | 17 | गेल एय़ा | गेल | `gel eya` | गेलएया | नेआ गेल एय़ा तना |
| 18 | `num_18` | 18 | गेल इरलिय़ा | गेल | `gel iralia` | गेलइरल | नेआ गेल इरलिय़ा तना |
| 19 | `num_19` | 19 | गेल अरेया | गेल | `gel area` | गेलअरे | नेआ गेल अरेया तना |
| 20 | `num_20` | 20 | हिसि | हिसि | `hisi` | बार हिसि, इसि, कुड़ी | नेआ हिसि तना (*This is twenty*) |

### 2.2 Pedagogical Carrier Phrases
To train robust models that do not overfit to artificial isolated acoustic boundaries, 25% of tokens must be collected in authentic pedagogical carrier frames:
1. **Frame A (Demonstrative)**: `नेआ [संख्या] तना` (*nea [number] tana* — "This is [number]")
2. **Frame B (Choral counting)**: `मिदते काजीपे [संख्या]` (*midte kajipe [number]* — "Speak together: [number]")
3. **Frame C (Counting prompt)**: `लेकापे [संख्या]` (*lekape [number]* — "Count: [number]")

---

## 3. Speaker Diversity Plan

### 3.1 Why Speaker Diversity is Critical
Speech models trained on small speaker pools memorize fundamental frequency ($F_0$), vocal tract formant spacing, and speaker idiosyncrasies rather than phonological features:
- **Adult Females (Teachers & Mothers)**: Typical $F_0 \approx 180 - 240$ Hz. Crucial because primary school teachers in Jharkhand are predominantly female.
- **Adult Males (Teachers & Elders)**: Typical $F_0 \approx 90 - 140$ Hz. Broader resonance, longer vocal tract length ($~17$ cm).
- **Primary School Children (Ages 6–8)**: Typical $F_0 \approx 260 - 380$ Hz. Shorter vocal tract ($~10-12$ cm), higher formants ($F_1, F_2$ shifted upwards by 20–30%), and developing articulatory precision. Models trained only on adults fail catastrophically on child primary students.

### 3.2 Target Demographic Cohort (Minimum 30 Speakers)

| Speaker Group | Age Range | Target Count | Location Target | Rationale |
| :--- | :---: | :---: | :--- | :--- |
| **Primary School Children (Girls)** | 6 – 8 yrs (Grade 1–2) | **8 speakers** | Khunti / Murhu / Torpa | Direct end-user demographic; child acoustic properties |
| **Primary School Children (Boys)** | 6 – 8 yrs (Grade 1–2) | **8 speakers** | Khunti / Murhu / Torpa | Direct end-user demographic; child pitch variability |
| **Adult Native Females** | 20 – 50 yrs | **8 speakers** | Primary teachers, Anganwadi workers | Model teacher instruction voice; standard MTB-MLE pronunciation |
| **Adult Native Males** | 20 – 60 yrs | **6 speakers** | Primary teachers, community elders | Acoustic diversity; low pitch register |
| **TOTAL** | — | **30 speakers** | Rural Jharkhand primary schools | Statistically viable pool for speaker-disjoint evaluation |

---

## 4. Repetition Matrix & Dataset Volume

To capture natural intra-speaker variability (variations in vocal effort, pitch inflection, and recording session fatigue), recordings are collected across two separate sessions.

### 4.1 Repetition Plan
- **Isolated Numerals**: 6 repetitions per number per speaker (3 in Session 1, 3 in Session 2).
- **Carrier Phrases**: 2 repetitions per carrier phrase per speaker.
- **Total per Speaker**: $(20 \times 6) + (20 \times 2) = 160$ number utterances.

### 4.2 Master Recording Volume Projection

$$\text{Total Target Utterances} = 30 \text{ speakers} \times 160 \text{ utterances} = \mathbf{4,800 \text{ target speech tokens}}$$
$$\text{Background Acoustic Segments} = 30 \text{ sessions} \times 40 \text{ segments} = \mathbf{1,200 \text{ environmental tokens}}$$
$$\text{Total Curated Corpus} = \mathbf{6,000 \text{ audio assets}}$$

### 4.3 Identifier Scheme
Every audio recording is tagged with a deterministic identifier:
`REC_{DOMAIN}_{SPEAKER_ID}_{CLASS_ID}_REP{XX}.wav`

Examples:
- `REC_FLN_SPK_C04_NUM07_REP01.wav` (Child speaker 4, number 7, repetition 1)
- `REC_FLN_SPK_F02_NUM12_REP05.wav` (Female speaker 2, number 12, repetition 5)
- `REC_ENV_SPK_M01_BG00_REP03.wav` (Classroom background recording)

---

## 5. Dataset Partitioning (Strictly Speaker-Disjoint)

To ensure true generalizability and prevent over-optimistic evaluation metrics, the dataset must be split **across speakers**, ensuring zero speaker overlap between splits.

| Split | Percentage | Speaker Allocation | Total Speakers | Utterance Tokens | Purpose |
| :--- | :---: | :--- | :---: | :---: | :--- |
| **TRAIN** | **66.7%** | 5 Adult Female, 4 Adult Male, 11 Children | **20 speakers** | ~3,200 | Model training |
| **VALIDATION** | **16.7%** | 2 Adult Female, 1 Adult Male, 2 Children | **5 speakers** | ~800 | Hyperparameter tuning, early stopping |
| **TEST** | **16.7%** | 1 Adult Female, 1 Adult Male, 3 Children | **5 speakers** | ~800 | Final unbiased performance assessment |

> [!IMPORTANT]
> **Leakage Prevention Rules**:
> 1. **Zero Speaker Leakage**: No speaker appearing in `TRAIN` may ever appear in `VALIDATION` or `TEST`.
> 2. **Zero Augmentation Leakage**: Augmented audio files (SpecAugment, pitch shift, noise injection) must ONLY be generated from `TRAIN` recordings. Validation and Test must strictly evaluate raw, unaugmented authentic recordings.

---

## 6. Ethics, Privacy & Child Protection Protocol

Because this project engages rural primary school children, the field team must adhere to strict ethical and legal safeguards:
1. **Institutional Permissions**: Official approval from the Jharkhand Department of School Education and Literacy (DoSEL), local Block Education Officers (BEO), and School Management Committees (SMC).
2. **Informed Parental & Community Consent**: Written or audio-recorded informed consent from parents or legal guardians in Mundari or Hindi explaining the educational purpose of the research.
3. **Anonymization & Zero PII**:
   - No names, Aadhaar numbers, school registration numbers, or facial photos may be stored with audio files.
   - All speakers are identified exclusively via random alphanumeric IDs (`SPK_C01`, `SPK_F03`).
4. **Child-Friendly Data Collection**:
   - Sessions are capped at **10 to 12 minutes** to prevent vocal fatigue and distraction.
   - Collection is structured as an interactive flashcard game conducted in the presence of familiar female primary teachers.
   - Children may withdraw participation at any point without penalty.
5. **Data Security**: Recordings are stored on encrypted offline physical drives (AES-256) and never uploaded to unvetted public cloud storage without institutional data governance agreements.

---

## 7. Standardized Data Directory Hierarchy

```
data/
├── raw/
│   ├── speech/
│   │   ├── session_01/
│   │   │   ├── SPK_C01/
│   │   │   │   ├── REC_FLN_SPK_C01_NUM01_REP01.wav
│   │   │   │   └── ...
│   │   │   └── ...
│   │   └── background/
│   │       ├── REC_ENV_CLASSROOM_FAN_01.wav
│   │       └── REC_ENV_CLASSROOM_TAPS_01.wav
│   └── manifests/
│       └── raw_field_manifest.json
├── metadata/
│   ├── recording_manifest.schema.json
│   ├── speaker_demographics.json (Anonymized)
│   └── linguistic_review_log.json
├── processed/
│   ├── wav_16k_mono/
│   └── spectrograms/
└── splits/
    ├── train.json
    ├── validation.json
    └── test.json
```
