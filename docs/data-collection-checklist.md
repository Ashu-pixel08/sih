# SIH260042: Field Audio Acceptance & Verification Checklist
**Project**: AI-Powered Vernacular Pedagogy & Real-Time Translation Assistant  
**Target Language**: Mundari (`unr`)  
**Document Version**: 1.0.0  

---

## 1. Pre-Recording Equipment & Environmental Checklist

Before recording any session with a native speaker, the field engineer must verify all items below:

- [ ] **Acoustic Environment**: Ambient room noise floor is $\le -45.0$ dBFS (measured using a 5-second silence calibration).
- [ ] **Hardware Isolation**: Windows and doors closed; ceiling fans, coolers, generators, and nearby vehicles silenced.
- [ ] **Microphone Placement**: Directional microphone positioned at a fixed distance of **15 cm to 20 cm** from speaker mouth.
- [ ] **Pop Filter**: High-density foam windscreen or pop shield securely attached at a $30^\circ$ off-axis angle.
- [ ] **Hardware AGC Disabled**: Automatic Gain Control disabled in audio recording hardware/software.
- [ ] **Gain Calibration**: Test vocalization peaks between $-6.0$ dBFS and $-3.0$ dBFS (at least $3.0$ dB headroom).
- [ ] **Informed Consent**: Signed parental/guardian consent form (for minors) or teacher consent form on file.
- [ ] **Speaker Registration**: Anonymized `speaker_id` assigned (`SPK_Fxx`, `SPK_Mxx`, `SPK_Cxx`); zero personal names stored.

---

## 2. Automated Signal-Level Quality Gate (Code: `validate_field_recording.py`)

Every recorded WAV file must pass the automated validator before linguistic review:

| Check Item | Acceptance Standard | Rejection Threshold | Automated Tool Flag |
| :--- | :--- | :--- | :--- |
| **Container & Codec** | RIFF WAVE, Linear PCM | Compressed format (MP3, AAC, OGG) | `INVALID_HEADER` |
| **Sampling Rate** | Exactly 16,000 Hz | $\ne 16,000$ Hz | `WRONG_SAMPLE_RATE` |
| **Channel Count** | Exactly 1 (Mono) | 2 (Stereo) or $> 2$ | `WRONG_CHANNELS` |
| **Bit Depth** | Exactly 16-bit signed integer | 24-bit, 32-bit float, or 8-bit | `WRONG_BIT_DEPTH` |
| **Peak Amplitude** | $< -1.0$ dBFS (headroom) | $\ge -1.0$ dBFS | `CLIPPING_DETECTED` |
| **Saturated Samples** | Exactly 0 samples at $\pm 32767$ | $\ge 1$ saturated sample | `CLIPPING_DETECTED` |
| **RMS Energy** | $-28.0$ dBFS to $-16.0$ dBFS | $< -28.0$ dBFS or $> -16.0$ dBFS | `ENERGY_OUT_OF_BOUNDS` |
| **Estimated SNR** | $\ge 22.0$ dB | $< 22.0$ dB | `LOW_SNR_NOISY` |
| **Utterance Duration** | $400$ ms to $2,500$ ms | $< 400$ ms or $> 2,500$ ms | `DURATION_OUT_OF_BOUNDS` |
| **Lead-In Silence** | $\ge 50$ ms | $< 50$ ms (onset cut off) | `LEAD_IN_TRUNCATED` |
| **Lead-Out Silence** | $\ge 50$ ms | $< 50$ ms (word tail cut off) | `LEAD_OUT_TRUNCATED` |
| **DC Offset** | $|\text{mean}| \le 0.005$ | $> 0.005$ | `DC_OFFSET_BIAS` |

---

## 3. Native Speaker Linguistic Review Checklist

Conducted by the certified native Mundari review committee:

- [ ] **Lexical Target Parity**: The spoken word corresponds exactly to the requested prompt (e.g. speaker said *मिअद*, not *एक*).
- [ ] **Zero Non-Target Borrowing**: Speaker did not substitute Hindi, Sadri, or Bengali loanwords for numerals.
- [ ] **Checked Vowel Integrity**: Glottal stops and checked vowels (*ओड़ोः*, *चिनाः*) are articulated cleanly without trailing distortion.
- [ ] **Retroflex Consonant Articulation**: Voiced retroflex flap `/ɽ/` (*मोड़ेया*) is distinctly pronounced without alveolar flattening.
- [ ] **No False Starts**: Speaker vocalized the word in one continuous stroke without stuttering or self-correction.
- [ ] **Zero Extraneous Vocalization**: No laughing, giggling, coughing, throat clearing, or whispering during the token.
- [ ] **Dialect Tagging**: Recording tagged accurately as `Hasada` or `Naguri` in the manifest metadata.
- [ ] **Educational Suitability**: Certified as natural, authentic mother-tongue expression for Grade 1 children.

---

## 4. Packaging & Partitioning Gate

Before merging newly accepted recordings into training/evaluation splits:

- [ ] **Manifest Schema Conformance**: Validated against `data/metadata/recording_manifest.schema.json`.
- [ ] **Deterministic File Naming**: Matches `REC_{DOMAIN}_{SPEAKER_ID}_{CLASS_ID}_REP{XX}.wav`.
- [ ] **Strict Speaker-Disjoint Split**:
  - [ ] No speaker from `TRAIN` appears in `VALIDATION`.
  - [ ] No speaker from `TRAIN` appears in `TEST`.
  - [ ] No speaker from `VALIDATION` appears in `TEST`.
- [ ] **Zero Augmentation in Evaluation**: Validation and Test splits contain ONLY raw, authentic recordings.
- [ ] **Checksum Audit**: SHA256 checksums computed and locked in `recording_manifest.json`.
