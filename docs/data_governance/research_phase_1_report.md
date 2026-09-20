# Research Phase 1: Controlled Mundari Educational Data Acquisition

**Project ID**: SIH260042  
**Application**: Bhasha Setu (Vernacular FLN Assistant — Hindi ↔ Mundari)  
**Report Type**: External Resource Acquisition & Feasibility Audit  
**Status**: APPROVED BASELINE  
**Audit Date**: 2026-09-06  

---

## A. Executive Summary

This document presents the comprehensive findings of **Research Phase 1: Controlled Mundari Educational Data Acquisition** for the SIH260042 Vernacular FLN Assistant.

In strict adherence to the project governance boundaries:
- **No external datasets or translations were promoted into canonical data** or production code.
- **External entities, publishers, and authors are treated exclusively as external data sources**, preserving attribution while keeping our application namespaces and identity completely independent (`Bhasha Setu`).
- Every surveyed resource was subjected to technical, linguistic, pedagogical, and legal rights evaluations to determine whether it can be safely staged into the **Data Intake Contract** pipeline (`data/incoming/` $\rightarrow$ `data/validated/`).

### Key Audit Findings
1. **Pratham Books / Global-ASP Story Corpus**: Exactly 1 high-quality, fully aligned bilingual story (`mqu/0240_haikoah-gama.md` / `hi/0240_machhliyon-ki-baarish.md`) is available under **`CC-BY 4.0`** with explicit human native-translator attribution (Jodheswar Barla). Status: **`PUBLIC_ACCESS` / `LICENSE_VERIFIED` / `CANDIDATE_FOR_VALIDATION`**.
2. **Karya Hindi-Mundari Translation Corpus**: 17,826 raw sentence pairs (17,809 valid rows, 28,590 unique Mundari words) licensed under **`KPL BY-NC-SA-FS 1.0`**. It contains 2,333 numeracy/counting sentences (13.1% of corpus), making it an invaluable resource for offline translation and vocabulary modeling. Because the license mandates GPL for incorporating software, it must be ingested as training/evaluation data for decoupled models rather than directly embedded into non-GPL application binaries. Status: **`PUBLIC_ACCESS` / `RESEARCH_ONLY` / `CANDIDATE_FOR_VALIDATION`**.
3. **MMLoSo 2025 Shared Task (IJCNLP-AACL 2025)**: 20,000 sentence pairs in `mundari-train.csv` released under **`CC BY-SA 4.0`** (per ACL Anthology proceedings). Download is gated behind Kaggle competition authentication. Status: **`ACCESS_RESTRICTED` / `CANDIDATE_FOR_VALIDATION`**.
4. **Bharatavani / CIIL Textbooks & Dictionaries**: 15 primary-school textbooks and linguistic reference works were cataloged (including OSEPA Class I Alphabet and Class II Language primers). All reading URLs on `sec.bharatavani.in` are **gated behind mandatory user authentication** (`Login to Read`). Status: **`ACCESS_RESTRICTED` / `RESEARCH_ONLY`**.
5. **Acoustic & Speech Data**: The Karya Mundari TTS corpus provides 26,870 recordings (~17 GB) across two native speakers (44.1 kHz 32-bit PCM), with a 100-sample preview repository available on GitHub. Status: **`PUBLIC_ACCESS` (Sample) / `ACCESS_RESTRICTED` (Full) / `RESEARCH_ONLY`**.

---

## B. Source Inventory

| Source ID | Resource Title | Primary Publisher / Curator | Modality | Volume / Size | Primary URL | Access Mode | License Status | Intake Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SRC-PB-01** | *Haikoah Gama* (Fish Rain) | Pratham Books / StoryWeaver | Text (Bilingual) | 7 scenes, ~212 words | `github.com/global-asp/pb-source/tree/master/mqu` | `PUBLIC_ACCESS` | `LICENSE_VERIFIED` (CC-BY 4.0) | `CANDIDATE_FOR_VALIDATION` |
| **SRC-KAR-01** | Hindi–Mundari Translation Corpus | Karya / MSR India / IIT KGP | Parallel Text | 17,809 valid pairs (3.78 MB) | `github.com/karya-inc/dataset-hindi-mundari-translation` | `PUBLIC_ACCESS` | `LICENSE_VERIFIED` (KPL BY-NC-SA-FS 1.0) | `CANDIDATE_FOR_VALIDATION` |
| **SRC-MML-01** | MMLoSo 2025 Shared Task Data | MMLoSo / MoTA / Kaggle | Parallel Text | 20,000 pairs (`mundari-train.csv`) | `kaggle.com/competitions/mmloso2025` | `ACCESS_RESTRICTED` | `LICENSE_VERIFIED` (CC BY-SA 4.0) | `CANDIDATE_FOR_VALIDATION` |
| **SRC-BV-TB01** | *Munda Barnamala Bahi, Class-I* | OSEPA / CIIL Bharatavani | Primary Textbook | ~40 pages (PDF) | `sec.bharatavani.in/mundari/textbook` | `ACCESS_RESTRICTED` | `LICENSE_UNCLEAR` (Govt Crown/OSEPA) | `RESEARCH_ONLY` |
| **SRC-BV-TB02** | *Mesabani Pothi, Class-II* | OSEPA / CIIL Bharatavani | Primary Textbook | ~60 pages (PDF) | `sec.bharatavani.in/mundari/textbook` | `ACCESS_RESTRICTED` | `LICENSE_UNCLEAR` (Govt Crown/OSEPA) | `RESEARCH_ONLY` |
| **SRC-BV-TB03** | *Abuajagar Abuaha Kahani, Class-III* | OSEPA / CIIL Bharatavani | Reader / Stories | ~50 pages (PDF) | `sec.bharatavani.in/mundari/textbook` | `ACCESS_RESTRICTED` | `LICENSE_UNCLEAR` (Govt Crown/OSEPA) | `RESEARCH_ONLY` |
| **SRC-BV-TB04** | *Mo Ganita Bahi, Class-IV* | OSEPA / CIIL Bharatavani | Math Textbook | ~80 pages (PDF) | `sec.bharatavani.in/mundari/textbook` | `ACCESS_RESTRICTED` | `LICENSE_UNCLEAR` (Govt Crown/OSEPA) | `RESEARCH_ONLY` |
| **SRC-BV-LL01** | *Hone Koa Sida Kitab (Children's 1st Book)* | CIIL Bharatavani / Author | Early Reader | Unknown | `sec.bharatavani.in/mundari/bhashakosha` | `ACCESS_RESTRICTED` | `LICENSE_UNCLEAR` | `RESEARCH_ONLY` |
| **SRC-BV-LL02** | *Munda Jagar Itun Puthi* | CIIL Bharatavani / Author | Learning Primer | Unknown | `sec.bharatavani.in/mundari/bhashakosha` | `ACCESS_RESTRICTED` | `LICENSE_UNCLEAR` | `RESEARCH_ONLY` |
| **SRC-BV-DIC1** | *Tungkodhari: Mundari-English-Hindi Dictionary* | Man Masih Mundu / Victor Horo | Trilingual Lexicon | Full Lexicon | `bharatavani.in/mundari/dictionaries` | `ACCESS_RESTRICTED` | `LICENSE_UNCLEAR` (In-Copyright) | `RESEARCH_ONLY` |
| **SRC-BV-DIC2** | *Mundari Muhavara Kosh* | Mansidh Baraiud / K.K. Pub. | Idiom Dictionary | Full Lexicon | `bharatavani.in/mundari/dictionaries` | `ACCESS_RESTRICTED` | `LICENSE_UNCLEAR` (In-Copyright) | `RESEARCH_ONLY` |
| **SRC-KAR-AUD** | Mundari TTS Acoustic Corpus | Karya / MSR India / IIT KGP | Native Audio (WAV) | 26,870 wavs (~17 GB, 2 speakers) | `github.com/karya-inc/dataset-mundari-tts` | `PUBLIC_ACCESS` (Sample) | `LICENSE_VERIFIED` (KPL BY-NC-SA-FS 1.0) | `RESEARCH_ONLY` |

---

## C. Educational Textbook Sources (Bharatavani / OSEPA)

Our technical inspection of `sec.bharatavani.in/mundari/textbook` extracted the full book catalog. Every textbook listed below is an official primary educational resource:

### 1. Primary School Textbooks Catalog
1. **`Munda Barnamala Bahi, Class-I`**
   - **Class**: Class I
   - **Subject**: Alphabet & Early Literacy
   - **Publisher**: Odisha School Education Programme Authority (OSEPA), Bhubaneswar, Odisha
   - **Publication Year**: 2013
   - **Source URL**: `https://sec.bharatavani.in/mundari/book?post_category=text-book&id=Munda%20Barnamala%20Bahi%2C%20Class-I`
   - **Accessibility**: Gated behind `https://sec.bharatavani.in/home/login?id=Munda Barnamala Bahi, Class-I` (`Login to Read`).
   - **Copyright / License**: Government / Institutional Copyright (OSEPA / CIIL). Open public reuse license is not declared.
   - **Educational Usefulness**: **Critical**. Authoritative benchmark for Class I letter formation, phonics, and initial tribal vocabulary.

2. **`Mesabani Pothi, Class-II`**
   - **Class**: Class II
   - **Subject**: Language & Early Reading
   - **Publisher**: OSEPA, Bhubaneswar
   - **Publication Year**: 2009
   - **Source URL**: `https://sec.bharatavani.in/mundari/book?post_category=text-book&id=Mesabani%20Pothi%2C%20Class-II`
   - **Accessibility**: Requires Bharatavani login.
   - **Educational Usefulness**: High. Class II foundational sentences, vocabulary extension, and simple dialogues.

3. **`Abuajagar Abuaha Kahani, Class-III`**
   - **Class**: Class III | **Subject**: Language & Folklore | **Publisher**: OSEPA | **Year**: 2013
   - **Accessibility**: Login restricted.
   - **Educational Usefulness**: High. Folk narratives and cultural reading comprehension.

4. **`Bhasa Sikhiba, Class-III`** & **`Hedem Jagar, Class-III`**
   - **Class**: Class III | **Subject**: Language Acquisition | **Publisher**: OSEPA | **Year**: 2013
   - **Accessibility**: Login restricted.

5. **`Aabuha Hatu, Class-III`** & **`Abua Mulikuti Jagar, Class-III`**
   - **Class**: Class III | **Subject**: Environmental Studies (EVS / Our Village) | **Publisher**: OSEPA | **Year**: 2013
   - **Educational Usefulness**: Village life, nature, domestic animals, and social science terms.

6. **`Mo Ganita Bahi, Class-IV`**
   - **Class**: Class IV | **Subject**: Mathematics | **Publisher**: OSEPA | **Year**: 2013
   - **Educational Usefulness**: Math vocabulary, operations, geometric terms, and counting beyond 20.

7. **`Hone Koa Sida Kitab (Bachchon Ki Pratham Pustak)`**
   - **Category**: Language Learning (`bhashakosha`)
   - **Subject**: Children's First Book / Balvatika Early Childhood Care & Education (ECCE)
   - **Accessibility**: Login restricted.
   - **Educational Usefulness**: **Extreme**. Direct alignment with Balvatika / Grade 1 NIPUN Bharat foundation.

### Textbook Reusability Assessment
- **Text Extraction Feasibility**: PDFs are viewable only within the Bharatavani reader post-login. Automated scraping is prohibited by Bharatavani terms of use.
- **Bilingual Availability**: Textbooks published by OSEPA are designed for mother-tongue schooling and are primarily monolingual Mundari (in Odia or Devanagari script). Hindi glosses exist only in select teacher handbooks.
- **Legal Posture**: **`ACCESS_RESTRICTED` / `RESEARCH_ONLY`**. Cannot be directly downloaded or parsed by automated tools without institutional CIIL / OSEPA clearance.

---

## D. Story & Reading Sources (Pratham Books / Global-ASP)

Inspected from repository: `https://github.com/global-asp/pb-source`

### Story Corpus Inspection Details
- **Exact File**: `mqu/0240_haikoah-gama.md` (3,612 bytes)
- **Title**: *हाईकोअ: गमा* (Haikoah Gama / The Day It Rained Fish)
- **Parallel Hindi Story**: `hi/0240_machhliyon-ki-baarish.md` (*मछलियों की बारिश*)
- **Parallel English Story**: `en/0240_the-day-it-rained-fish.md` (*The Day It Rained Fish*)
- **Total Mundari Stories Available in Repo**: Exactly 1 story (Story ID: 0240).
- **Text Volume**: 7 markdown section scenes, 32 lines, ~212 words, 1,328 characters of authentic Mundari text.
- **Alignment**: Perfect structural page-by-page alignment between `mqu` and `hi` via markdown `##` delimiters.
- **Reading Level**: Pratham Books Level 2 (Early Reader / Grade 1–2).
- **Provenance & Authorship**:
  - Author / Story: Ramendra Kumar
  - Illustrator: Delwyn Remedios
  - Translator: Jodheswar Barla (attested human native-speaker translation)
  - Publisher: Pratham Books / StoryWeaver
- **License**: **`CC-BY 4.0`** (Creative Commons Attribution 4.0 International).
- **Reusability & Attribution**: Fully permitted for commercial and non-commercial educational reuse, derivative works, and model training. Requires explicit attribution to Pratham Books StoryWeaver, author, illustrator, and translator.
- **Intake Recommendation**: **`CANDIDATE_FOR_VALIDATION`**. Can immediately be converted to `data/incoming/pb_haikoah_gama.json` adhering to `parallel_translation.schema.json`.

---

## E. Dictionary & Linguistic Sources

Inspected from `https://bharatavani.in/mundari/dictionaries` and `https://sec.bharatavani.in/mundari/bhashakosha`:

### 1. Authoritative Dictionaries Catalog
1. **`टुङकोढारि अर्थात् मुण्डारी शब्दकोश | Mundari Dictionary (Mundari-English-Hindi)`**
   - **Author**: Man Masih Mundu | **Publisher / Content Partner**: Victor Horo, Ranchi, Jharkhand (2017)
   - **Languages**: Trilingual (Mundari, Hindi, English)
   - **Format**: Digital dictionary browser available at `https://bharatavani.in//mundari/dictionarysurf/?did=268&language=Mundari`.
   - **Usefulness**: Gold-standard trilingual reference for Mundari root morphemes, parts of speech, and standard Devanagari spellings.
2. **`मुण्डारी मुहावरा कोश | Mundari Muhavara Kosh`**
   - **Author**: Mansidh Baraiud | **Publisher**: K.K. Publications, Allahabad
   - **Languages**: Bilingual (Mundari, Hindi)
   - **Usefulness**: Idiomatic expressions, colloquial classroom phrases, and cultural metaphors.
3. **`सुबोध मुण्डारी व्याकरण | Subodh Mundari Veyakaran`**
   - **Author**: Radhagovind Patar | **Publisher**: Jharkhand Jharokha, Ranchi (2017)
   - **Focus**: Systematic Devanagari Mundari grammar, noun cases, and verbal inflections.
4. **`हिंदी और मुण्डारी भाषा के व्याकरण का तुलनात्मक विवेचन`**
   - **Author**: Dr. Jindar Singh Munda | **Publisher**: Parikrama Prakashan, Delhi (2017)
   - **Focus**: Contrastive Hindi-Mundari grammar, postpositions, and tense alignments.
5. **`Mundari Grammar`**
   - **Author**: N. K. Sinha | **Publisher**: CIIL Mysore (1975)
   - **Focus**: Academic linguistic description of Hasada dialect phonology and morphology.

### Dictionary Legal & Technical Assessment
- **Machine Readability**: The Bharatavani search widget (`dictionarysurf/?did=268`) allows single-word manual lookups. Raw dictionary databases or downloadable CSVs are not provided.
- **Copyright Status**: All works are under active individual or publisher copyright licensed exclusively to CIIL Bharatavani. Bulk extraction without express permission violates terms of service.
- **Intake Status**: **`RESEARCH_ONLY`**. Permitted for manual lookup and linguistic verification of disputed words by human evaluators, but prohibited from bulk automated ingestion.

---

## F. Translation Datasets

### 1. Karya Hindi–Mundari Translation Corpus (`SRC-KAR-01`)
- **Repository**: `github.com/karya-inc/dataset-hindi-mundari-translation`
- **Curators**: Microsoft Research India, IIT Kharagpur, Karya Inc., GIZ FAIR Forward.
- **Raw File**: `translation-hi-unr.tsv` (3,788,450 bytes)
- **Detailed Statistical Profiling**:
  - **Total Raw Lines**: 17,826
  - **Valid Sentence Pairs**: 17,809
  - **Malformed Lines**: 17 (rows with missing or extra tab delimiters)
  - **Exact Duplicate Pairs**: 5
  - **Verbatim Identical Pairs (Untranslated Proper Nouns)**: 22 (e.g. `'राजेश लोहिया पडरौना कुशीनगेर यू पी'`)
  - **Hindi Total Tokens**: 141,238 (unique vocabulary: 20,551 words)
  - **Mundari Total Tokens**: 131,360 (unique vocabulary: 28,590 words)
  - **Unicode Normalization**: 0 non-NFC Hindi sentences; **2,865 non-NFC Mundari sentences** (requires automated NFC pass).
  - **Control Characters**: 0 illegal characters found.
  - **Sentence Length Distribution**:
    - Hindi: Min 2 words, Max 11 words, Average 7.93 words.
    - Mundari: Min 0 words, Max 22 words, Average 7.38 words.
    - Breakdown: 1–3 words (3 pairs), 4–7 words (7,287 pairs), 8–15 words (10,519 pairs), 16+ words (0 pairs).
  - **Domain Breakdown**:
    - General Narrative & Daily Conversation: 14,461 pairs (81.2%)
    - **Numeracy & Counting**: 2,333 pairs (13.1%)
    - Family & Social Life: 367 pairs (2.1%)
    - Civic & Healthcare: 288 pairs (1.6%)
    - Education & Schooling: 187 pairs (1.1%)
    - Agriculture & Rural Economy: 173 pairs (1.0%)
- **Licensing Terms (`KPL BY-NC-SA-FS 1.0`)**:
  - **Non-Commercial**: Commercial exploitation prohibited.
  - **Attribution**: Must attribute DAIA Tech Pvt Ltd, MSR India, IIT Kharagpur, Karya, and GIZ FAIR Forward.
  - **ShareAlike**: Adaptations must carry identical licensing.
  - **Free Software (Copyleft)**: Incorporating software systems must be licensed under the GNU General Public License (GPL).
- **Project Incorporation Posture**:
  - Excellent for offline training of auxiliary NMT or embedding models.
  - To avoid imposing GPL encumbrance on the core application, the dataset should be maintained as an external training asset rather than compiled directly into the application bundle.

### 2. MMLoSo 2025 Shared Task Corpus (`SRC-MML-01`)
- **Workshop**: First International Workshop on Multimodal Models for Low-Resource Contexts and Social Impact (MMLoSo 2025 @ IJCNLP-AACL 2025, Mumbai).
- **Target File**: `mundari-train.csv` (20,000 sentence pairs).
- **Structure**: Columns `row_id`, `hindi`, `mundari`.
- **License**: Formally published under **`CC BY-SA 4.0`** (Creative Commons Attribution-ShareAlike 4.0 International) as documented in the ACL Anthology findings paper.
- **Access Gating**: Hosted via Kaggle (`kaggle.com/competitions/mmloso2025/data`), which requires Kaggle login authentication.
- **Intake Status**: **`CANDIDATE_FOR_VALIDATION` (Subject to Kaggle Account Auth)**.

---

## G. Speech & Audio Resources

### 1. Karya Mundari TTS Corpus (`SRC-KAR-AUD`)
- **Curators**: Microsoft Research India, IIT Kharagpur, Karya Inc.
- **Format**: 32-bit linear PCM WAV at 44.1 kHz (studio quality).
- **Volume**: 26,870 utterances (~17 GB) from 2 native speakers (1 male, 1 female).
- **Availability**:
  - Public sample repository: `github.com/karya-inc/dataset-mundari-tts` (100 audio samples per speaker).
  - Full corpus: Hosted on cloud storage, accessible upon request via `data@karya.in`.
- **License**: `KPL BY-NC-SA-FS 1.0`.
- **Educational Value**: High potential for synthesizing high-fidelity, native-accented audio prompts for FLN exercises, but requires downsampling to 16 kHz 16-bit mono for mobile Android deployment.

### 2. MunTTS Acoustic Modeling System
- **Repository**: `github.com/microsoft/MunTTS-A-Text-to-Speech-System-For-Mundari`
- **Publication**: *MunTTS: A Text-to-Speech System for Mundari* (ACL Anthology / arXiv).
- **Implementation**: Scripts for phonetic segmentation, grapheme-to-phoneme (G2P), and acoustic model fine-tuning.

---

## H. License & Access Matrix

| Source ID | Publicly Viewable? | Direct File Download? | Formal License | Non-Commercial Only? | Model Training Allowed? | Derivative Works Allowed? | Overall Legal / Technical Status |
| :--- | :---: | :---: | :--- | :---: | :---: | :---: | :--- |
| **SRC-PB-01** (Pratham Books) | **YES** | **YES** | **CC-BY 4.0** | NO (Free for all) | **YES** | **YES** | **`PUBLIC_ACCESS` / `LICENSE_VERIFIED` / `CANDIDATE_FOR_VALIDATION`** |
| **SRC-KAR-01** (Karya Text) | **YES** | **YES** | **KPL BY-NC-SA-FS 1.0** | **YES** (NC) | **YES** | **YES** (SA+GPL) | **`PUBLIC_ACCESS` / `LICENSE_VERIFIED` / `CANDIDATE_FOR_VALIDATION`** |
| **SRC-MML-01** (MMLoSo CSV) | **YES** | Gated (Kaggle) | **CC BY-SA 4.0** | NO | **YES** | **YES** (SA) | **`ACCESS_RESTRICTED` / `LICENSE_VERIFIED` / `CANDIDATE_FOR_VALIDATION`** |
| **SRC-BV-TB01..04** (OSEPA Textbooks) | Gated (Login) | Gated (Reader) | **Govt / OSEPA Crown** | Undefined | **NO** | **NO** | **`ACCESS_RESTRICTED` / `LICENSE_UNCLEAR` / `RESEARCH_ONLY`** |
| **SRC-BV-LL01..02** (Early Primers) | Gated (Login) | Gated (Reader) | **In-Copyright** | Undefined | **NO** | **NO** | **`ACCESS_RESTRICTED` / `LICENSE_UNCLEAR` / `RESEARCH_ONLY`** |
| **SRC-BV-DIC1..2** (Dictionaries) | Gated (Widget) | **NO** | **In-Copyright** | Undefined | **NO** | **NO** | **`ACCESS_RESTRICTED` / `LICENSE_UNCLEAR` / `RESEARCH_ONLY`** |
| **SRC-KAR-AUD** (Karya Audio) | Sample (Yes) / Full (No) | Cloud Request | **KPL BY-NC-SA-FS 1.0** | **YES** (NC) | **YES** | **YES** (SA+GPL) | **`ACCESS_RESTRICTED` / `LICENSE_VERIFIED` / `RESEARCH_ONLY`** |

---

## I. Data Quality Assessment

| Quality Dimension | Pratham Books (`SRC-PB-01`) | Karya Corpus (`SRC-KAR-01`) | MMLoSo Corpus (`SRC-MML-01`) | Bharatavani Textbooks (`SRC-BV-TB`) |
| :--- | :--- | :--- | :--- | :--- |
| **Script Hygiene** | 100% Devanagari script, standard Mundari orthography | 100% Devanagari script. 2,865 sentences require NFC normalization pass. | Devanagari script, pre-curated for NLP benchmarks | Devanagari & Odia scripts depending on publication year |
| **Structural Integrity** | Flawless markdown structure, 100% page aligned | 99.9% clean (17 malformed lines out of 17,826; 5 duplicate pairs) | Tabular CSV (`row_id`, `hindi`, `mundari`) | Scanned raster PDFs inside browser reader |
| **Vocabulary Diversity** | ~212 words, child-friendly narrative vocabulary | 28,590 unique Mundari vocabulary items; rich morphological representation | ~20,000 sentence pairs; high type-token ratio | Foundational pedagogical vocabulary aligned with primary school syllabi |
| **Phonetic Notation** | None (requires IPA phonetic mapping pass) | None (orthographic text only) | None (orthographic text only) | None (textbook orthography) |
| **Acoustic Parity** | No audio attached | Audio available separately via Karya TTS (44.1 kHz) | Text-only benchmark | No audio attached |

---

## J. Educational Relevance Assessment

| Pedagogical Domain | Target Audience | Source Match | Educational Utility |
| :--- | :--- | :--- | :--- |
| **Foundational Numeracy (1–20)** | Balvatika – Grade 1 | Karya Corpus (2,333 pairs contain number words); OSEPA *Mo Ganita Bahi* | **Very High**: Enables comprehensive number word coverage, counting chants, and bilingual word problem prompts. |
| **Foundational Literacy (Class I Alphabet)** | Balvatika – Grade 1 | OSEPA *Munda Barnamala Bahi*; *Hone Koa Sida Kitab* | **Critical Reference**: Essential for establishing authentic phonics, sound-symbol correspondence, and initial consonant clusters. |
| **Bilingual Story Reading** | Grade 1 – Grade 3 | Pratham Books *Haikoah Gama* (`SRC-PB-01`); OSEPA *Abuaha Kahani* | **Immediate Candidate**: Perfectly paced early-grade narrative with high child engagement and animal vocabulary. |
| **Classroom Instruction Commands** | Teachers & Students | Karya Conversational subset; *Mundari Muhavara Kosh* | **High**: Elicits authentic polite imperatives and daily classroom discourse. |

---

## K. Recommended Acquisition Order

Based on legal permissiveness, data cleanliness, and educational relevance:

1. **Step 1: Pratham Books *Haikoah Gama* (`SRC-PB-01`)**
   - **Reason**: 100% verified `CC-BY 4.0` license, perfect parallel Hindi alignment, early-reader level, human translator verified.
   - **Action**: Stage into `data/incoming/pb_haikoah_gama.json` via `parallel_translation.schema.json`.
2. **Step 2: Karya Hindi–Mundari Numeracy Subset (`SRC-KAR-01`)**
   - **Reason**: 2,333 sentence pairs covering foundational mathematics and numbers. Licensed under `KPL BY-NC-SA-FS 1.0`.
   - **Action**: Run automated NFC normalization and filter out malformed lines (17 rows) and duplicate rows (5 rows); stage as external evaluation/training asset.
3. **Step 3: MMLoSo 2025 Shared Task Dataset (`SRC-MML-01`)**
   - **Reason**: 20,000 sentence pairs under `CC BY-SA 4.0` benchmarked at IJCNLP-AACL 2025.
   - **Action**: Obtain authenticated access via Kaggle and stage into `data/incoming/` for validator profiling.
4. **Step 4: Karya Mundari TTS Audio Samples (`SRC-KAR-AUD`)**
   - **Reason**: Verified native speaker recordings (1 male, 1 female).
   - **Action**: Acquire sample WAVs, downsample to 16 kHz 16-bit mono, verify SNR $\ge 15.0$ dB, and evaluate acoustic quality.
5. **Step 5: Formal Institutional Outreach to CIIL / OSEPA (`SRC-BV-TB`)**
   - **Reason**: Official primary school primers (*Munda Barnamala Bahi* and *Mesabani Pothi*) are the ultimate curriculum benchmarks.
   - **Action**: Request formal academic / educational research clearance from CIIL Bharatavani for non-commercial FLN pedagogical usage.

---

## L. Blocked & Unclear Sources

The following resources must **NOT** be ingested into active datasets at this time:

| Blocked Resource | Reason for Block | Remediation Required |
| :--- | :--- | :--- |
| **Bharatavani Online Dictionaries (Bulk Extraction)** | In-copyright proprietary works. Gated behind interactive widget. Scraping violates CIIL Bharatavani Terms of Service. | Maintain strictly as manual linguistic reference. Do NOT attempt automated web scraping. |
| **Bharatavani OSEPA Textbooks (PDFs)** | Login authentication wall (`Login to Read`). Copyright belongs to state educational boards (OSEPA/JCERT) without declared open license. | Formal memorandum or institutional request to CIIL/OSEPA required before automated ingestion. |
| **Commercial LLM Translations** | Unattested commercial MT outputs hallucinate low-resource Munda morphology. | Strictly banned under `EXTERNAL_DATA_RULES.md`. |
| **Web-Scraped Blogs / Social Media** | Unverified dialect provenance, inconsistent orthography, and missing copyright grants. | Excluded from intake. |

---

## M. Next-Step Acquisition Checklist

To transition from Research Phase 1 to Controlled Ingestion:

- [x] Complete technical and legal catalog of external resources.
- [ ] Stage `SRC-PB-01` (Pratham Books *Haikoah Gama*) into `data/incoming/pb_0240_haikoah_gama.json` adhering to `parallel_translation.schema.json`.
- [ ] Create `data/incoming/pb_0240_license_manifest.json` recording CC-BY 4.0 attribution to Jodheswar Barla and Pratham Books.
- [ ] Run `python tools/data_intake/validator.py data/incoming/pb_0240_haikoah_gama.json` to verify zero schema violations.
- [ ] Filter, clean, and NFC-normalize the 2,333 numeracy sentence pairs from `SRC-KAR-01`.
- [ ] Submit candidate records to native Mundari educator for pedagogical alignment review using `data/templates/human_validation_form.md`.
- [ ] Confirm that no unapproved or non-canonical records enter `content/content_registry.json` or the Android APK assets.
