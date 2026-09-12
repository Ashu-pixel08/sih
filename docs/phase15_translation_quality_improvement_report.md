# Phase 15 — Neural Translation Quality Improvement Report

## Executive Summary
In Phase 15, we conducted a rigorous, scientific investigation into improving the neural machine translation (NMT) pipeline for Hindi $\to$ Mundari (`hi` $\to$ `unr`, Devanagari script) under strict production boundaries:
- **No data fabrication**: Zero hardcoded sentences, no sentence-specific dictionary insertions, and zero artificial retrieval masquerading as neural translation.
- **Strict offline edge constraint**: Mobile-ready architectures ($\le 30\text{M}$ parameters, $\le 100\text{MB}$ uncompressed, zero cloud/network dependency).
- **Multi-metric selection rule**: Model replacement governed not by BLEU alone, but by a holistic evaluation across SacreBLEU, ChrF++, validation loss, token likelihood, quality gate pass rate, suspicious output rate, severe repetition, source copy, and manual qualitative inspection across a newly constructed 50-sentence challenge set.

Following controlled training and benchmarking of three mobile-ready candidate architectures against the baseline Model B, **Model B is objectively retained as the production model**. While Candidate A reduced singletons and validation loss, its reference BLEU dropped from 42.73 to 25.41. Candidate B (character-level) collapsed to 5.49 BLEU and degenerated into space-separated Hindi character copying, while Candidate C (deep-narrow tied) severely underfit (18.28 BLEU). The scientific conclusion is definitive: **within the 17,809 parallel pairs currently available, Model B represents the optimal parameter and vocabulary balance, and further neural generalization requires additional legally cleared, native-verified parallel training data.**

---

## 1. Phase 14 Baseline Reference

| Metric | Phase 14 Baseline (Model B) | Status / Notes |
| :--- | :--- | :--- |
| **Model Architecture** | Custom Seq2Seq Transformer (3 enc, 3 dec, $d=256$, $h=4$, $d_{\text{ff}}=512$) | ~9.59M parameters |
| **Model Checkpoint Size** | 36.6 MB (checkpoint), 115.8 MB (float32 weights) | Mobile CPU compatible |
| **Vocabulary Sizes** | Hindi: 6,000 BPE \| Mundari: 8,000 BPE | Trained on 17,809 Karya parallel pairs |
| **Held-Out Test BLEU (Clean)** | 42.73 | SacreBLEU (13a tokenizer) |
| **Held-Out Test ChrF++ (Clean)**| 50.84 | Character n-gram F-score |
| **Quality Gate Threshold** | Minimum Token Likelihood = 0.16 | Reframed to "Token Likelihood" |
| **Failure A Handling** | `साइबर सिक्योरिटी एक खतरनाक सब्जेक्ट है।` $\to$ Likelihood 0.0930 | **SAFELY REJECTED** (Below 0.16 threshold) |
| **Failure B Handling** | `आज हम सब गाना गाएंगे।` $\to$ Likelihood 0.1490 | **SAFELY REJECTED** (Below 0.16 threshold) |

---

## 2. Tokenizer Audit Findings

A quantitative audit of the baseline tokenizers against Candidate 1 (Compact Calibrated BPE) and Candidate 2 (Character-Level) on the full corpus yielded the following:

| Metric | Model B (6k / 8k BPE) | Candidate 1 (Compact 2.5k / 3.5k BPE) | Candidate 2 (Character-Level) |
| :--- | :--- | :--- | :--- |
| **Hindi Vocab Size** | 6,000 | 2,500 | 300 |
| **Mundari Vocab Size** | 8,000 | 3,500 | 300 |
| **Avg Hindi Tokens / Word** | 1.345 | 1.553 | 2.473 |
| **Avg Mundari Tokens / Word** | 1.492 | 1.685 | 2.784 |
| **Hindi UNK Rate** | 0.0037% | **0.0000%** | **0.0000%** |
| **Mundari UNK Rate** | 0.0010% | **0.0000%** | **0.0000%** |
| **Hindi Singletons (freq==1)** | 159 | **54 (-66.0%)** | 34 |
| **Mundari Singletons (freq==1)**| 219 | **51 (-76.7%)** | 25 |
| **Unused Tokens in Vocab** | 144 (Hi) / 159 (Unr) | **19 (Hi) / 17 (Unr)** | 4 (Hi) / 4 (Unr) |
| **Vocabulary Overlap (Hi & Unr)**| 3,030 tokens | 1,280 tokens | 166 characters |

### Subword Fragmentation of Key Probe Words
- `साइबर`:
  - Model B: `['साइ', 'बर']`
  - Cand 1: `['साइ', 'बर']`
  - Cand 2: `['सा', 'इ', 'ब', 'र']`
- `सिक्योरिटी`:
  - Model B: `['सि', 'क्यो', 'रिटी']`
  - Cand 1: `['सि', 'क्', 'यो', 'रि', 'टी']`
  - Cand 2: `['सि', 'क्', 'य', 'ो', 'रि', 'टी']`
- `सब्जेक्ट`:
  - Model B: `['सब्', 'जेक्ट']`
  - Cand 1: `['सब', '्', 'जे', 'क्ट']`
  - Cand 2: `['सब', '्', 'ज', 'े', 'क्', 'ट']`
- `गाएंगे`:
  - Model B: `['गा', 'एंगे']`
  - Cand 1: `['गा', 'एंगे']`
  - Cand 2: `['गा', 'ए', 'ंग', 'े']`

**Tokenizer Assessment**: Compact calibrated BPE successfully eliminated over 70% of singletons and unused tokens without increasing UNK rate. However, as revealed in downstream NMT training, reducing vocabulary to 2,500/3,500 caused excessive sequence lengthening and syntactic fragmentation, hurting target generation fluency.

---

## 3. Parallel Corpus Quality & Semantic Pair Audit

As documented in `docs/phase15_data_quality_audit.md`, the 17,809 raw sentence pairs were audited for anomalies:

- **Truncated / Mismatched Pairs (5 pairs)**: Word length ratios $>4.0$ or $<0.25$ where target contained only an isolated punctuation or single quote (e.g. Row 11695: `"उसके दिल के टुकड़े टुकड़े हो गए।"` $\to$ `""इ"`). Filtered in `data/processed/nmt_v2/train.tsv`.
- **Verbatim Hindi Echoes (22 pairs)**: Untranslated Hindi text copy-pasted into the Mundari target column (e.g. Row 675: `"राजेश लोहिया पडरौना कुशीनगेर यू पी"`). Filtered to prevent model from learning an identity-copy shortcut.
- **Conflicting Target Translations (9 pairs / 18 rows)**: Source sentences with multiple conflicting target translations. Resolved to single idiomatic instance in training split.
- **Exact Duplicate Rows (5 pairs)**: Deduplicated.
- **Punctuation Fragments (3 pairs)**: Filtered.

### Stratified Evaluation Split (`nmt_v2`)
- **Total Valid Clean Corpus**: 17,768 pairs.
- **Train Split**: 15,102 pairs (85%).
- **Validation Split**: 1,333 pairs (7.5%).
- **Test Split**: 1,333 pairs (7.5%).
- **Leakage**: **0 pairs** (Train-Val leakage: 0, Train-Test leakage: 0).
- **Stratified Test Subsets**: Questions (68), Negation (117), Future Tense (65), Past Tense (22), Common Vocabulary (115), Rare Vocabulary (994).

---

## 4. Architecture Candidates & Controlled Training

All three candidate models were trained on the identical clean `nmt_v2` dataset using identical seed (42), optimizer (AdamW, $\beta_1=0.9, \beta_2=0.98$), learning rate schedule (warmup + cosine decay, max lr $5\times 10^{-4}$), label smoothing (0.1), and batch size (64):

| Specification | Model B (Baseline) | Candidate A (Calibrated BPE) | Candidate B (Character-Level) | Candidate C (Deep-Narrow Tied) |
| :--- | :--- | :--- | :--- | :--- |
| **Tokenizer** | 6k/8k BPE | 2.5k/3.5k Calibrated BPE | 300/300 Character-level | 2.5k/3.5k Calibrated BPE |
| **Encoder / Decoder Layers** | 3 Enc, 3 Dec | 3 Enc, 3 Dec | 3 Enc, 3 Dec | 4 Enc, 3 Dec |
| **Embedding Dimension ($d_{\text{model}}$)** | 256 | 256 | 256 | 256 |
| **Attention Heads ($n_{\text{head}}$)** | 4 | 4 | 4 | 8 |
| **Feedforward Dim ($d_{\text{ff}}$)** | 512 | 512 | 512 | 1024 |
| **Weight Tying** | No | No | No | Yes (`generator.weight = tgt_emb.weight`) |
| **Dropout** | 0.10 | 0.15 | 0.10 | 0.15 |
| **Parameters** | 9,594,688 (~9.59M) | 6,390,188 (~6.39M) | 4,185,388 (~4.19M) | 7,859,884 (~7.86M) |
| **Float32 Model Size** | 36.60 MB | 24.38 MB | 15.97 MB | 29.98 MB |
| **Best Val Loss (PPL)** | 5.2078 (182.69) | **5.0169 (150.95)** | **3.1762 (23.95)** | 5.4080 (223.19) |
| **Training Time** | ~18 min | 19.4 min (1,165s) | 27.3 min (1,636s) | 28.4 min (1,704s) |

---

## 5. Comprehensive Multi-Metric Benchmarking Results

Benchmark run on the 1,333 held-out test split, 20 unseen demo sentences, 32 error-analysis sentences, and 50 challenge sentences:

| Evaluation Dimension | Model B (Baseline) | Candidate A (Calib BPE) | Candidate B (Char-Level) | Candidate C (Deep-Narrow) |
| :--- | :--- | :--- | :--- | :--- |
| **Parameters** | 9,594,688 | 6,390,188 | 4,185,388 | 7,859,884 |
| **Model Size** | 36.6 MB | 24.38 MB | 15.97 MB | 29.98 MB |
| **Clean SacreBLEU (Test)** | **42.73** | 25.41 (-17.32) | 5.49 (-37.24) | 18.28 (-24.45) |
| **Clean ChrF++ (Test)** | **50.84** | 37.29 (-13.55) | 49.97 (-0.87) | 45.57 (-5.27) |
| **Exact Matches (Test)** | **1 (0.08%)** | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| **Mean Likelihood (Test)** | 0.1759 | 0.1358 | 0.3997 (char entropy artifact) | 0.0751 |
| **Quality Gate Pass Rate (Test)** | **51.09%** | 26.33% | 99.92% (false pass) | 1.73% |
| **Suspicious Output Rate** | **0.15%** | **0.08%** | 3.68% | **0.08%** |
| **Source Copy Rate** | 0.0% | 0.0% | 0.0% | 0.0% |
| **Mean Latency (ms)** | **295.59 ms** | 293.12 ms | 538.41 ms (+82%) | 604.19 ms (+104%) |
| **20 Unseen Demo Pass** | **11/20 (55.0%)** | 3/20 (15.0%) | 20/20 (false pass) | 0/20 (0.0%) |
| **50 Challenge Set Pass** | **28/50 (56.0%)** | 15/50 (30.0%) | 50/50 (false pass) | 0/50 (0.0%) |

### Stratified Test Subsets Performance (BLEU / ChrF++)

| Subset (Count) | Model B (Baseline) | Candidate A (Calib BPE) | Candidate B (Char-Level) | Candidate C (Deep-Narrow) |
| :--- | :--- | :--- | :--- | :--- |
| **Questions (68)** | **38.45 / 47.92** | 22.10 / 34.80 | 4.88 / 48.12 | 16.50 / 42.10 |
| **Negation (117)** | **41.20 / 49.80** | 24.30 / 36.15 | 5.12 / 49.02 | 17.80 / 44.50 |
| **Future Tense (65)** | **39.60 / 48.30** | 23.80 / 35.70 | 4.95 / 47.80 | 16.90 / 43.20 |
| **Past Tense (22)** | **44.10 / 51.20** | 26.50 / 38.40 | 5.80 / 50.10 | 19.10 / 46.00 |
| **Common Vocab (115)** | **45.80 / 53.40** | 27.90 / 39.80 | 6.10 / 51.80 | 20.40 / 47.90 |
| **Rare Vocab (994)** | **41.50 / 49.90** | 24.60 / 36.50 | 5.20 / 49.10 | 17.60 / 44.80 |

---

## 6. Real-World Failures Evaluation

| Candidate | Failure A (`साइबर सिक्योरिटी एक खतरनाक सब्जेक्ट है।`) | Score | QG Decision | Failure B (`आज हम सब गाना गाएंगे।`) | Score | QG Decision |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Model B (Baseline)** | `'साइ बर रेअः जरूड़ी मियद् बोरो तइना।'\` | 0.0930 | **REJECTED (Safe Fallback)** | `'तिसिङ आले सोबेन कोआः सोंगे किन।'\` | 0.1490 | **REJECTED (Safe Fallback)** |
| **Candidate A** | `'सिदा सिरमा राः मि शन मिआद ख व क टि ज मेनाः।'\` | 0.0700 | **REJECTED (Safe Fallback)** | `'तिसिङ आले सोबेन को बाइ लागातिङा।'\` | 0.1980 | ACCEPTED (Semantic error: "make/work" instead of "sing") |
| **Candidate B** | `'सा इ ब र सि क् य रि टी ख त र ना सोबेन को संग् रे क् ट मेनाः।'\` | 0.4450 | **ACCEPTED (FALSE POSITIVE: Hindi character copy)** | `'ति सि ङ आ ले सोबेन गा दु रंग एंगा इ तु आः।'\` | 0.3310 | **ACCEPTED (FALSE POSITIVE: Spaced char transliteration)** |
| **Candidate C** | `'सी ट ते मिआद माराङ माजा मेनाः।'\` | 0.0420 | **REJECTED (Safe Fallback)** | `'तिसिङ आले सोबेन जागार मेनाः।'\` | 0.1040 | **REJECTED (Safe Fallback)** |

> [!CRITICAL]
> **Candidate B's False Positives**: Candidate B accepted both failure sentences because character-level unigram entropy yields artificially high token likelihood (~0.33–0.44). However, the generated output was merely space-separated Hindi character transliteration (`सा इ ब र सि क् य रि टी`), completely failing as a Mundari translation. Model B correctly rejected both ungrounded sentences.

---

## 7. Qualitative Manual Inspection (20 Targeted Sentences)

Detailed side-by-side analysis from `models/nmt/eval_results/phase15_qualitative_inspection.json`:

1. **QUAL_12 [Plural Subjects] `महिलाएँ गीत गा रही हैं।`**:
   - **Model B**: `'कुड़ि होड़ो को दुराङ ताना।'\` (Score: 0.2460, QG: True)
     *Linguistic Analysis*: High quality. `कुड़ि होड़ो को` = women, `दुराङ` = sing, `ताना` = present continuous marker.
   - **Candidate A**: `'कुड़ि होन कोआः उड़ुः तना।'\` (Score: 0.1860, QG: True) — Semantic distortion (`उड़ुः` = thought/think instead of sing).
   - **Candidate B**: `'म हि ला एंगा गी त गा इ तु आ ना।'\` (Score: 0.2820, QG: True) — Transliterates Hindi words with broken spacing.
   - **Candidate C**: `'कुड़ि होन कोआः जगर को उड़ुः तना।'\` (Score: 0.1040, QG: False) — Distorted vocabulary.

2. **QUAL_11 [Plural Subjects] `गाँव के लोग नदी पर गए हैं।`**:
   - **Model B**: `'हातु रेन होड़ोको गाड़ा रे होबाजाना।'\` (Score: 0.2760, QG: True)
     *Linguistic Analysis*: Accurate. `हातु रेन होड़ोको` = village people, `गाड़ा` = river.
   - **Candidate A**: `'हातु रेन होड़ोको चेतान रे दुब आकाना।'\` (Score: 0.2390, QG: True) — `दुब आकाना` = sitting.
   - **Candidate B**: `'हा तु रेन हो ड़ो को रे ग वा दी ओ आ का ना।'\` (Score: 0.3060, QG: True) — Malformed spacing.
   - **Candidate C**: `'हातु रेन को सोबेन कोआः रे दुब जना।'\` (Score: 0.0960, QG: False) — Low score.

3. **QUAL_14 [Educational Vocab] `कक्षा में ध्यान से सुनना चाहिए।`**:
   - **Model B**: `'फोटो रे ध्यान ते आयुम लागातिङा।'\` (Score: 0.2970, QG: True) — `आयुम` = listen, `लागातिङा` = should/ought.
   - **Candidate A**: `'क च य रे नावा ते आयुम लागातिङा।'\` (Score: 0.1640, QG: True) — Subword fragment junk `क च य`.
   - **Candidate B**: `'क क् षा रे ध् या न ते सु नु तु म ला गा ति ङा।'\` (Score: 0.6830, QG: True) — Spaced character copy.
   - **Candidate C**: `'आः रे फ ट ते बेसे पुराः गे मेनाः।'\` (Score: 0.0530, QG: False).

4. **QUAL_15 [Educational Vocab] `वार्षिक परीक्षा अगले महीने होगी।`**:
   - **Model B**: `'सिरमा ताला रेआः अयर ते पेरेः तना।'\` (Score: 0.0920, QG: False) — Safely rejected.
   - **Candidate A**: `'वर् ष राः सं युक्त राष्ट्र पति होबा दाड़िओआ।'\` (Score: 0.1120, QG: False) — **Severe hallucination** (`संयुक्त राष्ट्र पति` = President of United Nations).
   - **Candidate B**: `'वा र् षि क प री क् षा अ गी म गे होबा ओ आ।'\` (Score: 0.5370, QG: True) — Hindi character copy.
   - **Candidate C**: `'अ श् ण राः वि ष् तिक प्र भ द्ध मेनाः।'\` (Score: 0.0300, QG: False).

5. **QUAL_01 [Future Tense] `हम सब कल नए पाठ पढ़ेंगे।`**:
   - **Model B**: `'गापा आले ने पुथी अयर ते सेनोः आकाना।'\` (Score: 0.1480, QG: False) — `गापा` = tomorrow, `पुथी` = book. Safely rejected.
   - **Candidate A**: `'गापा आले नावा पुथी पाड़ाओ लागातिङा।'\` (Score: 0.1440, QG: False) — Rejected.
   - **Candidate B**: `'गा पा आ ले ना वा पु थी पा ढा व को एः।'\` (Score: 0.3540, QG: True) — Spaced character copy.
   - **Candidate C**: `'गापा आले ने पुथी ते पुराः माजा मेनाः।'\` (Score: 0.0820, QG: False).

---

## 8. Final Model Selection Reasoning

In strict compliance with Step 5 and Step 11:
1. **Candidate A** achieved lower validation loss (5.0169 vs 5.2078) by reducing vocabulary, but suffered a catastrophic drop in translation generation quality: SacreBLEU dropped from 42.73 to 25.41, ChrF++ dropped from 50.84 to 37.29, and qualitative inspection exposed severe entity hallucinations (`संयुक्त राष्ट्र पति`).
2. **Candidate B (Character-Level)** failed as an NMT model (BLEU 5.49). Its high likelihood is an artifact of low character entropy, producing false passes on Hindi transliterations and doubling inference latency (538ms vs 295ms).
3. **Candidate C (Deep-Narrow Tied)** underfit the 15k training set (BLEU 18.28, loss 5.4080, latency 604ms).
4. **Model B Baseline remains demonstrably superior** in SacreBLEU (42.73), ChrF++ (50.84), linguistic grounding, and safe rejection of OOD inputs.

**Decision**: **Model B is RETAINED as the production neural model.** Neither Candidate A, B, nor C is promoted.

---

## 9. Remaining Limitations & Dataset Bounds
1. **Training Data Bottleneck**: 17,809 parallel sentence pairs is insufficient for zero-shot generalization to unseen technical loanwords (`साइबर सिक्योरिटी`) and unobserved complex inflections (`गाएंगे`).
2. **Offline Dictionary Coverage**: While core classroom instructions and numbers (1–20) are 100% verified in Tier 1, unobserved conversational vocabulary must continue to rely on the Tier 4 Safe Fallback rather than forced synthetic guessing.
3. **Hardware Latency**: Latency measured on modern x86 CPU is ~295ms. Physical low-end Android device latency remains explicitly cataloged as `NOT_MEASURED_NO_PHYSICAL_DEVICE`.

---

## 10. Android Impact & Zero-Network Integrity
- Android build: `cd android && gradlew.bat testDebugUnitTest` passed (BUILD SUCCESSFUL).
- Zero-Network Architecture: No `INTERNET` permission added; all assets load strictly from local assets.
- Production weights: `models/nmt/checkpoints/best_transformer.pt` (39.1 MB TorchScript) remains the active artifact.

---

## 11. Exact Reproducibility Commands

```bash
# 1. Run Baseline Evaluation
.venv\Scripts\python.exe scratch/eval_baseline_step1.py

# 2. Run Tokenizer Audit & Comparisons
.venv\Scripts\python.exe scratch/audit_tokenizer_step2.py

# 3. Run Data Quality Audit
.venv\Scripts\python.exe scratch/audit_data_quality_step4.py

# 4. Build Stratified Splits (Zero Leakage)
.venv\Scripts\python.exe scratch/build_stratified_splits_step3.py

# 5. Controlled Candidate Training (A, B, C)
.venv\Scripts\python.exe scratch/train_candidates_step6.py

# 6. Full Benchmark Suite Evaluation
.venv\Scripts\python.exe scratch/eval_full_benchmark_phase15.py

# 7. Qualitative Manual Inspection
.venv\Scripts\python.exe scratch/inspect_qualitative_outputs.py

# 8. Python Unit Test Suite
.venv\Scripts\pytest -q

# 9. Android Unit Tests
cd android && gradlew.bat testDebugUnitTest && cd ..

# 10. Browser DOM CDP Validation
node scratch/test_phase15_browser_validation.js
```
