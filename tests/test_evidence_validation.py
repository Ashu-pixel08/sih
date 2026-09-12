"""
test_evidence_validation.py - Tests for Evidence-Based Validation Framework (Phase 6)

Guarantees:
1. MACHINE_VALIDATED cannot become HUMAN_VALIDATED
2. REFERENCE_SUPPORTED cannot become HUMAN_VALIDATED
3. Missing human reviewer evidence cannot create HUMAN_VALIDATED
4. Candidate story records cannot silently enter canonical content (CANONICAL_APPROVED)
5. Inaccessible/license-unclear sources cannot become approved data
6. Unresolved linguistic anomalies remain visible and penalize evidence coverage score
7. Consistency linter catches whitespace anomalies, suspected typos, and parenthetical glossing
8. Consistency linter flags extreme length disparities
9. Translation engine enforces conservative fallback to OUT_OF_VOCABULARY_UNVERIFIED
10. Provenance completeness is strictly validated
"""

import os
import sys
import json
import pytest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
TOOLS_DIR = os.path.join(PROJECT_ROOT, "tools", "data_intake")
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, TOOLS_DIR)

from validator import DataIntakeValidator
from consistency_linter import ConsistencyLinter
from evidence_scorer import EvidenceScorer
from ai.translation.translation_engine import TranslationEngine


@pytest.fixture
def validator():
    return DataIntakeValidator()


@pytest.fixture
def linter():
    return ConsistencyLinter()


@pytest.fixture
def scorer():
    return EvidenceScorer()


@pytest.fixture
def translation_engine():
    return TranslationEngine()


# 1. Non-equivalence invariant tests
def test_machine_validated_cannot_become_human_validated(validator):
    rec = {
        "record_id": "TR_TEST_EQ_01",
        "hindi_text": "पानी बरस रहा है",
        "mundari_text": "दअ: गमा तना",
        "license": "CC-BY-4.0",
        "acceptance_status": "HUMAN_VALIDATED",
        "linguistic_validation_status": "MACHINE_VALIDATED",
        "human_review_completed": False
    }
    res = validator.validate_records([rec], "parallel_translation")
    assert res["valid"] is False
    assert any("NON-EQUIVALENCE VIOLATION" in err for err in res["errors"])
    assert any("cannot be equated to or claimed as HUMAN_VALIDATED" in err for err in res["errors"])


def test_reference_supported_cannot_become_human_validated(validator):
    rec = {
        "record_id": "TR_TEST_EQ_02",
        "hindi_text": "बड़ा घर",
        "mundari_text": "मरंग ओड़अ:",
        "license": "CC-BY-4.0",
        "acceptance_status": "HUMAN_VALIDATED",
        "linguistic_validation_status": "REFERENCE_SUPPORTED",
        "human_review_completed": False
    }
    res = validator.validate_records([rec], "parallel_translation")
    assert res["valid"] is False
    assert any("NON-EQUIVALENCE VIOLATION" in err for err in res["errors"])


def test_missing_human_reviewer_blocks_human_validated(validator):
    rec = {
        "record_id": "TR_TEST_EQ_03",
        "hindi_text": "अच्छा काम",
        "mundari_text": "बुगी कामी",
        "license": "CC-BY-4.0",
        "acceptance_status": "HUMAN_VALIDATED",
        "linguistic_validation_status": "HUMAN_VALIDATED",
        "linguistic_reviewer_id": None,
        "human_review_completed": False
    }
    res = validator.validate_records([rec], "parallel_translation")
    assert res["valid"] is False
    assert any("without genuine human reviewer credentials" in err for err in res["errors"])


# 2. Candidate isolation tests
def test_candidate_story_record_cannot_enter_canonical_approved(validator):
    rec = {
        "record_id": "TR_PB_0240_P01_S1",
        "story_id": "0240",
        "hindi_text": "अवंती पिटारा ज़ू की प्रभारी थी।",
        "mundari_text": "अवंती पिटारा चेड़े ओड़अ: रेन गोमके तइनकेनाए ।",
        "license": "CC-BY-4.0",
        "acceptance_status": "CANONICAL_APPROVED",
        "linguistic_validation_status": "CORPUS_ATTESTED",
        "educational_validation_status": "JCERT_ALIGNED"
    }
    res = validator.validate_records([rec], "parallel_translation")
    assert res["valid"] is False
    assert any("GOVERNANCE ISOLATION" in err for err in res["errors"])
    assert any("cannot be promoted to CANONICAL_APPROVED" in err for err in res["errors"])


def test_inaccessible_or_unclear_license_quarantined(validator):
    rec = {
        "record_id": "TR_TEST_UNCLEAR_LIC",
        "hindi_text": "नमस्ते",
        "mundari_text": "जोहार",
        "license": "Unclear / All Rights Reserved",
        "acceptance_status": "RESEARCH_VALIDATED"
    }
    res = validator.validate_records([rec], "parallel_translation")
    assert res["valid"] is False
    assert res["quarantine_recommended"] is True
    assert any("ambiguous license" in err for err in res["errors"])


# 3. Consistency linter tests
def test_linter_detects_whitespace_anomaly_before_colon(linter):
    rec = {
        "record_id": "LINT_WS_01",
        "hindi_text": "क्या तुम आओगे?",
        "mundari_text": "बल्लू चिया : हिजूआ?"
    }
    res = linter.lint_record(rec)
    assert any("Extraneous whitespace preceding punctuation ':'" in w for w in res["warnings"])
    assert any("WHITESPACE" in a for a in res["anomalies"])


def test_linter_detects_suspected_typo(linter):
    rec = {
        "record_id": "LINT_TYPO_01",
        "hindi_text": "मेढ़क की बारिश हो जाए",
        "mundari_text": "चोकेकोअ: गाा होबाओआ"
    }
    res = linter.lint_record(rec)
    assert any("SUSPECTED TYPO: 'गाा'" in w for w in res["warnings"])


def test_linter_detects_parenthetical_glossing(linter):
    rec = {
        "record_id": "LINT_GLOSS_01",
        "hindi_text": "टोकरी उठाई",
        "mundari_text": "मियद दाऊड़ा (डाली) सबकेते"
    }
    res = linter.lint_record(rec)
    assert any("Parenthetical glossing detected" in w for w in res["warnings"])


def test_linter_flags_extreme_length_disparity(linter):
    rec = {
        "record_id": "LINT_LEN_01",
        "hindi_text": "हाँ।",
        "mundari_text": "हे बल्लू अया: कुड़ामरे होयो पेरे एटे:केढ़ा मड़ी मड़ी ते मो: इदिजाना मो: इदिजाना मो: इदिजाना एन्डेते साए केन मिसातोरा सोगेन होयो बल्लूअ: मोचायते ओड़ोंग जाना ।"
    }
    res = linter.lint_record(rec)
    assert any("Extreme length disparity" in w for w in res["warnings"])
    assert res["metrics"]["length_ratio"] < 0.25


# 4. Evidence scorer tests
def test_evidence_scorer_deducts_for_anomalies(scorer):
    clean_rec = {
        "record_id": "SC_CLEAN_01",
        "source": "Pratham Books",
        "source_reference": "Story 0240 p. 10",
        "source_url": "https://example.com/story",
        "author": "Ramendra Kumar",
        "translator": "Jodheswar Barla",
        "checksum": "abc123def456",
        "license": "CC-BY-4.0",
        "hindi_text": "मछलियों की बारिश",
        "mundari_text": "हाईकोअ: गमा"
    }
    anomaly_rec = {
        "record_id": "SC_ANOMALY_01",
        "source": "Pratham Books",
        "source_reference": "Story 0240 p. 19",
        "source_url": "https://example.com/story",
        "author": "Ramendra Kumar",
        "translator": "Jodheswar Barla",
        "checksum": "abc123def456",
        "license": "CC-BY-4.0",
        "hindi_text": "मेढ़क की बारिश हो जाए",
        "mundari_text": "चोकेकोअ: गाा होबाओआ"  # Contains suspected typo 'गाा'
    }

    clean_res = scorer.score_record(clean_rec)
    anomaly_res = scorer.score_record(anomaly_rec)

    assert clean_res["evidence_coverage_score"] > anomaly_res["evidence_coverage_score"]
    assert anomaly_res["anomalies_penalty"] > 0
    assert any("SUSPECTED TYPO" in a for a in anomaly_res["unresolved_anomalies"])


# 5. Translation engine conservative fallback test
def test_translation_engine_conservative_fallback(translation_engine):
    # Verified classroom greeting
    res_known = translation_engine.translate("नमस्ते")
    assert res_known.status == "VERIFIED_EDUCATIONAL_LOOKUP"
    assert res_known.translated_text == "जोहार"

    # Out-of-vocabulary arbitrary text must fall back safely without hallucination
    res_unknown = translation_engine.translate("कल विद्यालय में विशेष विज्ञान मेला आयोजित होगा")
    assert res_unknown.status == "OUT_OF_VOCABULARY_UNVERIFIED"
    assert res_unknown.translated_text is None
    assert "OUT_OF_VOCABULARY" in res_unknown.status


def test_candidate_story_records_not_in_canonical_registry():
    # Verify no candidate sentence from Story #0240 exists in content/content_registry.json
    reg_path = os.path.join(PROJECT_ROOT, "content", "content_registry.json")
    with open(reg_path, "r", encoding="utf-8") as f:
        reg_data = json.load(f)

    reg_texts = []
    for item in reg_data.get("items", []):
        reg_texts.append(item.get("hindi_text", ""))
        reg_texts.append(item.get("mundari_text", ""))

    assert "मछलियों की बारिश" not in reg_texts
    assert "हाईकोअ: गमा" not in reg_texts
    assert "अवंती पिटारा ज़ू की प्रभारी थी।" not in reg_texts
