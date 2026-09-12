# Data Sources, References, and Legal Attribution

This document maintains strict records of all external data sources, research references, and licensing constraints utilized in this project. In accordance with project governance, these external materials serve strictly as research inputs and training datasets, and do not define the architecture, naming, or identity of this project.

---

## 1. Primary Text Translation Dataset

- **Original Dataset Name**: Hindi to Mundari Translation Dataset Corpus
- **Origin / Source Repository**: `https://github.com/karya-inc/dataset-hindi-mundari-translation`
- **Creators / Contributing Organizations**: 
  - Microsoft Research India
  - Indian Institute of Technology Kharagpur (IIT Kharagpur)
  - Karya Inc. / DAIA Tech Pvt Ltd
  - Indo-German Development Cooperation project "FAIR Forward – Artificial Intelligence for all" (implemented by GIZ on behalf of BMZ)
- **Copyright**: © 2023 DAIA Tech Pvt Ltd
- **License**: Karya Public License Attribution-NonCommercial-ShareAlike-FreeSoftware 1.0 (KPL BY-NC-SA-FS 1.0)
  - **Summary**: Allows non-commercial reuse, remixing, adapting, and incorporation into software systems.
  - **Mandatory Terms**:
    1. **Attribution (BY)**: Appropriate credit must be preserved.
    2. **NonCommercial (NC)**: Only non-commercial use is permitted.
    3. **ShareAlike (SA)**: Any adaptations or remixing must be shared under identical terms.
    4. **FreeSoftware (FS)**: Any software incorporating this dataset must be licensed under the GNU General Public License (GPL).
- **Physical Content**: 17,826 lines in TSV format (`translation-hi-unr.tsv`), size: 3.78 MB.
- **Audit Findings**:
  - Valid sentence pairs: 17,809
  - Malformed / empty lines: 17
  - Duplicate pairs: 5
  - Script: Devanagari script for both Hindi and Mundari (ISO 639-3 language code: `unr` for Mundari).
- **Usage in System**:
  - Ground-truth reference for Hindi–Mundari vocabulary and grammar.
  - Mining educational terminology and linguistic alignment.
  - Training/evaluating offline retrieval and translation engines.

---

## 2. Primary Speech Dataset

- **Original Dataset Name**: Mundari TTS Dataset Corpus
- **Origin / Source Repository**: `https://github.com/karya-inc/dataset-mundari-tts`
- **Creators / Contributing Organizations**: 
  - Microsoft Research India
  - Indian Institute of Technology Kharagpur (IIT Kharagpur)
  - Karya Inc. / DAIA Tech Pvt Ltd
  - GIZ / FAIR Forward / BMZ
- **Copyright**: © 2023 DAIA Tech Pvt Ltd
- **License**: KPL BY-NC-SA-FS 1.0 (Attribution-NonCommercial-ShareAlike-FreeSoftware 1.0)
- **Full Corpus Specifications (Reported)**:
  - 26,870 total recordings across two speakers (19,868 female, 7,002 male).
  - Recorded in sound-treated studio with high-quality microphone/preamp.
  - Sampling format: 44.1 kHz, 1-channel mono, 32-bit PCM.
  - Total corpus size: ~17 GB uncompressed (~7 GB compressed).
  - Access: Full dataset requires direct request via `data@karya.in`.
- **Public Sample Dataset (Audited Locally)**:
  - Archive: `data-sample.tgz` (64.5 MB).
  - Total audio files: 200 WAV recordings (100 female, 100 male).
  - Accompanying text transcripts: 200 UTF-8 files in Devanagari script.
  - Total duration: 12.36 minutes (average utterance: ~3.7 seconds).
  - Transcript matching: 100% ID correspondence between WAV and TXT files.
- **Usage in System**:
  - Acoustic and phonological benchmarking of Mundari speech.
  - Evaluation of audio preprocessing (conversion from 44.1 kHz 32-bit to 16 kHz 16-bit mono).
  - Validation of speech recognition and phoneme alignment.
  - Note: Does not contain pre-isolated numbers 1–20; isolated educational audio requires dedicated verified recordings.

---

## 3. Speech Recognition Reference Architecture

- **Reference Architecture**: OpenAI Whisper
- **Origin / Repository**: `https://github.com/openai/whisper`
- **License**: MIT License
- **Usage in System**:
  - Concept benchmark for log-mel filterbank feature extraction, encoder-decoder ASR design, and multilingual speech processing.
  - **Constraint Note**: Whisper is NOT directly deployed to edge Android due to memory footprint and absence of native Mundari support; used solely as an offline research/transcription benchmark.

---

## 4. Educational & Pedagogical Frameworks

- **NIPUN Bharat Guidelines**: National Initiative for Proficiency in Reading with Understanding and Numeracy (Department of School Education and Literacy, Ministry of Education, Government of India). Focus on Foundational Literacy and Numeracy (FLN) Grade 1 competencies.
- **Jharkhand JCERT & PALASH**: State curriculum guidelines for Mother Tongue-Based Multilingual Education (MTB-MLE). Our architecture is designed to support the pedagogical objectives of transitioning tribal mother-tongue children to school language, without claiming official institutional integration.
