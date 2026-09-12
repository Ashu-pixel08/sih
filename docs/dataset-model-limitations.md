# Dataset & Model Limitations, Governance Policy & Data Requirements

**Project**: SIH260042 — “AI-Powered Vernacular Pedagogy and Real-Time Translation Tool for Mother Tongue-Based Primary Education”  
**Authoritative Status**: `RESEARCH / BASELINE IMPLEMENTATION / PIPELINE VALIDATION ONLY`  
**Accuracy Claim Policy**: `MISSING — SUFFICIENT LABELED 1–20 SPEECH DATA`

---

## 1. Executive Summary on Data Reality

> [!IMPORTANT]
> **Core Engineering Finding**:
> 1. **Zero Isolated 1–20 Audio Clips**: In the 200-recording public sample, there are **0 isolated single-word recordings**. All recordings are complete sentences between 1.97s and 7.70s.
> 2. **15 of 20 Numbers Acoustically Missing**: 15 out of 20 numerals (3, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19) have **zero acoustic representation** in the speech sample.
> 3. **Non-Production Status**: The 21-class speech model implemented in Phase 8 and exported in Phase 9 serves strictly as an **architecture and pipeline validation artifact**. It MUST NOT be claimed as a production-ready Mundari speech recognizer until verified isolated recordings are collected and trained.
> 4. **Zero Fabrication Guarantee**: No synthetic or fabricated labels have been attributed to real Mundari speech. All synthetic simulation experiments are strictly isolated under `SYNTHETIC / PIPELINE VALIDATION ONLY`.

---

## 2. Granular Data Limitations

| Dimension | Measured / Observed Reality | Engineering Consequence & Limitation |
| :--- | :--- | :--- |
| **Acoustic Numeral Coverage** | Only 5 numbers (1, 2, 4, 10, 20) appear inside multi-word sentences. 15 numbers have 0 acoustic occurrences. | Mathematically impossible to train a truthful 21-class classifier on this sample alone. |
| **Acoustic Isolation** | All 182 valid WAV files are continuous sentences (avg 3.71 seconds). | Word boundaries are unaligned; isolated 1.0s windowing cannot extract clean phonetic roots without manual phonetic segmentation. |
| **Speaker Diversity** | Sample contains exactly 2 speakers (1 female, 1 male). | Insufficient acoustic diversity for cross-speaker generalization, especially for primary school child voices. |
| **Domain Mismatch** | Sentences cover news, agriculture, and general folklore, rather than Grade 1 FLN classroom counting. | Linguistic context differs from primary school student-teacher interaction. |

---

## 3. Synthetic Data Governance Policy

To validate our training code, loss convergence, backward pass, and TFLite export mechanics without waiting for field data collection, we constructed `ai/training/synthetic_simulation_harness.py`.

### Strict Usage Boundaries:
- **PERMITTED USE**:
  - Validating training loop mechanics, learning rate schedulers, and optimizer updates.
  - Verifying input shape `[1, 101, 64, 1]` and output shape `[1, 21]`.
  - Verifying that data augmentation does not leak into validation/test splits.
  - Verifying numerical parity between PyTorch reference and LiteRT runtime.
- **STRICTLY PROHIBITED USE**:
  - Presenting synthetic data as real Mundari speech recordings.
  - Using synthetic evaluation scores to claim real-world linguistic recognition accuracy.
  - Claiming the model is "tested on native speakers" based on synthetic simulations.

---

## 4. Required Real-World Audio Data Specification

To transition the speech model from a validated baseline architecture into a production-ready FLN classroom tool, the following verified field recordings must be acquired:

1. **Target Vocabulary**:
   - Class 0: `_background_` (classroom chatter, desk taps, bell sounds, teacher Hindi speech).
   - Classes 1–20: Isolated pronunciations of Mundari numerals (`मिअद`, `बारिया`, `अपिया`, ... `हिसि`).
2. **Recording Volume**:
   - **20 to 50 isolated recordings per numeral** = **400 to 1,000 isolated audio clips**.
   - **50 to 100 background noise / out-of-vocabulary audio clips** for Class 0.
3. **Speaker Diversity**:
   - Minimum 4 to 8 native speakers.
   - Must include child voices (ages 5–8) and adult female/male voices to represent classroom demographics.
4. **Acoustic Format**:
   - 16.0 kHz or 44.1 kHz, 16-bit Mono WAV, recorded in quiet classroom or booth conditions.
   - Clean lead-in and trailing silence (< 100 ms).

---

## 5. Architectural Safeguard: The Guaranteed Presentation Path

The speech classifier is designed as an **enhancement layer**, never a single point of failure:

$$\text{Speech Processing} \longrightarrow \text{Translation Engine} \longrightarrow \text{Educational Content Engine} \longrightarrow \text{Verified Mundari Output} \longrightarrow \text{Offline Android}$$

### Guaranteed Classroom Presentation Path:
1. **Teacher Hindi Input / Touch Card**:
   - If spoken speech recognition confidence is below 0.65 (or in high-noise presentation environments), the system immediately falls back to the **Interactive Touch & Card Mode**.
2. **Deterministic Tier 1 Translation**:
   - Exact verified lookup for numbers 1–20 with 100% precision and zero hallucination.
3. **Verified Pedagogical Output**:
   - Prototype audio playback reference (pending native validation), high-contrast SVG flashcard with Ten-Frame visual counters, and printable bilingual worksheets.
4. **100% Offline Capability**:
   - Zero network dependencies; 100% functional in airplane mode on 2 GB RAM Android hardware.
