# SIH260042: Native Speaker Linguistic Annotation & Verification Protocol
**Project**: AI-Powered Vernacular Pedagogy and Real-Time Translation Tool for Mother Tongue-Based Primary Education  
**Target Language**: Mundari (`unr`) — Jharkhand MTB-MLE Context  
**Document Version**: 1.0.0  
**Status**: APPROVED ANNOTATION PROTOCOL  

---

## 1. Review Workflow & Lifecycle

Every recorded field token must pass through a two-stage quality assurance gate before it can enter the model training or evaluation corpus:

```
[Field Recording WAV]
          │
          ▼
┌─────────────────────────────────┐
│ STAGE 1: AUTOMATED SIGNAL AUDIT │
│ (RMS, Peak, Clipping, SNR, VAD) │
└─────────────────────────────────┘
          │
          ├── Fails Technical Spec ──> [STATUS: REJECTED_TECHNICAL]
          ▼ Passes
┌──────────────────────────────────────────────┐
│ STAGE 2: NATIVE SPEAKER LINGUISTIC REVIEW    │
│ (Pronunciation, Dialect, Lexical Legitimacy) │
└──────────────────────────────────────────────┘
          │
          ├── High Quality & Correct ─────────> [STATUS: ACCEPTED]
          ├── Valid but minor edit required ──> [STATUS: REQUIRES_CORRECTION]
          └── Wrong word / hesitation / noise ─> [STATUS: REJECTED_LINGUISTIC]
```

---

## 2. Review Status Definitions

| Status Code | Meaning | Action / Pipeline Eligibility |
| :--- | :--- | :--- |
| `UNREVIEWED` | Freshly ingested recording; pending human inspection | Blocked from training and evaluation splits |
| `ACCEPTED` | Verified by native Mundari speaker/teacher; passes all criteria | **Eligible** for training, validation, or test sets |
| `REQUIRES_CORRECTION` | Lexically valid but requires audio trimming or metadata fix | Held in staging until corrected by data engineer |
| `REJECTED_TECHNICAL` | Clipped, severe noise, wrong sample rate, or audio glitch | Permanently quarantined in `data/rejected/technical/` |
| `REJECTED_LINGUISTIC` | Incorrect word, false start, non-native mispronunciation | Permanently quarantined in `data/rejected/linguistic/` |

---

## 3. Metadata Fields Captured Per Recording

Every reviewed recording must have a corresponding record in `data/metadata/recording_manifest.json`:

```json
{
  "recording_id": "REC_FLN_SPK_C03_NUM05_REP02",
  "speaker_id": "SPK_C03",
  "class_index": 5,
  "label_id": "num_05",
  "expected_numeral": 5,
  "prompt_text": "मोड़ेया",
  "transcribed_text": "मोड़ेया",
  "phonetic_transcription_ipa": "moɽeja",
  "dialect_region": "Naguri (Khunti District)",
  "pronunciation_quality": "EXCELLENT_NATIVE",
  "technical_quality": {
    "sample_rate_hz": 16000,
    "duration_ms": 980,
    "rms_dbfs": -21.4,
    "peak_dbfs": -4.2,
    "snr_db": 31.2,
    "clipping_detected": false
  },
  "background_noise_level": "NEGLIGIBLE_SILENCE",
  "reviewer": {
    "reviewer_id": "REV_MUNDARI_01",
    "role": "Native Mundari Primary Teacher (DIET Khunti)",
    "timestamp_iso": "2026-09-04T12:00:00Z"
  },
  "review_status": "ACCEPTED",
  "linguistic_notes": "Clear articulation of retroflex flap /ɽ/ and natural checked vowel ending."
}
```

---

## 4. Linguistic Verification Criteria for Mundari Numerals

### 4.1 Phonological Features of Mundari
Native reviewers must pay specific attention to the distinctive phonological features of Mundari:
1. **Glottal Stops & Checked Vowels**: Mundari features final glottal stops or checked vowels (often indicated in Devanagari with visarga `ः` or half-stops, e.g., *चिनाः*, *ओड़ोः*). The vowel must not be cut off prematurely.
2. **Retroflex Flaps**: The numeral 5 (*मोड़ेया*) features the voiced retroflex flap `/ɽ/` (ड़). Reviewers must ensure the child does not substitute an alveolar `/d/` or Hindi dental `/d̪/`.
3. **Palatal Approximants**: The semivowel `/j/` in *मिअद* / *मियद* and *बारिया* must be natural and unforced.

### 4.2 Dialectal Balance (Hasada vs. Naguri)
Mundari in Jharkhand has two primary dialectal variants:
- **Hasada (Eastern/Southern — Murhu, Tamar, Bandgaon)**: Often considered the standard literary dialect by linguists (Hoffmann, Munda).
- **Naguri (Western/Northern — Khunti, Torpa, Karra)**: Heavily spoken in primary schools in central Khunti district with slight vowel rounding.
Both Hasada and Naguri variants are valid; reviewers must document the dialect in metadata rather than rejecting regional pronunciations.

### 4.3 Educational Suitability for Grade 1
Reviewers must assess:
- Is this the form a Grade 1 child naturally hears at home and in the village?
- Does it conflict with official JCERT textbook terminology (e.g. *चांदो* FLN workbooks)?
- If the speaker uses a borrowed Indo-Aryan form (e.g. *एक*, *दो*) instead of the authentic Mundari numeral (*मिअद*, *बारिया*), the token must be classified as `REJECTED_LINGUISTIC (BORROWED_NON_TARGET)`.

---

## 5. Reviewer Committee Composition

To eliminate individual bias, annotations must be governed by a three-member panel:
1. **Lead Native Speaker Educator**: Certified primary teacher fluent in Mundari and Hindi with at least 5 years of rural classroom experience.
2. **Community Representative**: An elder or Anganwadi worker from the local village community ensuring cultural authenticity.
3. **System Linguist / Integration Engineer**: Technical supervisor verifying audio quality, acoustic segmentation, and manifest integrity.

**Consensus Rule**: A recording is marked `ACCEPTED` if and only if both native reviewers approve the token. If reviewers disagree, the token is flagged `REQUIRES_CORRECTION` and reviewed jointly.
