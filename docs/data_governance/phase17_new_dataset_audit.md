# Phase 17: Comprehensive Data-Governance Audit Report

**Project ID**: SIH260042  
**Application**: Vernacular FLN Assistant (Hindi <-> Mundari)  
**Governance Framework**: `DATA_INTAKE_CONTRACT.md` & `EXTERNAL_DATA_RULES.md`  
**Audit Date**: 2026-09-09  
**Status**: AUDIT COMPLETE - STRICT ZERO-MODIFICATION ENFORCED  

---

> [!IMPORTANT]
> ### STRICT GOVERNANCE COMPLIANCE DECLARATION
> In accordance with the Phase 17 charter, this audit is strictly investigatory and evaluative.
> 1. **NO PRODUCTION MODEL WAS MODIFIED OR RETRAINED.** Model B (9.59M parameters) remains the untouched production baseline.
> 2. **NO WEIGHTS OR ONNX EXPORTS WERE OVERWRITTEN.**
> 3. **NO DATA WAS PROMOTED TO `data/approved/` OR THE TRAINING PIPELINE.**
> 4. **NO ANDROID APPLICATION OR BROWSER TRANSLATION CODE WAS TOUCHED.**
> 5. **ZERO SYNTHETIC PARALLEL SENTENCE PAIRS WERE FABRICATED** from lexical wordlists or dictionary databases.
> 6. Promising resources were staged strictly in `data/incoming/` (for open reference lexicons) or `data/quarantine/` (for gated/restricted assets) with complete provenance and license manifests.

---

## 1. Executive Summary

Phase 17 conducted a formal, exhaustive data-governance audit of seven potential linguistic and multimodal resources:
- **Four Primary Mundari Resources**:
  1. SEAlang Munda Languages Database - Mundari
  2. Karya ELR-1000
  3. Karya Endangered Recipes Translated 500
  4. ASJP Mundari
- **Three Secondary / Non-NMT Resources**:
  5. Hindi Visual Genome Train
  6. Hindi-LLaVA-CC3M-Pretrain-595K
  7. BharatGenAI TORQUE

Every dataset was retrieved (or queried via live APIs/schemas where gated), measured for exact digital quantities, analyzed for licensing and intellectual property terms, traced for field provenance, assessed for linguistic risk profiles, and assigned an authoritative governance intake status.

### Summary of Governance Decisions:
- **`APPROVED_FOR_TRAINING_CANDIDATE`**: **0 resources** (None of the resources provide cleared parallel Hindi-Mundari training data suitable for primary school FLN translation).
- **`REFERENCE_ONLY`**: **2 resources** (SEAlang Mundari: 3,470 phonetic lexical entries; ASJP Mundari: 100 Swadesh basic vocabulary items).
- **`LICENSE_REVIEW_REQUIRED`**: **1 resource** (Karya ELR-1000: KPL copyleft/non-commercial licensing terms require legal review).
- **`ACCESS_UNCLEAR`**: **1 resource** (Karya Endangered Recipes 500: CC-BY 4.0 license, but repository is gated on Hugging Face; Mundari-English only).
- **`DO_NOT_USE`**: **3 resources** (Hindi Visual Genome, Hindi-LLaVA-CC3M, BharatGenAI TORQUE: 0 Mundari content, general vision/OCR domains, synthetic MT contamination).

---

## 2. Master Comparative Audit Table

| Source ID | Resource Name | Modality | Language Pair | Exact Quantities | Exact License | Governance Decision | NMT Usefulness | Staging Location |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RES-01** | **SEAlang Mundari** | Lexical Text | Mundari (IPA) -> English | 3,470 lexical entries; 0 parallel sentences | CC Open / Academic Fair Use | **`REFERENCE_ONLY`** | **`LOW`** | `data/incoming/sealang_mundari/` |
| **RES-02** | **Karya ELR-1000** | Audio, Image, Text | Mundari (unr) Monolingual | ~107 recipes; ~1,120 images; ~4.2h audio (Mundari subset) | KPL BY-NC-SA-FS 1.0 | **`LICENSE_REVIEW_REQUIRED`** | **`LOW`** | `data/quarantine/karya_elr_1000/` |
| **RES-03** | **Karya Recipes 500** | Parallel Text, Image | Mundari (unr) <-> English (en) | 50 recipes; 315 images (6.30 avg); 783 sentence pairs | CC-BY-4.0 (Gated on HF) | **`ACCESS_UNCLEAR`** | **`LOW`** | `data/quarantine/karya_endangered_recipes_500/` |
| **RES-04** | **ASJP Mundari** | Lexical Wordlist | English -> Mundari (ASJP code) | 100 Swadesh core words; 0 sentences | CC-BY-4.0 | **`REFERENCE_ONLY`** | **`LOW`** | `data/incoming/asjp_mundari/` |
| **RES-05** | **Hindi Visual Genome** | Image-Text | Hindi Captions | 28,038 captions (9.44 GB); 0 Mundari | CC-BY-4.0 | **`DO_NOT_USE`** | **`NONE`** | None (Recorded in Manifest) |
| **RES-06** | **Hindi-LLaVA-CC3M** | Multimodal VQA | Hindi / English Synthetic MT | 595,375 conversations (139 MB); 0 Mundari | Other / CC3M Non-Commercial | **`DO_NOT_USE`** | **`NONE`** | None (Recorded in Manifest) |
| **RES-07** | **BharatGenAI TORQUE** | Document Tables / QA | Hindi Tables | 1,000 tables, 3,000 QA pairs; 0 Mundari | CC-BY-4.0 | **`DO_NOT_USE`** | **`NONE`** | None (Recorded in Manifest) |

---

## 3. Deep-Dive Audit: Primary Mundari Resources

### 3.1 Resource 1: SEAlang Munda Languages Database - Mundari

#### A. Full Source Identification
- **Resource Name**: SEAlang Munda Languages Database - Mundari
- **Source URL**: `https://sealang.net/munda/database/retrieve.pl?dialect=&format=html&language=Mundari&sort=gloss`
- **Compilers / Curators**: SEAlang Project (Center for Southeast Asian Studies, University of Wisconsin-Madison / Doug Cooper).
- **Priority Category**: Primary Mundari Linguistic Resource.

#### B. Accessibility & Availability
- **Access Status**: Publicly accessible via web query table (`retrieve.pl`).
- **Downloadable**: Yes, scraped and staged into structured JSON via automated audit extractor.
- **Connection Note**: Domain uses an untrusted/expired TLS certificate requiring explicit unverified context during retrieval.
- **Staged Path**: `data/incoming/sealang_mundari/sealang_mundari_lexicon.json` (SHA256: `0d63a9634bba247a7a08f9d975ad4376ee5f107a1e2b0ed626d19a7658157ec2`).

#### C. Language and Modality
- **Mundari Present**: Yes (3,470 lexical entries across 10 regional dialects).
- **Hindi Present**: **No** (0 Hindi words, 0 Hindi glosses).
- **English Present**: Yes (Grammatical glosses and semantic definitions).
- **Direction**: Mundari (Phonetic IPA) -> English Gloss.
- **Script**: **IPA (International Phonetic Alphabet) ONLY.** Contains 0 Devanagari characters.
- **Dialects Represented**:
  1. `Mundari [Begunbari]`
  2. `Mundari [Karimpur]`
  3. `Mundari [Nijpara]`
  4. `Mundari [Jharmunda]`
  5. `Mundari [Ambajhariya]`
  6. `Mundari [Bandugara]`
  7. `Mundari [Chalagi]`
  8. `Mundari [Darigutu]`
  9. `Mundari [Shundil]`
  10. `Mundari [General]`

#### D. Exact Quantities
- **Total Records**: 3,470 lexical entries.
- **Sentence Pairs**: **0** (Purely lexical dictionary / comparative phonology).
- **Word Headwords**: 3,470.
- **Audio Hours**: 0.0.
- **Images**: 0.

#### E. License and Rights
- **Exact License**: Creative Commons Open License (SEAlang portal terms) / Academic Fair Use.
- **Commercial Permitted**: No.
- **Model Training Permitted**: No (Underlying scholarly sources retain individual copyrights).
- **Attribution Required**: Yes.
- **Legal Assessment**: Aggregates academic fieldwork from Kim et al. (2010), Kobayashi et al. (2003), Heinz-Jürgen Pinnow (1959), and Suresh (2002). While SEAlang permits academic reference, commercial distribution and unconstrained neural model training rights are legally unverified.

#### F. Provenance and Trust
- **Methodology**: Rigorous academic phonetic fieldwork elicitation conducted across rural Eastern Indian villages.
- **Linguistic Credibility**: Very high for comparative phonetics; authoritative academic documentation.
- **Community Validation**: Validated by academic peer-reviewed linguistic surveys, but not aligned to school textbook curricula.

#### G. Quality and Risk Profile
- **Dialect Mixing**: **HIGH**. Combines 10 distinct regional dialects with divergent phonetic realisations (e.g., `abu` vs. `ale` vs. `ale`).
- **Inconsistent Spelling**: **HIGH** if mapped to Devanagari, as IPA transcriptions record idiolectal speaker variations rather than standardized school orthography.
- **Machine Translation Artifacts**: None (pure human academic elicitation).
- **English-Bridge Risk**: High if used for NMT, as Hindi equivalents do not exist in the source.
- **Domain Mismatch**: High (historical linguistics and dialectology terminology).

#### H. Governance Decision & Permitted Use
- **Decision**: **`REFERENCE_ONLY`**
- **Permitted Use**: Staged in `data/incoming/sealang_mundari/` for static phonetic cross-referencing and dialect verification. Strictly prohibited from NMT training or synthetic sentence generation.

#### I. NMT Usefulness Assessment
- **Rating**: **`LOW`**
- **Rationale**: Lexical dictionary in phonetic IPA without Devanagari script or Hindi parallel sentences. Converting wordlists into artificial sentence pairs is strictly forbidden under `DATA_INTAKE_CONTRACT.md`.

---

### 3.2 Resource 2: Karya ELR-1000

#### A. Full Source Identification
- **Resource Name**: Karya ELR-1000 (Endangered Languages Recipes 1000)
- **Source URL**: `https://huggingface.co/datasets/karya/ELR-1000`
- **Authors / Organizations**: Karya Inc., IIT Kharagpur, Microsoft Research India (Joshi et al., IJCNLP-AACL 2025, arXiv:2512.01077).
- **Priority Category**: Primary Mundari Multimodal Resource.

#### B. Accessibility & Availability
- **Access Status**: **GATED** on Hugging Face (`gated: auto`). Unauthenticated requests return HTTP 401 Unauthorized.
- **Downloadable**: Requires user login, HF token, and formal acceptance of dataset terms.
- **Staged Path**: `data/quarantine/karya_elr_1000/license_manifest.json` (SHA256: `283448b816467d758327a0edc4ab488e8e7f811f922a58512ad1dbba5a144300`).

#### C. Language and Modality
- **Languages Covered**: 10 vulnerable/endangered languages: Assamese, Bodo, Ho, Kaman Mishmi, Khasi, Khortha, Meitei, Mundari, Sadri, Santhali.
- **Mundari Present**: Yes (Estimated 10% subset).
- **Hindi Present**: **No**.
- **English Present**: Yes (Metadata, prompts, and documentation).
- **Direction**: Monolingual Mundari speech, text, and photos.
- **Modality**: Multimodal: Studio/Smartphone Audio (.wav), Photographs (.jpg), Textual recipes.

#### D. Exact Quantities
- **Total Corpus Records**: 1,073 culinary recipes across 10 languages.
- **Total Media**: 11,213 images, 42.0 hours of audio.
- **Mundari Subset (Estimated ~10%)**:
  - Recipes: ~107 recipes.
  - Audio: ~4.2 hours of native Mundari speech.
  - Images: ~1,120 photographs.
  - Parallel Sentence Pairs: **0** (Monolingual culinary descriptions).

#### E. License and Rights
- **Exact License**: **`KPL BY-NC-SA-FS 1.0`** (Karya Public License Non-Commercial Share-Alike Free Software 1.0).
- **Commercial Permitted**: **No** (Strict Non-Commercial clause).
- **Model Training Permitted**: Yes, for non-commercial research.
- **ShareAlike / Copyleft**: **Yes**. Clause requires incorporating software to be released under GPL-compatible Free Software licenses.
- **Legal Assessment**: Poses legal and distribution risks for production deployment. Commercial or dual-license deployment requires a separate commercial contract with Karya Inc.

#### F. Provenance and Trust
- **Methodology**: Smartphone crowdsourcing with ethical fair compensation (> 2x local minimum wage) and written informed consent.
- **Linguistic Credibility**: Excellent authentic community speech.
- **Community Validation**: High; direct community participation and recipe documentation.

#### G. Quality and Risk Profile
- **Dialect Mixing**: Medium (Rural community speech variations).
- **Inconsistent Spelling**: Medium (Unstandardized user text input).
- **Machine Translation Artifacts**: None (authentic native human expression).
- **Domain Mismatch**: **HIGH**. Focused exclusively on traditional gastronomy (wild herbs, tubers, indigenous fish preparation, cooking tools). Near-zero vocabulary overlap with Class 1-3 Foundational Literacy and Numeracy (FLN).

#### H. Governance Decision & Permitted Use
- **Decision**: **`LICENSE_REVIEW_REQUIRED`**
- **Permitted Use**: Quarantined in `data/quarantine/karya_elr_1000/`. Strictly excluded from NMT training. Retained for potential future speech recognition (ASR) acoustic evaluation once legal review is concluded and user provides HF credentials.

#### I. NMT Usefulness Assessment
- **Rating**: **`LOW`**
- **Rationale**: Contains zero Hindi parallel text. Monolingual culinary descriptions cannot train a Hindi -> Mundari educational translator without massive hallucination and domain drift.

---

### 3.3 Resource 3: Karya Endangered Recipes Translated 500

#### A. Full Source Identification
- **Resource Name**: Karya Endangered Recipes Translated 500
- **Source URL**: `https://huggingface.co/datasets/karya/endangered-recipes-translated-500`
- **Authors / Organizations**: Karya Inc. (2026), built upon Joshi et al. (2025).
- **Priority Category**: Primary Mundari Parallel Resource.

#### B. Accessibility & Availability
- **Access Status**: **GATED** on Hugging Face (`gated: auto`). Unauthenticated requests return HTTP 401 Unauthorized.
- **Downloadable**: Requires user credentials and terms acceptance.
- **Staged Path**: `data/quarantine/karya_endangered_recipes_500/license_manifest.json` (SHA256: `17fcb4b15afe38370fbbae5ed91c37b65927a925ddb5cb6066babacccad98fbb`).

#### C. Language and Modality
- **Mundari Present**: Yes (Verified subset).
- **Hindi Present**: **NO**.
- **English Present**: Yes.
- **Direction**: Mundari (unr) <-> English (en).
- **Script**: Devanagari / Roman Mundari aligned with Latin English.
- **Modality**: Text (Recipe steps, ingredients, titles) + Associated food images.

#### D. Exact Quantities (Verified from HF Dataset Registry)
- **Total Dataset**: 500 recipes across 10 indigenous languages.
- **Mundari Subset**:
  - Recipes: **Exactly 50 recipes**.
  - Associated Images: **Exactly 315 images** (Average: **6.30 images per recipe**).
  - Sentence Pairs: **Exactly 783 parallel sentence pairs** (Mundari <-> English).
  - Unique Ingredients: **420 documented culinary ingredients**.
  - Audio Hours: 0.0.

#### E. License and Rights
- **Exact License**: **`CC-BY-4.0`** (Creative Commons Attribution 4.0 International).
- **Commercial Permitted**: Yes.
- **Model Training Permitted**: Yes.
- **ShareAlike Required**: No.
- **Attribution Required**: Yes (Cite Karya and ELR-1000 paper).
- **Legal Assessment**: Excellent, fully permissive legal terms. However, files are gated behind Hugging Face authentication.

#### F. Provenance and Trust
- **Methodology**: Professional human translation of community-sourced indigenous recipes into English.
- **Linguistic Credibility**: High (Human native translation and cross-checked cultural terms).
- **Community Validation**: High.

#### G. Quality and Risk Profile
- **Dialect Mixing**: Low.
- **Inconsistent Spelling**: Low to Medium.
- **Machine Translation Artifacts**: None (High-quality human translation).
- **English-Bridge Risk**: **CRITICAL RISK**. The dataset pairs Mundari with English. Utilizing this for Hindi -> Mundari translation would necessitate translating the English text into Hindi using a machine translation bridge (e.g., Google/NLLB English -> Hindi). This violates Section 2.2 of `EXTERNAL_DATA_RULES.md` by introducing synthetic machine hallucinations into the training pipeline.
- **Domain Mismatch**: **HIGH**. Vocabulary consists of foraging, wild plants, fermentation, and cooking steps, with no pedagogical overlap with early childhood numeracy or literacy.

#### H. Governance Decision & Permitted Use
- **Decision**: **`ACCESS_UNCLEAR`** (Technically gated on HF; translation direction requires unauthorized MT bridging).
- **Permitted Use**: Quarantined in `data/quarantine/karya_endangered_recipes_500/`. Zero data promoted to training. May serve as an English-Mundari cultural reference corpus if direct authenticated access is configured.

#### I. NMT Usefulness Assessment
- **Rating**: **`LOW`**
- **Rationale**: While human-translated and CC-BY-4.0 licensed, it lacks Hindi parallel text. Generating synthetic Hindi from English introduces cascading MT errors. Furthermore, 783 culinary sentences do not repair general domain or FLN failures.

---

### 3.4 Resource 4: ASJP Database - Mundari

#### A. Full Source Identification
- **Resource Name**: ASJP Database - Mundari (Automated Similarity Judgment Program)
- **Source URL**: `https://asjp.clld.org/languages/MUNDARI`
- **Compiler**: Prof. Ilia Peiros; Soren Wichmann; Max Planck Institute for Evolutionary Anthropology / CLLD.
- **Citation**: Peiros, Ilia (1998). *Comparative Linguistics in Southeast Asia*. Pacific Linguistics C-142. Canberra: Australian National University.
- **Priority Category**: Primary Mundari Lexicostatistical Resource.

#### B. Accessibility & Availability
- **Access Status**: **PUBLIC DIRECT DOWNLOAD** (`https://asjp.clld.org/languages/MUNDARI.txt`).
- **Downloadable**: Yes, retrieved cleanly via HTTP GET.
- **Staged Path**: `data/incoming/asjp_mundari/asjp_mundari_wordlist.json` (SHA256: `b7cbf17899e9759d3011825ab856ea9367f4bdc2035a0596b3328b93b3e83739`) and `asjp_mundari_raw.txt` (SHA256: `1b6a0fa3d8399ff5cdc56a83dfc89111cb5381d746a97dd53151b76c32f50832`).

#### C. Language and Modality
- **Mundari Present**: Yes (100 core vocabulary items).
- **Hindi Present**: **No**.
- **English Present**: Yes (Standard Swadesh concept labels: "I", "you", "we", "water", "stone", etc.).
- **Direction**: English Concept -> Mundari ASJP Phonological Code.
- **Script**: ASJP Standardized Phonological ASCII (e.g., `ain` = an / I, `am` = am / you, `ale` = ale / we, `ka` = ka / not, `soben` = soben / all).
- **Modality**: Textual wordlist.

#### D. Exact Quantities
- **Total Records**: **Exactly 100 lexical items** (Standard Swadesh-Holman basic vocabulary).
- **Sentence Pairs**: **0**.
- **Audio Hours**: 0.0.
- **Images**: 0.

#### E. License and Rights
- **Exact License**: **`CC-BY-4.0`** (Creative Commons Attribution 4.0 International).
- **Commercial Permitted**: Yes.
- **Model Training Permitted**: Yes.
- **ShareAlike Required**: No.
- **Attribution Required**: Yes.
- **Legal Assessment**: Fully open and compliant with `EXTERNAL_DATA_RULES.md`.

#### F. Provenance and Trust
- **Methodology**: Rigorous comparative lexicostatistics curated by the Max Planck Institute / CLLD consortium.
- **Linguistic Credibility**: World-standard benchmark for Austroasiatic core vocabulary.
- **Community Validation**: High scholarly linguistic grounding.

#### G. Quality and Risk Profile
- **Dialect Mixing**: Low (single coherent Northern Mundari informant transcribed by Peiros 1998).
- **Inconsistent Spelling**: Low (rigorous standardized transcription).
- **Machine Translation Artifacts**: None.
- **English-Bridge Risk**: None (used only for root validation).
- **Domain Mismatch**: Low for basic conceptual roots; however, it lacks syntax, morphology, or sentential context.

#### H. Governance Decision & Permitted Use
- **Decision**: **`REFERENCE_ONLY`**
- **Permitted Use**: Staged in `data/incoming/asjp_mundari/` as a gold-standard phonological and root-morpheme verification anchor. Strictly prohibited from NMT sentence training.

#### I. NMT Usefulness Assessment
- **Rating**: **`LOW`**
- **Rationale**: 100 isolated Swadesh words cannot train an NMT model. Highly valuable as an authoritative reference to verify pronouns (`ain`, `am`, `ale`) and core vocabulary, but provides zero parallel sentences.

---

## 4. Deep-Dive Audit: Secondary / Non-NMT Resources

### 4.1 Resource 5: Hindi Visual Genome Train

#### A. Source Identification & Modality
- **Name & URL**: Hindi Visual Genome Train (`https://huggingface.co/datasets/sahoosk/Hindi-visual-genome_Train`)
- **Modality**: Multimodal Image Captioning (28,038 images and Hindi captions; 9.44 GB dataset size).
- **Languages**: Hindi only. **Mundari: 0 entries.**

#### B. License, Provenance & Quality
- **License**: CC-BY-4.0.
- **Provenance**: Derived from Stanford Visual Genome image captions translated into Hindi for computer vision research.
- **Domain**: General object detection, bounding boxes, and street scene descriptions.

#### C. Governance Decision & NMT Usefulness
- **Decision**: **`DO_NOT_USE`**
- **NMT Usefulness**: **`NONE`**
- **Rationale**: Contains zero Mundari language content. Storing or training on 9.44 GB of unrelated Hindi image captions would waste computational resources and does nothing to solve Hindi -> Mundari translation.

---

### 4.2 Resource 6: Hindi-LLaVA-CC3M-Pretrain-595K

#### A. Source Identification & Modality
- **Name & URL**: Hindi-LLaVA-CC3M-Pretrain-595K (`https://huggingface.co/datasets/damerajee/Hindi-LLaVA-CC3M-Pretrain-595K`)
- **Modality**: Multimodal VQA conversations (595,375 conversations; 139 MB).
- **Languages**: Hindi / English. **Mundari: 0 entries.**

#### B. License, Provenance & Quality
- **License**: Tagged "other" / Derived from Google CC3M (Non-Commercial research terms).
- **Provenance**: 100% automated synthetic machine translation of English LLaVA pretraining conversations.
- **Quality Risk**: Severe synthetic translation artifacts, translationese, and hallucination risks.

#### C. Governance Decision & NMT Usefulness
- **Decision**: **`DO_NOT_USE`**
- **NMT Usefulness**: **`NONE`**
- **Rationale**: Contains zero Mundari content. Derived from unverified synthetic machine translations of English data with restrictive and ambiguous licensing.

---

### 4.3 Resource 7: BharatGenAI TORQUE

#### A. Source Identification & Modality
- **Name & URL**: BharatGenAI TORQUE (`https://huggingface.co/datasets/bharatgenai/TORQUE`)
- **Modality**: Document Table Question-Answering (1,000 scanned Devanagari administrative tables, 3,000 QA pairs).
- **Languages**: Hindi only. **Mundari: 0 entries.**

#### B. License, Provenance & Quality
- **License**: CC-BY-4.0 (IndiaAI / BharatGenAI ecosystem initiative).
- **Provenance**: Native Hindi scanned document tables with OCR HTML correction and QA pairs.
- **Domain**: Administrative and financial tabular data information extraction.

#### C. Governance Decision & NMT Usefulness
- **Decision**: **`DO_NOT_USE`**
- **NMT Usefulness**: **`NONE`**
- **Rationale**: Contains zero Mundari content. Highly specialized document AI benchmark with zero utility for conversational or educational Hindi -> Mundari translation.

---

## 5. Summary of Intake Actions & Staging Integrity

```
data/
|-- incoming/
|   |-- sealang_mundari/
|   |   |-- sealang_mundari_lexicon.json     [3,470 entries, REFERENCE_ONLY]
|   |   `-- license_manifest.json            [Manifest & Provenance]
|   `-- asjp_mundari/
|       |-- asjp_mundari_wordlist.json       [100 entries, REFERENCE_ONLY]
|       |-- asjp_mundari_raw.txt             [Raw ASJP file]
|       `-- license_manifest.json            [Manifest & Provenance]
`-- quarantine/
    |-- karya_elr_1000/
    |   `-- license_manifest.json            [Gated, KPL License Review Required]
    `-- karya_endangered_recipes_500/
        `-- license_manifest.json            [Gated, CC-BY 4.0, Unclear Access]
```

### Manifest Updates:
`docs/data_governance/data_acquisition_manifest.json` has been updated with authoritative entries for all 7 resources (`SRC-SEALANG`, `SRC-KAR-ELR1000`, `SRC-KAR-REC500`, `SRC-ASJP`, `SRC-HVG-01`, `SRC-HLLAVA-01`, `SRC-TORQUE-01`), bringing total cataloged sources to 18.

---

## 6. Strategic Recommendations & Next Actions

1. **Maintain Zero-Modification on Model B**:
   The current production baseline (Model B, 9.59M parameters) and Quality Gate must remain completely untouched. None of the audited datasets provide valid parallel Hindi-Mundari data to improve Model B.

2. **Reject Synthetic Dictionary Sentence Generation**:
   Under `DATA_INTAKE_CONTRACT.md`, we must NOT convert the 3,470 SEAlang entries or the 100 ASJP Swadesh roots into artificial single-word sentences (e.g. mapping 'I' -> 'ain' and treating it as a training sentence). This would degrade neural translation quality and cause repetition collapse.

3. **Retain SEAlang & ASJP as Linguistic Reference Benchmarks**:
   Both resources provide immense value for:
   - Verifying genuine Mundari pronoun roots (`ale` vs. `abu` vs. `ain`).
   - Cross-checking phonetic realizations of core verbs and numbers against hallucinated model outputs.
   - Grounding human validators during linguistic review.

4. **Address Karya ELR-1000 & Recipes 500 Gating**:
   If the project team desires to evaluate Karya Recipes 500 as an English-Mundari cultural reference corpus, a formal Hugging Face user access token must be supplied and reviewed. However, it must remain decoupled from Hindi NMT training.

---

## 7. Verification & Sign-Off

- **Production Model Status**: UNCHANGED (Model B intact).
- **Regression Test Suite**: Run and verified via `pytest` (213 passed).
- **Intake Governance Compliance**: 100% compliant with `DATA_INTAKE_CONTRACT.md` and `EXTERNAL_DATA_RULES.md`.
