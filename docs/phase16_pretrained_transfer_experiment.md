# Phase 16: Pretrained Multilingual Transfer Experiment Report

## 1. Motivation
In Phase 15, an exhaustive empirical audit established that **Model B** (~9.59M parameter from-scratch Transformer) remains the best small architecture for Hindi $\to$ Mundari translation on our legally cleared parallel corpus, achieving **SacreBLEU 42.73** and **ChrF++ 50.84** on the held-out test split (`data/processed/nmt_v2/test.tsv`). However, Phase 14 and Phase 15 also revealed severe generalization bottlenecks:
- **Out-of-Distribution (OOD) Technical Terms**: Modern concepts (`साइबर`, `सिक्योरिटी`, `सब्जेक्ट`) shatter into fragmented subwords, inducing low generation confidence and safe quality gate rejection (Failure A).
- **Inflectional Rigidity**: Unseen verbal inflections (`गाएंगे` vs common corpus forms `गाते हैं` / `गाया`) trigger degraded grammatical structure (Failure B).

**Research Question of Phase 16**:
Can multilingual transfer from a massive pretrained encoder-decoder (**google/mt5-small**, ~300M parameters) fine-tuned *strictly* on our legally cleared 15,102-pair Hindi-Mundari parallel corpus overcome subword OOD fragmentation and generalize better on unseen Hindi $\to$ Mundari sentences than Model B?

---

## 2. Hardware & Execution Environment
- **Host GPU**: NVIDIA GeForce RTX 3050 Laptop GPU (6GB VRAM, Driver 581.86, CUDA 13.0 capability).
- **Environment**: Python 3.13.5 (64-bit Windows) in virtual environment (`.venv`).
- **PyTorch Status & Hardware Decision (Step 2)**:
  - The working `.venv` environment was initialized with `torch==2.14.0+cpu`.
  - An attempt to install the 2.6GB Windows CUDA wheel (`torch==2.14.0+cu126`) was severed by remote TCP connection resets (`ConnectionResetError: [WinError 10054] An existing connection was forcibly closed by the remote host`).
  - Following the explicit rule of **Step 2** (*"If GPU installation is not practical, document it and choose the smallest feasible pretrained model. Do NOT destroy the existing environment"*), the clean environment was preserved without corruption.
  - Multi-threaded CPU execution with 14 parallel threads was deployed (`torch.set_num_threads(14)`), achieving 0.36 seconds per batch step and enabling complete training in 2,285.4 seconds (~38.1 minutes) without crashing or destabilizing production dependencies.

---

## 3. Pretrained Model Candidates Evaluated

| Model Candidate | Parameters | Supported Languages | Explicit Mundari (`unr`) Support | License | Expected VRAM / RAM | Fine-Tuning Feasibility (RTX 3050 / CPU) | Android Compression Feasibility |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`google/mt5-small`** (Tested) | **300.18M** | 101 languages (mC4) | **NO** (Devanagari script covered) | **Apache 2.0** | ~1.5GB VRAM / ~2.5GB RAM | **High** (LoRA PEFT, 688k trainable params) | Distillable to student model (<20MB) |
| `facebook/nllb-200-distilled-600M` | ~615M | 200 languages | **NO** (`sat_Olck` only; no `unr`) | CC-BY-NC 4.0 | 6 - 8 GB VRAM | **Poor** (High OOM risk on 6GB GPU) | Restricted by non-commercial license |
| `ai4bharat/IndicBART` | ~244M | 11 Indic + English | **NO** (11 scheduled only) | MIT | ~3GB VRAM / ~2GB RAM | **Medium** | Distillable to student model |

---

## 4. License & Support Verification
- **Model Selected**: `google/mt5-small`
- **License**: Apache 2.0 (fully open for commercial, educational, and public deployment without NC clauses).
- **Mundari Language Support**: **NOT officially supported** in mC4 pretraining. However, because mT5's 250,100 SentencePiece vocabulary includes the entire Devanagari Unicode block, all characters and basic syllabic structures of Devanagari Mundari are representable without `<unk>` tokens.

---

## 5. Tokenizer Audit & Probe Analysis (Step 11)

| Probe Word | Category | `google/mt5-small` (250k vocab) | Model B Hindi BPE (6k vocab) | Model B Mundari BPE (8k vocab) |
| :--- | :--- | :--- | :--- | :--- |
| **साइबर** | Technical Loanword | `['▁साइ', 'बर']` (2 tokens) | `['साइ', 'बर']` (2 tokens) | `['साइ', 'बर']` (2 tokens) |
| **सिक्योरिटी** | Technical Loanword | `['▁', 'सिक', '्यो', 'र', 'िटी']` (5 tokens) | `['सि', 'क्यो', 'रिटी']` (3 tokens) | `['सिक्', 'यो', 'रिटी']` (3 tokens) |
| **सब्जेक्ट** | Technical Loanword | `['▁सब', '्ज', 'ेक्ट']` (3 tokens) | `['सब्', 'जेक्ट']` (2 tokens) | `['सब्', 'जेक्ट']` (2 tokens) |
| **गाना** | Common Root | `['▁ग', 'ाना']` (2 tokens) | `['गाना']` (1 token) | `['गा', 'ना']` (2 tokens) |
| **गाएंगे** | Inflected Verb | `['▁ग', 'ाएं', 'गे']` (3 tokens) | `['गा', 'एंगे']` (2 tokens) | `['गाए', 'ंगे']` (2 tokens) |
| **खतरनाक** | Common Adjective | `['▁ख', 'तर', 'नाक']` (3 tokens) | `['खतरनाक']` (1 token) | `['खतरनाक']` (1 token) |

**Key Finding**:
Although `google/mt5-small` has a 250,100 token vocabulary, its budget is allocated across 101 languages. As a result, Indic words undergo heavy character-level fragmentation (`खतरनाक` $\to$ 3 tokens, `सिक्योरिटी` $\to$ 5 tokens), whereas Model B's domain-specific Hindi tokenizer represents frequent words as single unified subwords. However, for `साइबर`, both models segment identically into `['साइ', 'बर']`.

---

## 6. Training Configuration (Steps 3, 4, 5)
- **Dataset**: `data/processed/nmt_v2/train.tsv` (15,102 clean parallel pairs, 0 leakage with test/val).
- **Validation**: `data/processed/nmt_v2/val.tsv` (1,333 pairs).
- **Test Set**: `data/processed/nmt_v2/test.tsv` (1,333 pairs, identical held-out test split).
- **Adaptation Strategy**: LoRA (Low-Rank Adaptation) on attention query (`q`) and value (`v`) projections.
  - LoRA rank: $r=16$, $\alpha=32$, dropout: $0.05$.
  - Trainable parameters: 688,128 (0.2287% of 300,864,896 total parameters).
- **Optimization**: AdamW (`lr=1e-3`, `weight_decay=0.01`), cosine learning rate scheduler with 100-step linear warmup.
- **Batching**: Batch size 8, gradient accumulation 4 (effective batch size 32), max length 64.
- **Convergence**:
  - Initial Train Loss: 20.2970
  - Step 100 Val Loss: 6.0772
  - Step 300 Val Loss: 4.5001
  - Step 600 Val Loss: **4.3410** (Checkpoint saved to `models/nmt/pretrained_transfer/best_model`).
  - Total Training Time: 2,285.4 seconds (~38.1 minutes).

---

## 7. Baseline vs Pretrained Model Benchmark (Step 15)

| Metric | Model B (Baseline) | `google/mt5-small-lora` (Transfer) | Delta / Assessment |
| :--- | :--- | :--- | :--- |
| **Architecture** | Custom From-Scratch Transformer | Pretrained Encoder-Decoder + LoRA | Transfer Experiment |
| **Evaluation Split** | `data/processed/nmt_v2/test.tsv` (1,333 pairs) | `data/processed/nmt_v2/test.tsv` (1,333 pairs) | **Identical Held-Out Split** |
| **Parameters** | **9,594,688** (~9.59M) | 300,864,896 (~300.86M) | +291.27M (+3035%) |
| **Checkpoint Size** | **36.6 MB** | ~1,200 MB base + 2.7 MB adapter | ~32x larger |
| **Validation Loss** | 5.2078 | **4.3410** | Pretrained loss lower |
| **SacreBLEU** | **42.73** | **0.91** | **-41.82 BLEU (Catastrophic Drop)** |
| **ChrF++** | **50.84** | **14.40** | **-36.44 ChrF++** |
| **Exact Match** | 1 / 1,333 (0.08%) | 0 / 1,333 (0.00%) | 0 exact |
| **Suspicious Rate** | 0.15% (2 / 1,333) | 0.08% (1 / 1,333) | Both mechanically low |
| **Naive QG Pass Rate** | 51.09% | 99.92% (Misleading Artifact) | Degenerate template artifact |
| **Mean Latency** | **295.59 ms** | 415.99 ms | +120.40 ms (+40.7%) |
| **Latency p50 / p95**| **326.44 ms / 449.01 ms** | 403.01 ms / 591.47 ms | Higher variance on CPU |

---

## 8. Real-World Failures & Core Probes (Step 7)

| Input ID | Hindi Source | Model B Baseline Output | `google/mt5-small-lora` Output | Semantic Preservation Audit |
| :--- | :--- | :--- | :--- | :--- |
| **Failure A** | साइबर सिक्योरिटी एक खतरनाक सब्जेक्ट है। | `साइबर रे रेः जरूड़ी मियुद बोरो तना।` (Conf: 9% $\to$ **REJECTED**) | `नेआ साइबरसिक सिक्योरिटी को काः।` (Conf: 25.1%) | **Neither translates accurately**. Model B safely rejected it. mT5 kept subwords `साइबरसिक सिक्योरिटी` but collapsed the clause into `को काः` (not/negation marker). |
| **Failure B** | आज हम सब गाना गाएंगे। | `तिसिङ आले सोबेन कोआः सोङे किना।` (Conf: 15% $\to$ **REJECTED**) | `नेआ ते रे आञ गाना जाना।` (Conf: 16.1%) | **Severe Failure in mT5**. Copies `गाना जाना` and flips 1st person plural `हम` to 1st person singular `आञ` ("me"). |
| **Probe C** | कल स्कूल कौन नहीं आया था? | `होला स्कूल ओकोए काएः तइन केना।` (Conf: 21% $\to$ **PASSED**) | `नेआ ते रे स्कूल कौन आञः।` (Conf: 16.8%) | **Model B wins decisively**. Model B generates genuine Mundari (`होला ... ओकोए काएः`). mT5 copies Hindi `स्कूल कौन`. |
| **Probe D** | इस पाठ का मतलब कौन समझाएगा? | `ने कजि रेआः माने ओकोए इतुआना।` (Conf: 23% $\to$ **PASSED**) | `नेआ ते आञ रे काः जाना।` (Conf: 10.8%) | **Model B wins decisively**. Model B translates `माने ओकोए इतुआना` ("who knows the meaning"). mT5 generates gibberish. |
| **Probe E** | महिलाएँ गीत गा रही हैं। | `कुड़िको दुरं दुरं तनाको।` (Conf: 20% $\to$ **PASSED**) | `नेआ महिलाएँ गीत गा: रे आञः पुरुष गीत गीत।` (Conf: 13.2%) | **Severe Hallucination in mT5**. mT5 hallucinates the antonym `पुरुष` (men) out of nowhere! |
| **Probe F** | वार्षिक परीक्षा अगले महीने होगी। | `सिरमा रअः परीक्षा एटाः चंडु रे होबाओआ।` (Conf: 18.5% $\to$ **PASSED**) | `नेआ परीक्षा रे आञः जाना।` (Conf: 17.5%) | **Model B wins decisively**. Model B translates `सिरमा रअः परीक्षा` (annual exam) and `एटाः चंडु` (next month). mT5 produces meaningless fragment. |

---

## 9. Morphology Diagnostic Analysis (Step 9)

7 controlled tense/person/aspect variations were tested to determine whether pretrained representations improve inflectional generalization:

| ID | Hindi Source | Feature Tested | `google/mt5-small-lora` Output | Linguistic Evaluation |
| :--- | :--- | :--- | :--- | :--- |
| **MORPH-01** | आज हम गाना गाएंगे। | 1st pl future | `नेआ ते गाना जाना।` | **Failed**. Copies Hindi `गाना जाना`. No 1st person marker. |
| **MORPH-02** | आज वे गाना गाएंगे। | 3rd pl future | `नेआ गाना ते रे आञ कोना।` | **Failed**. Generates `आञ` (1st person singular "me") instead of 3rd person `इनकु`. |
| **MORPH-03** | कल हम गाना गाएंगे। | 1st pl future (tomorrow) | `नेआ ते गाना जाना।` | **Failed**. Identical collapse to MORPH-01; insensitive to temporal shift `कल`. |
| **MORPH-04** | हम रोज गाना गाते हैं। | 1st pl habitual present | `नेआ रोज गाना गाड़ो: रे आञ।` | **Failed**. Copies Hindi `रोज गाना`, hallucinated `आञ`. |
| **MORPH-05** | हमने कल गाना गाया। | 1st pl past tense | `नेआ ते आञ गाना जाना।` | **Failed**. Insensitive to past tense; identical `गाना जाना` template. |
| **MORPH-06** | बच्चे गीत गा रहे हैं। | 3rd pl continuous | `नेआ गीत गा: बच्चे रे आञः गीत गीत` | **Failed**. Severe duplication (`गीत गीत`), Hindi copy `बच्चे`. |
| **MORPH-07** | महिलाएँ गीत गा रही हैं। | 3rd pl fem continuous | `नेआ महिलाएँ गीत गा: रे आञः पुरुष गीत गीत।` | **Failed**. Unrelated noun hallucination (`पुरुष`). |

**Morphology Conclusion**:
Parameter-efficient fine-tuning on `google/mt5-small` **completely failed** to learn Mundari agglutinative verbal morphology. Because Mundari verbs combine root + tense/aspect marker + object agreement + subject clitic (e.g. `दुरं-तना-को`), an unadapted 250k multilingual decoder defaults to shallow keyword copying and high-frequency template emission.

---

## 10. Loanword Diagnostic Analysis (Step 10)

| ID | Target Loanword | Hindi Source | `google/mt5-small-lora` Output | Handling Assessment |
| :--- | :--- | :--- | :--- | :--- |
| **LOAN-01** | साइबर | साइबर सिक्योरिटी एक खतरनाक सब्जेक्ट है। | `नेआ साइबरसिक सिक्योरिटी को काः।` | Preserves loanword syllables, but clause structure collapses. |
| **LOAN-02** | सिक्योरिटी | स्कूल में सिक्योरिटी बहुत जरूरी है। | `नेआ स्कूल सिक्योरिटी रे होड़ोः।` | Copies loanwords `स्कूल`, `सिक्योरिटी` into generic template. |
| **LOAN-03** | कंप्यूटर | स्कूल में कंप्यूटर सीखना बहुत अच्छा है। | `नेआ कंप्यूटर सीखना।` | Direct Hindi copying (`कंप्यूटर सीखना`). |
| **LOAN-04** | डिजिटल | यह पाठ डिजिटल स्क्रीन पर दिखेगा। | `नेआ स्क्रीन रे आञः ओड़ो:` | Omits `डिजिटल`, copies `स्क्रीन`. |
| **LOAN-05** | इंटरनेट | आज इंटरनेट से सभी बच्चे पढ़ रहे हैं। | `नेआ इंटरनेट रे ते बच्चे काएः।` | Copies `इंटरनेट` and `बच्चे`. |
| **LOAN-06** | स्कूल | कल स्कूल कौन नहीं आया था? | `नेआ ते रे स्कूल कौन आञः।` | Copies `स्कूल कौन`. |
| **LOAN-07** | फाइल | इस फाइल को ध्यान से देखो। | `नेआ ध्यान रे आञः जाना।` | Drops `फाइल`, copies `ध्यान`. |
| **LOAN-08** | मोबाइल | मोबाइल पर संदेश आ गया है। | `नेआ मोबाइल रे संदेश ते आञः ओड़ो:` | Copies `मोबाइल` and `संदेश`. |

**Loanword Conclusion**:
`google/mt5-small` preserves Devanagari subwords for English loanwords without out-of-vocabulary exceptions. However, instead of translating the surrounding clause, it mechanically repeats the loanwords or copies adjacent Hindi tokens into high-frequency filler frames (`नेआ ... रे आञः ओड़ो:`).

---

## 11. Unseen & Challenge Benchmarks (Step 8)
- **20 Unseen Demo Benchmark (`data/benchmarks/unseen_demo_20.json`)**:
  - Model B: 11 / 20 pass rate (55.0%), generating accurate grammatical outputs for classroom domains while rejecting low-confidence items.
  - `google/mt5-small-lora`: 20 / 20 pass rate (100.0% naive pass), but **every single output is a degenerate template** (e.g. `DEMO-01` $\to$ `नेआ रः बच्चे रे सुप्रभात को आञ।`, `DEMO-02` $\to$ `नेआ कक्षा रे रः आञ कोना।`, `DEMO-03` $\to$ `नेआ रः बच्चे रे आञ केना।`).
- **50 Challenge Set (`data/test_vectors/challenge_set_50.json`)**:
  - Model B: 28 / 50 pass rate (56.0%).
  - `google/mt5-small-lora`: 50 / 50 pass rate (100.0% naive pass), all collapsing into variations of `नेआ ... रे आञः जाना`.

---

## 12. Quality Gate Calibration Finding (Step 12)
As predicted in Step 12, **raw model likelihood is completely misleading for pretrained cross-lingual decoders**:
- In `google/mt5-small-lora`, the average generation confidence was **0.1652**, and 99.92% of outputs passed the $\ge 0.05$ threshold.
- However, the model achieved only **0.91 BLEU**!
- Why? The decoder collapsed into a degenerate subspace emitting high-frequency Mundari postpositions (`नेआ`, `ते`, `रे`, `आञः`, `जाना`) which have high local probability in every context.
- **Rule Confirmed**: High generation confidence / likelihood must **never** be equated with semantic translation correctness.

---

## 13. Qualitative Examples & Linguistic Diagnostics

### Example 1: Classroom Question
- **Hindi Source**: `कल स्कूल कौन नहीं आया था?`
- **Model B**: `होला स्कूल ओकोए काएः तइन केना।`
  - *Linguistic analysis*: Correctly translates `कल` (yesterday) $\to$ `होला`, `कौन` $\to$ `ओकोए`, `नहीं आया था` $\to$ `काएः तइन केना` (negative 3rd person singular past).
- **mT5-small-lora**: `नेआ ते रे स्कूल कौन आञः।`
  - *Linguistic analysis*: Unconnected filler string. Copies Hindi word `कौन`. Emits 1st person singular clitic `आञः` ("my"). Meaning is completely lost.

### Example 2: Classroom Instruction
- **Hindi Source**: `इस पाठ का मतलब कौन समझाएगा?`
- **Model B**: `ने कजि रेआः माने ओकोए इतुआना।`
  - *Linguistic analysis*: Translates `इस` $\to$ `ने`, `बात/पाठ` $\to$ `कजि`, `का मतलब` $\to$ `रेआः माने`, `कौन समझाएगा/जानेगा` $\to$ `ओकोए इतुआना`.
- **mT5-small-lora**: `नेआ ते आञ रे काः जाना।`
  - *Linguistic analysis*: Emits `नेआ` (this), `ते` (from/by), `आञ` (me), `रे` (in), `काः` (not), `जाना` (Hindi go/passive). Total syntactic and semantic gibberish.

### Example 3: Semantic Hallucination
- **Hindi Source**: `महिलाएँ गीत गा रही हैं।`
- **Model B**: `कुड़िको दुरं दुरं तनाको।`
  - *Linguistic analysis*: Correctly identifies `महिलाएँ` $\to$ `कुड़िको` (women, animate plural), `गीत गा रही हैं` $\to$ `दुरं दुरं तनाको` (singing present continuous 3rd person plural).
- **mT5-small-lora**: `नेआ महिलाएँ गीत गा: रे आञः पुरुष गीत गीत।`
  - *Linguistic analysis*: Copies Hindi words `महिलाएँ गीत`, hallucinates `पुरुष` (men), duplicates `गीत गीत`. Extreme hallucination.

---

## 14. Android Feasibility & Compression (Step 13)
- **Direct Edge Deployment**: `google/mt5-small` requires **1.2 GB** for model weights alone, which is **60x larger** than our 20 MB offline budget for low-cost Android smartphones ($<2$GB RAM).
- **Inference Latency**: Mean latency on 14 CPU threads is **415.99 ms** per sample. On a physical low-power ARM mobile processor (e.g. MediaTek Helio G35), CPU inference for a 300M parameter model would exceed 5,000–10,000 ms, causing severe ANRs (Application Not Responding).
- **Distillation Teacher Feasibility**: Because `google/mt5-small-lora` achieved only 0.91 BLEU and failed to learn Mundari grammar under LoRA fine-tuning, **it cannot even serve as an effective teacher model for student distillation**.

---

## 15. Regression & System Integrity (Step 16)
1. **Pytest Regression Suite**:
   - Ran `pytest` across all existing tests.
   - Result: **213 passed, 0 failed** in 44.89s.
2. **Android Unit Test Suite**:
   - Ran `.\android\gradlew.bat -p android testDebugUnitTest`.
   - Result: **BUILD SUCCESSFUL** (23 actionable tasks: 1 executed, 22 up-to-date).
3. **Live Browser DOM Prototype Validation**:
   - Executed `scratch/test_phase16_browser_validation.js` against live bridge server `http://localhost:8080/`.
   - Inputs verified:
     - `FAILURE_A` (`साइबर सिक्योरिटी एक खतरनाक सब्जेक्ट है।`): Safely blocked by Tier 2 Quality Gate (`[Out of Vocabulary — Requires Linguistic Validation]`).
     - `FAILURE_B` (`आज हम सब गाना गाएंगे।`): Safely blocked by Tier 2 Quality Gate (`[Out of Vocabulary — Requires Linguistic Validation]`).
     - `BENCH_1` (`कल स्कूल कौन नहीं आया था?`): Passed Tier 2 Neural AI (`होला स्कूल ओकोए काएः तइन केना।`, Likelihood 21%).
     - `BENCH_2` (`इस पाठ का मतलब कौन समझाएगा?`): Passed Tier 2 Neural AI (`ने कजि रेआः माने ओकोए इतुआना।`, Likelihood 23%).
     - `GREETING_CANONICAL` (`नमस्ते`): Passed Tier 1 Canonical Lookup (`जोहार`).
   - Screenshots captured and verified in `scratch/screenshots/phase16_*.png`.

---

## 16. Final Recommendation & Model Selection Decision (Step 14)
Under the five mandatory criteria established in Step 14:
1. *Materially improve reference metrics on the same split*: **FAILED** (0.91 BLEU vs Model B's 42.73 BLEU).
2. *Improve unseen generalization behavior*: **FAILED** (mT5 produces repetitive pseudo-Mundari templates).
3. *Reduce suspicious semantic failures*: **FAILED** (hallucinates antonyms such as `पुरुष` for `महिलाएँ`).
4. *Do not simply copy Hindi*: **FAILED** (copies raw Hindi phrases like `गाना जाना`, `कंप्यूटर सीखना`).
5. *Potentially compressible to offline target*: **FAILED** (300M parameter model is 32x larger and produces unviable translations).

### DECISION:
**MODEL B IS DECISIVELY AND OBJECTIVELY RETAINED AS THE BEST AND OFFICIAL TRANSLATION MODEL.**
No replacement of Model B will occur. The production Android offline engine, TorchScript export, and browser translation bridge remain 100% powered by Model B.

---

## 17. Final Status Block

```
PHASE16_STATUS: COMPLETE
PRETRAINED_MODEL_TESTED: google/mt5-small-lora
PRETRAINED_MODEL_SUPPORTS_MUNDARI: NO
GPU_AVAILABLE: YES_RTX_3050_6GB_CPU_MULTI_THREAD_USED
BASELINE_TEST_SPLIT: data/processed/nmt_v2/test.tsv
BEST_MODEL: Model_B_Baseline
BASELINE_BLEU: 42.73
BEST_BLEU: 42.73
BASELINE_CHRF: 50.84
BEST_CHRF: 50.84
FAILURE_A: SAFELY_REJECTED_BY_QUALITY_GATE
FAILURE_B: SAFELY_REJECTED_BY_QUALITY_GATE
UNSEEN_20: MODEL_B_RETAINED_55PCT_PASS_ACCURATE_MT5_DEGENERATE
CHALLENGE_50: MODEL_B_RETAINED_56PCT_PASS_ACCURATE_MT5_DEGENERATE
MODEL_REPLACED: NO
ANDROID_INTEGRATION: UNCHANGED_MODEL_B_STANDALONE
FULL_TEST_RESULT: 213_PASSED_0_FAILED
ANDROID_TEST_RESULT: BUILD_SUCCESSFUL_ALL_PASSED
PHYSICAL_DEVICE_STATUS: NOT_MEASURED_NO_PHYSICAL_DEVICE
```
