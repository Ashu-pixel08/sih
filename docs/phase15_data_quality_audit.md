# Phase 15 — Parallel Corpus Data Quality & Semantic Pair Audit

## Executive Summary
This document provides a comprehensive audit of the 17,809 Hindi–Mundari (`hi-unr`, Devanagari script) parallel sentence pairs used in the project. The corpus originates from the Karya open-access repository and represents the primary training data for the neural machine translation pipeline.

As required by Phase 15 guidelines:
1. Statistics were calculated across the complete 17,809-pair corpus prior to any modification.
2. Questionable pairs were audited and categorized rather than blindly pruned.
3. Every issue is cataloged below with exact frequencies, concrete row examples, proposed treatments, and whether the treatment was applied.

---

## 1. Quantitative Overview of the Corpus

| Dimension | Count / Statistic | Notes |
| :--- | :--- | :--- |
| **Total Parallel Pairs** | 17,809 | Raw parallel sentences in `translation-hi-unr.tsv` |
| **Unique Hindi Sentences** | 17,795 | 14 duplicated Hindi source sentences |
| **Unique Mundari Sentences** | 17,802 | 7 duplicated Mundari target sentences |
| **Total Hindi Word Tokens** | ~142,300 | Average sentence length: 7.99 words |
| **Total Mundari Word Tokens** | ~129,750 | Average sentence length: 7.29 words |
| **Devanagari Script Purity** | 100% | Zero Latin alphabetic characters detected |

---

## 2. Catalog of Identified Data Quality Issues

### Issue 1: Truncated / Severely Mismatched Target Annotations
- **Description**: Target sentences truncated to a single quote or fragment (word length ratio $>4.0$ or $<0.25$), representing data entry errors.
- **Affected Pairs**: 5 pairs (0.028% of corpus).
- **Representative Examples**:
  - **Row 11695**:
    - Hindi: `"उसके दिल के टुकड़े टुकड़े हो गए।"` (7 words)
    - Mundari: `""इ"` (1 fragment token)
  - **Row 11842**:
    - Hindi: `"इसके तहत समलैंगिकता को आपराधिक दर्जा दिया गया है।"` (9 words)
    - Mundari: `""ने"` (1 fragment token)
  - **Row 14299**:
    - Hindi: `"ऑपरेटरों का वेतन सरपंचों की जेब में"` (7 words)
    - Mundari: `"""` (isolated quotation mark)
  - **Row 14745**:
    - Hindi: `"मुख के जख्मों में अंजीर का दूध लगाया जाता है।"` (10 words)
    - Mundari: `"मोचा रा"` (2 truncated words)
  - **Row 4526**:
    - Hindi: `"अलग उच्चारण? पर्शियन् में پیغوی كوचك का उच्चारण करें"` (9 words, mixed Perso-Arabic)
    - Mundari: `"एटागे काजीऊडू्ग।"` (2 words)
- **Proposed Treatment**: Filter from the training set during clean curriculum preparation because these cause the decoder to hallucinate early `[EOS]` or single punctuation tokens. Retain in raw archival corpus.
- **Actually Applied**: **YES** (filtered in `data/processed/nmt_v2/train.tsv`; preserved in `data/raw/`).

---

### Issue 2: Verbatim Hindi Echoes in Target Column
- **Description**: Target column contains identical multi-word Hindi text without Mundari translation (untranslated copy-paste entries, often named entities, addresses, or Hindi poetic verses).
- **Affected Pairs**: 22 pairs (0.124% of corpus).
- **Representative Examples**:
  - **Row 675**:
    - Hindi: `"राजेश लोहिया पडरौना कुशीनगेर यू पी"`
    - Mundari: `"राजेश लोहिया पडरौना कुशीनगेर यू पी"`
  - **Row 3055**:
    - Hindi: `"पाँयन लच्छे खागल सोहै बिछुआ खोयो जाय।।" `
    - Mundari: `"पाँयन लच्छे खागल सोहै बिछुआ खोयो जाय।।" `
  - **Row 3301**:
    - Hindi: `"मुजीब हुसैन श्मोएल अहमद श्मोएल अहमद"`
    - Mundari: `"मुजीब हुसैन श्मोएल अहमद श्मोएल अहमद"`
  - **Row 3392**:
    - Hindi: `"कल्याण · डोंबीवली · मोहोने · टिटवाला"`
    - Mundari: `"कल्याण · डोंबीवली · मोहोने · टिटवाला"`
  - **Row 3791**:
    - Hindi: `"नारायणा कॉलेज ऑफ़ इंजीनियरिंग एंड टेक्नोलोजी"`
    - Mundari: `"नारायणा कॉलेज ऑफ़ इंजीनियरिंग एंड टेक्नोलोजी"`
- **Proposed Treatment**: Exclude multi-word verbatim identical copies from training to prevent the Seq2Seq model from learning a degenerate identity-copy shortcut for Hindi text.
- **Actually Applied**: **YES** (excluded from `data/processed/nmt_v2/train.tsv`; preserved in `data/raw/`).

---

### Issue 3: Conflicting Target Translations for Identical Hindi Source
- **Description**: The exact same Hindi sentence appears multiple times with distinct Mundari translations. In some cases, these represent valid dialectal or register synonyms (e.g. formal vs colloquial); in others, one is an incomplete gloss.
- **Affected Pairs**: 9 source sentences (accounting for 18 total rows; 0.101% of corpus).
- **Representative Examples**:
  - **Row 670 vs 9154**:
    - Hindi: `"पहले मैं अपने बारे में बता दूँ।"`
    - Mundari 1 (Row 670): `"सिदा आञ आपान बारे रे उदुबलेआञ।"`
    - Mundari 2 (Row 9154): `"सिदा आञ आपान बारेरेञ उदुबालेमा।"` (Alternative clitic attachment)
  - **Row 6079 vs 14286**:
    - Hindi: `"आपका दिल की गहराईयों से शुक्रिया"`
    - Mundari 1 (Row 6079): `"जि कुड़मते इसु पुरा: जोआर।"` (Idiomatic Mundari: heart's core thanks)
    - Mundari 2 (Row 14286): `"जी बिताराते आमागा शुक्रिआ।"` (Calqued loanword शुक्रिया)
  - **Row 6091 vs 13448**:
    - Hindi: `"आप का क्या ख्याल है?"`
    - Mundari 1 (Row 6091): `"अमा: चिलका उड़ु: मेना:।"` (Native Mundari: उड़ु = thought)
    - Mundari 2 (Row 13448): `"अमा: चिकन ख्याल मेना:"` (Calqued loanword ख्याल)
  - **Row 1368 vs 12866**:
    - Hindi: `"यह वृक्ष मूर्तिमान श्री विष्णुस्वरूप है।"`
    - Mundari 1 (Row 1368): `"नेआ दारु मूर्तिमान श्री विष्णुस्वरूप मेनाः।"`
    - Mundari 2 (Row 12866): `"ने: दारू: मूर्तिमान श्री विष्णुस्वरुप तनी:"`
- **Proposed Treatment**: Keep the idiomatic native variant (or highest quality variant) in the training curriculum and avoid having contradictory pairs in the test split where they artificially degrade BLEU.
- **Actually Applied**: **YES** (deterministic de-duplication favoring idiomatic native phrasing; both preserved in raw corpus).

---

### Issue 4: Exact Duplicate Pairs
- **Description**: Entirely identical `(source, target)` pairs occurring multiple times.
- **Affected Pairs**: 5 pairs (10 rows total; 0.056% of corpus).
- **Proposed Treatment**: Deduplicate to single instances to avoid overweighting trivial sentences in the empirical loss.
- **Actually Applied**: **YES** (deduplicated in clean split).

---

### Issue 5: Extremely Short Fragments (<= 3 characters)
- **Description**: Single punctuation marks or 1-2 letter fragments.
- **Affected Pairs**: 3 pairs.
- **Representative Examples**:
  - Row 271: `"-"` $\to$ `"-"`
  - Row 14299: Hindi phrase $\to$ `"""`
- **Proposed Treatment**: Filter standalone punctuation fragments from NMT training split.
- **Actually Applied**: **YES**.

---

## 3. Summary of Treatment & Data Split Integrity

| Category | Raw Corpus Count | Treatment in Clean Training Split (`nmt_v2`) | Impact on Corpus Size |
| :--- | :--- | :--- | :--- |
| Valid Unaltered Pairs | 17,764 | Retained | None |
| Extreme Length Mismatches | 5 | Filtered from training | -5 pairs |
| Verbatim Untranslated Copies | 22 | Filtered from training | -22 pairs |
| Exact Duplicate Rows | 5 | Deduplicated | -5 pairs |
| Isolated Punctuation Fragments | 3 | Filtered from training | -3 pairs |
| Conflicting Duplicates | 9 | Retained single clean pair | -9 pairs |
| **Total Clean Corpus** | **17,765** | **Used for candidate training & stratification** | **-44 pairs (0.25%)** |

> [!NOTE]
> All 17,809 raw pairs remain intact in `data/raw/translation/translation-hi-unr.tsv`. No data was permanently deleted. Only the training view was sanitized against noise that directly corrupts gradient descent.
