# External Data Acquisition & Ethics Policy

**Project ID**: SIH260042  
**Application**: APP_NAME_PENDING (Vernacular FLN Assistant — Hindi ↔ Mundari)  
**Document Version**: 1.0.0  
**Scope**: All project contributors, data collectors, field researchers, and automated ingestion pipelines  

---

## 1. Ethical Principles for Indigenous Language Technology

Mundari is an Austroasiatic (Munda) language spoken predominantly in Jharkhand, Odisha, and West Bengal, classified by UNESCO as an indigenous language requiring active preservation and respectful technological stewardship. 

Developing educational technology for young tribal learners (Ages 3–8 / Balvatika to Grade 3) carries profound ethical responsibilities:
- **Linguistic Dignity**: Tribal children must not be presented with machine-hallucinated, broken, or synthetically mangled forms of their mother tongue.
- **Cultural Authenticity**: Examples, vocabulary, and stories must reflect tribal socio-cultural reality, flora, fauna, and community life.
- **Non-Exploitative Collaboration**: Community members and native speakers who share their voices and knowledge are valued partners, not uncredited data points.

---

## 2. Permitted vs. Prohibited Data Sources & Licenses

### 2.1 Permitted Licensing Categories
- **Government / Educational Open Access**:
  - NCERT / JCERT published bilingual primers released under public terms.
  - Central Institute of Indian Languages (CIIL) open academic grammars and lexicons.
  - Ministry of Tribal Affairs public resources.
- **Permissive Open-Source**:
  - Creative Commons Attribution (CC-BY 4.0).
  - Creative Commons Zero (CC0 1.0 / Public Domain).
  - Open Data Commons Attribution License (ODC-By).
- **Direct Field Collection**:
  - Audio and linguistic data collected directly by the project team accompanied by signed **Informed Consent Forms**.

### 2.2 Prohibited Data Sources
- **Web Scraping of Proprietary Materials**:
  - Scraping private blogs, copyrighted textbooks, or commercial language apps without written publisher authorization is strictly forbidden.
- **Synthetic LLM Hallucinations**:
  - Generating Mundari text using general commercial LLMs (GPT-4, Claude, Gemini, etc.) and submitting it as "ground truth" or "canonical" translation is **strictly prohibited**. LLMs exhibit severe hallucination in low-resource Munda languages.
- **Synthetic Native Audio Falsification**:
  - Passing off text-to-speech (TTS) audio or voice-converted samples as "native human recordings" constitutes academic fraud and results in immediate disqualification of the dataset.

---

## 3. Field Collection Protocol & Informed Consent for Native Audio

When recording native speakers for the audio reference library or speech recognition benchmarks:

### 3.1 Prior Informed Consent
1. Every speaker (or parent/guardian if a child is recorded) must sign or voice-record an **Informed Consent Agreement** in Mundari or Hindi.
2. The agreement must explicitly explain:
   - The purpose of the recording (building an educational app for primary school children).
   - How the audio will be stored and distributed (open educational research license).
   - The anonymization policy (speaker names are converted to irreversible IDs like `SPK-MUN-001`).

### 3.2 Acoustic & Environmental Rigor
1. Audio must be captured in uncompressed 16-bit linear PCM WAV at 16,000 Hz (mono).
2. Background noise must not exceed 25 dBA; minimum Signal-to-Noise Ratio (SNR) must be $\ge 15.0$ dB.
3. Pronunciations must be checked on-site by a community elder or native language teacher to avoid unnatural stilted cadences.

---

## 4. Machine Learning & Speech Pipeline Boundaries

### 4.1 Strict Split Isolation (No Speaker Leakage)
- For speech recognition (ASR) datasets, partitioning into `TRAIN`, `VAL`, and `TEST` must be performed at the **Speaker Level**.
- Under no circumstances may any speech sample from Speaker $X$ be present in both the training set and the evaluation set. Leakage creates artificially inflated accuracy metrics that collapse when deployed in real rural classrooms.

### 4.2 Benchmark Transparency
- All word error rates (WER) and character error rates (CER) must be reported against a publicly inspectable, held-out native test set.
- Results must document acoustic recording conditions (quiet indoor vs. active classroom).

---

## 5. Violations & Rejection Protocol

Any submission found to violate this policy will be:
1. Immediately transferred to `data/quarantine/`.
2. Documented in the project quarantine ledger.
3. Barred from canonical promotion until full remediation or permanent deletion.
