# SIH260042: Field Session Audio Ingestion & QA Dry-Run Report

**Project**: AI-Powered Vernacular Pedagogy & Real-Time Translation Tool (Jharkhand)  
**Target Language**: Mundari (`unr`)  
**Session ID**: `SESS_20260904_KHUNTI_MOCK_DRYRUN`  
**Session Location**: Khunti Primary School (Mock Simulation)  
**Generated Date**: 2026-09-04  
**Execution Type**: AUTOMATED DRY-RUN (MOCK FIXTURES FOR PIPELINE VALIDATION)  

---

> [!CAUTION]
> **Data Authenticity Notice**:
> This ingestion run was executed using **strictly labeled synthetic mock audio fixtures** to validate software ingestion mechanics, acoustic QA validation gates, and speaker-disjoint splitting.
> **Zero real Mundari speech recordings** were created or modified during this test.
> Production status remains:
> - Real Isolated 1–20 Audio: **MISSING**
> - Native Speaker Verification: **PENDING FIELD COLLECTION**
> - Real 1–20 Speech Recognition Accuracy: **UNVERIFIED**
> - NIPUN Bharat Competency Codes: **UNVERIFIED**

---

## 1. Session Ingestion & Acoustic QA Audit

| Metric | Result | Operational Meaning |
| :--- | :---: | :--- |
| **Total Ingested Recordings** | **77** | Raw takes scanned in session directory |
| **Technically Passed & Accepted** | **72** | Satisfied all 8 signal specification thresholds |
| **Technically Rejected & Quarantined** | **5** | Caught by automated signal quality gate |
| **Total Audio Duration** | **1.27 min** | Cumulative duration of ingested audio |
| **Schema Validation Status** | **VALID DRAFT 2020-12** | Conforms to `recording_manifest.schema.json` |

### Technical Rejection Breakdown
- **`REC_MOCK_ERR_CLIPPED_SPK_C01_NUM01`** (SPK_C01): Technical rejection: Clipping detected: peak 0.00 dBFS exceeds limit -1.0 dBFS (6064 saturated samples).; Audio energy -3.07 dBFS is too loud (> -16.0 dBFS).; DC offset 0.0060 exceeds threshold 0.005.
- **`REC_MOCK_ERR_WRONG_SR_SPK_C02_NUM02`** (SPK_C02): Technical rejection: Sampling rate 8000 != 16000 Hz.
- **`REC_MOCK_ERR_STEREO_SPK_F01_NUM03`** (SPK_F01): Technical rejection: Channel count 2 != 1 (must be mono).
- **`REC_MOCK_ERR_LOW_ENERGY_SPK_M01_NUM04`** (SPK_M01): Technical rejection: Audio energy -54.05 dBFS is too low (< -28.0 dBFS).; Estimated SNR 1.2 dB is below minimum threshold 22.0 dB.
- **`REC_MOCK_ERR_TOO_SHORT_SPK_C03_NUM05`** (SPK_C03): Technical rejection: Audio energy -54.08 dBFS is too low (< -28.0 dBFS).; Utterance duration 200.0 ms < minimum 400.0 ms.; Estimated SNR 1.2 dB is below minimum threshold 22.0 dB.

---

## 2. Speaker-Disjoint Partitioning & Split Allocations

All `72` accepted recordings were partitioned into speaker-disjoint splits to guarantee zero evaluation leakage.

| Split Name | Speaker Count | Assigned Speakers | Token Count | Percentage |
| :--- | :---: | :--- | :---: | :---: |
| **Train** | 4 | `SPK_C02, SPK_C04, SPK_F01, SPK_M01` | 48 | 66.7% |
| **Validation** | 1 | `SPK_C01` | 12 | 16.7% |
| **Test** | 1 | `SPK_C03` | 12 | 16.7% |
| **TOTAL** | **6** | — | **72** | **100.0%** |

---

## 3. Data Leakage Verification Audit

| Leakage Audit Dimension | Audit Status | Audit Details |
| :--- | :---: | :--- |
| **Speaker ID Disjointness** | `PASS (0 speaker overlap)` | $\text{Train} \cap \text{Val} = \emptyset, \text{Train} \cap \text{Test} = \emptyset, \text{Val} \cap \text{Test} = \emptyset$ |
| **Recording ID Disjointness** | `PASS (0 duplicate recording IDs)` | Zero overlapping recording IDs across splits |
| **Audio File Path Disjointness** | `PASS (0 duplicate file paths)` | Zero duplicate audio file paths across splits |
| **Augmentation Confinement** | `PASS (0 cross-split)` | All augmented derivatives strictly inherit source split |

---

## 4. Collection Target Audit & Volume Projection

Comparison of current dry-run batch against the approved field protocol collection targets:

| Parameter | Approved Protocol Target | Current Dry-Run Batch | Target Status |
| :--- | :---: | :---: | :--- |
| **Total Native Speakers** | **30 speakers** | 6 speakers | Target for field campaign |
| **Primary Children (Girls)** | 8 speakers | 2 speakers | Target for field campaign |
| **Primary Children (Boys)** | 8 speakers | 2 speakers | Target for field campaign |
| **Adult Native Females** | 8 speakers | 1 speaker | Target for field campaign |
| **Adult Native Males** | 6 speakers | 1 speaker | Target for field campaign |
| **Isolated Repetitions** | 6 per numeral | 2 per numeral | Target for field campaign |
| **Carrier Repetitions** | 2 per numeral | 0 in mini-batch | Target for field campaign |
| **Target Speech Tokens** | **4,800 tokens** | 72 tokens | Target for field campaign |
| **Background Noise Tokens** | **1,200 tokens** | 12 tokens | Target for field campaign |
| **Total Curated Assets** | **6,000 assets** | 77 assets | Target for field campaign |

> [!NOTE]
> The figures above are **COLLECTION TARGETS** for the planned native speaker field acquisition campaign in Jharkhand primary schools. They are not guaranteed requirements proven by the current sample.
