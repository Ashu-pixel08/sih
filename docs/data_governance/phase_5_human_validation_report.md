# Phase 5 Human Validation Preparation & Linguistic QA Report

**Project Identifier:** SIH260042 (`APP_NAME_PENDING`)  
**Phase:** Phase 5 — Human Validation Preparation & Linguistic QA  
**Date:** September 6, 2026  
**Governance Standard:** Anti-Fabrication Gatekeeping, Dual-Track QA & OOV Quarantine  
**Production Code Impact:** Zero runtime code modified (Strictly governance tests & intake validation safeguards)

---

## 1. Executive Summary

Phase 5 transitions the project from open-license data acquisition (Phase 4) into structured **Human Linguistic Validation Preparation**. In compliance with project governance rules, automated systems must never fabricate human validation, claim unverified endorsements, or promote candidate literature directly into canonical educational content.

During this phase:
1. All **27 candidate records** in `data/incoming/pratham_0240.json` were audited by automated gatekeepers across linguistic, orthographic, and educational dimensions.
2. A structured machine-readable review template was created: [pratham_0240_human_review_template.json](file:///C:/Users/chatu/.gemini/antigravity/scratch/vernacular_fln_assistant/data/incoming/pratham_0240_human_review_template.json), containing dedicated empty review fields for independent native-speaker linguists and primary educators.
3. A formal 13-section academic review packet was authored: [phase_5_human_validation_packet.md](file:///C:/Users/chatu/.gemini/antigravity/scratch/vernacular_fln_assistant/docs/data_governance/phase_5_human_validation_packet.md), detailing dual-track review rubrics (Linguistic & Educational) and flagging suspected orthographic issues for expert determination.
4. An objective institutional directory of potential academic reviewers was cataloged: [potential_mundari_reviewers.md](file:///C:/Users/chatu/.gemini/antigravity/scratch/vernacular_fln_assistant/docs/data_governance/potential_mundari_reviewers.md), with all participation statuses marked **`NOT_CONFIRMED`**.
5. Automated validation safeguards in `tools/data_intake/validator.py` and `tests/test_data_intake_contract.py` were reinforced with 4 new governance tests, ensuring that records awaiting review, records with fake reviewer IDs (e.g. `AUTO`, `AI`), or records with rejected dispositions can never bypass quarantine into production.

---

## 2. Summary of Files Created & Modified

| File Path | Nature of Change | Purpose |
| :--- | :--- | :--- |
| `data/incoming/pratham_0240_human_review_template.json` | **[NEW]** | Machine-readable review template containing all 27 records with empty/pending human review fields. |
| `docs/data_governance/phase_5_human_validation_packet.md` | **[NEW]** | Comprehensive 13-section academic evaluation dossier and dual-track rubric for accredited reviewers. |
| `docs/data_governance/potential_mundari_reviewers.md` | **[NEW]** | Institutional registry of publicly verified potential academic validators (all status `NOT_CONFIRMED`). |
| `docs/data_governance/phase_5_human_validation_report.md` | **[NEW]** | Authoritative audit and status report for Phase 5. |
| `tools/data_intake/validator.py` | **[MODIFIED]** | Strengthened `DataIntakeValidator` canonical promotion safety gate against fake reviewers and unapproved dispositions. |
| `tests/test_data_intake_contract.py` | **[MODIFIED]** | Added 4 automated regression tests enforcing human sign-off gates and canonical isolation. |

---

## 3. Automation Audit vs. Human Review Status

* **Total Candidate Records Staged:** **27 records**
* **Records Reviewed by Automated Linters / Schemas:** **27 records (100%)**
  * Syntactic schema validation: **PASS** (`parallel_translation.schema.json`)
  * Character encoding & normalization: **PASS** (100% NFC Devanagari)
  * Suspicious untranslated string check: **PASS** (0 untranslated placeholders)
  * Duplicate pair detection: **PASS** (0 duplicates)
* **Records Still Awaiting Human Review:** **27 records (100%)**
  * Linguistic Review Status: `PENDING_HUMAN_REVIEW` (27 / 27)
  * Educational Review Status: `PENDING_HUMAN_REVIEW` (27 / 27)
  * Final Committee Disposition: `PENDING_COMMITTEE_DECISION` (27 / 27)

---

## 4. Key Orthography Concerns Flagged for Expert Linguist

An in-depth orthographic audit of Jodheswar Barla's Devanagari Mundari text identified five specific phenomena that require formal determination by an accredited native linguist:

1. **Devanagari Glottal / Checked Vowel Colon Notation:**
   - The text uses ASCII colon (`:`) to mark checked vowels and glottal stops (`ʔ`), e.g., in genitive endings (`हाईकोअ:`, `बल्लूगअ:`, `चोकेकोअ:`), lexical roots (`ओड़अ:`, `दअ:`, `पेड़े:`, `ती:`, `होटो:`), and verb aspect markers (`एटे:केढ़ा`).
   - *Linguistic Question:* Does regional classroom pedagogy in Jharkhand recommend ASCII colon (`:`), Visarga (`ः`), or traditional Devanagari combinations?
2. **Probable Transcription Typo in Record 20 (`TR_PB_0240_P19_S7`):**
   - Text reads: *"चोकेकोअ: गाा होबाओआ"* instead of *"चोकेकोअ: गमा होबाओआ"* (rain of frogs).
   - *Recommendation for Reviewer:* Confirm correction of `गाा` to `गमा` under disposition `REVISE_ORTHOGRAPHY`.
3. **Spelling Inconsistency for Verb "Extinguish" (`iɽiŋ`):**
   - Scene 2 (`P05`): `इड़िंग`
   - Scene 3 (`P07`): `इड़िं:` (with anusvara and colon)
   - Scene 7 (`P17`): `इंड़ी`
   - *Recommendation for Reviewer:* Standardize on a single orthographic convention for classroom instruction.
4. **Typographical Spacing in Interrogative (`P05`):**
   - Text contains an extraneous space before colon: `बल्लू चिया : ने दिया कोके...`.
   - *Recommendation for Reviewer:* Remove space to yield `चिया:`.
5. **Loanword vs. Vernacular Balance:**
   - Record 16 (`P15`) retains Hindi/Sanskrit loanword: `धन्यवाद मेताइया`.
   - Record 12 (`P11`) glosses traditional bamboo basket `दाऊड़ा` with Sadri/Hindi loanword `(डाली)`.
   - *Recommendation for Reviewer:* Evaluate whether young Grade 1–2 learners benefit from retaining these glosses or using pure Mundari terms.

---

## 5. Potential Reviewer Institutional Directory Status

| Named Academic / Entity | Institutional Affiliation | Evidence Base | Outreach Status | Consent / Agreement Status |
| :--- | :--- | :--- | :---: | :---: |
| **Dr. Juran Singh Manki** | Head, Dept. of Mundari, DSPMU Ranchi | Official DSPMU Faculty Portal | Not Contacted | **`NOT_CONFIRMED`** |
| **Sri T. N. S. Munda** | Asst. Professor, Dept. of TRL, DSPMU Ranchi | Official DSPMU University Directory | Not Contacted | **`NOT_CONFIRMED`** |
| **Prof. Tanmoy Bhattacharya**| Professor of Linguistics, University of Delhi | Official DU Linguistics Faculty Site | Not Contacted | **`NOT_CONFIRMED`** |
| **Sri Jodheswar Barla** | Translator, StoryWeaver / Pratham Books | StoryWeaver Entry 4279 Metadata | Not Contacted | **`NOT_CONFIRMED`** |

*Under no circumstances should any marketing, presentation, or documentation claim that any of these scholars have validated or endorsed the application.*

---

## 6. Verification & Test Results

1. **Data Intake Contract & Governance Suite:**
   - Command: `.venv\Scripts\python -m pytest tests/test_data_intake_contract.py`
   - **Result:** **13 passed in 0.04s (100%)**
   - Specifically verified:
     * `test_validator_blocks_pending_review_canonical_promotion`: **PASS**
     * `test_validator_blocks_fake_or_default_reviewer_signoff`: **PASS**
     * `test_validator_blocks_rejected_or_unapproved_dispositions`: **PASS**
     * `test_candidate_records_isolated_from_canonical_registry`: **PASS**
2. **Cross-Platform & Content Registry Parity:**
   - Command: `.venv\Scripts\python -m pytest tests/test_content_registry.py tests/test_cross_platform_parity.py`
   - **Result:** **12 passed in 0.04s (100%)**
3. **Full Pytest Regression Suite:**
   - Command: `.venv\Scripts\python -m pytest`
   - **Result:** **151 passed (100%)** (147 existing tests + 4 new governance tests).
4. **Production Code Isolation:**
   - Confirmed: 0 files modified in `frontend/`, `android/`, `models/`, or `content/content_registry.json`.

---

## 7. Mandatory Governance Declaration

> [!CAUTION]
> ### FORMAL DECLARATION
> **NO HUMAN LINGUISTIC APPROVAL HAS OCCURRED IN PHASE 5.**  
> All 27 candidate records remain in Tier 1 quarantine status (`CANDIDATE_FOR_LINGUISTIC_VALIDATION`). No candidate translations have been merged into the broadcast-safe canonical registry or production models. Canonical promotion remains completely blocked until formal human linguistic and educational sign-offs are executed.
