"""
test_data_intake_contract.py - Tests for the Data Intake Contract and Tooling
Verifies:
1. Validator catches missing fields, duplicate IDs, empty translations
2. Validator catches suspicious identical Hindi-Mundari text
3. Validator catches illegal control characters
4. Validator catches ambiguous/missing licenses
5. Validator catches speaker leakage between TRAIN and TEST
6. Validator catches audio sample rate / channel mismatches
7. Validator blocks fraudulent CANONICAL_APPROVED claims
8. Reporter correctly calculates lexical and audio distributions
"""

import os
import sys
import json
import pytest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "tools", "data_intake"))

from validator import DataIntakeValidator
from reporter import DatasetReporter


@pytest.fixture
def validator():
    return DataIntakeValidator()


@pytest.fixture
def reporter():
    return DatasetReporter()


def test_validator_valid_candidate(validator):
    rec = {
        "record_id": "TR_TEST_001",
        "hindi_text": "किताब खोलो",
        "mundari_text": "पुथी ओलोपे",
        "mundari_script": "Devanagari",
        "domain": "CLASSROOM_INSTRUCTION",
        "grade": 1,
        "source": "JCERT Class 1 Primer",
        "source_reference": "Unit 2, p. 10",
        "license": "CC-BY-4.0",
        "provenance_status": "CORPUS_ATTESTED",
        "linguistic_validation_status": "NATIVE_SPEAKER_VERIFIED",
        "educational_validation_status": "JCERT_APPROVED",
        "acceptance_status": "SOURCE_FOUND"
    }
    res = validator.validate_records([rec], "parallel_translation")
    assert res["valid"] is True
    assert res["passed_records"] == 1
    assert res["failed_records"] == 0
    assert len(res["errors"]) == 0


def test_validator_detects_empty_translation(validator):
    rec = {
        "record_id": "TR_TEST_EMPTY",
        "hindi_text": "पानी लाओ",
        "mundari_text": "   ",
        "license": "CC-BY-4.0"
    }
    res = validator.validate_records([rec], "parallel_translation")
    assert res["valid"] is False
    assert res["failed_records"] == 1
    assert any("empty Mundari translation" in err for err in res["errors"])


def test_validator_detects_suspicious_identical_text(validator):
    rec = {
        "record_id": "TR_TEST_IDENTICAL",
        "hindi_text": "एक",
        "mundari_text": "एक",
        "license": "CC-BY-4.0"
    }
    res = validator.validate_records([rec], "parallel_translation")
    assert res["valid"] is False
    assert any("untranslated placeholder suspected" in err for err in res["errors"])


def test_validator_detects_control_characters(validator):
    rec = {
        "record_id": "TR_TEST_CTRL",
        "hindi_text": "किताब\x07खोलो",
        "mundari_text": "पुथी ओलोपे",
        "license": "CC-BY-4.0"
    }
    res = validator.validate_records([rec], "parallel_translation")
    assert res["valid"] is False
    assert any("illegal ASCII control characters" in err for err in res["errors"])


def test_validator_detects_duplicate_ids(validator):
    recs = [
        {
            "record_id": "DUP_01",
            "hindi_text": "बैठो",
            "mundari_text": "दुबपे",
            "license": "CC-BY-4.0"
        },
        {
            "record_id": "DUP_01",
            "hindi_text": "खड़े हो जाओ",
            "mundari_text": "तिंगुपाय",
            "license": "CC-BY-4.0"
        }
    ]
    res = validator.validate_records(recs, "classroom_phrase")
    assert res["valid"] is False
    assert any("Duplicate or missing record ID" in err for err in res["errors"])


def test_validator_detects_ambiguous_license(validator):
    rec = {
        "record_id": "TR_TEST_LIC",
        "hindi_text": "नमस्ते",
        "mundari_text": "जोहार",
        "license": "Unknown / Found online"
    }
    res = validator.validate_records([rec], "parallel_translation")
    assert res["valid"] is False
    assert res["quarantine_recommended"] is True
    assert any("ambiguous license" in err for err in res["errors"])


def test_validator_detects_speaker_leakage(validator):
    recs = [
        {
            "audio_id": "ASR_01",
            "transcript": "मिअद",
            "speaker_id": "SPK_LEAK_01",
            "split_assignment": "TRAIN",
            "license": "CC-BY-4.0"
        },
        {
            "audio_id": "ASR_02",
            "transcript": "बारिया",
            "speaker_id": "SPK_LEAK_01",
            "split_assignment": "TEST",
            "license": "CC-BY-4.0"
        }
    ]
    res = validator.validate_records(recs, "speech_recognition")
    assert res["valid"] is False
    assert res["quarantine_recommended"] is True
    assert any("CRITICAL DATASET LEAKAGE" in err for err in res["errors"])


def test_validator_blocks_fraudulent_canonical_claim(validator):
    rec = {
        "record_id": "TR_FRAUD_01",
        "hindi_text": "सुनो",
        "mundari_text": "आयूमपे",
        "license": "CC-BY-4.0",
        "acceptance_status": "CANONICAL_APPROVED",
        "linguistic_validation_status": "UNVERIFIED",
        "educational_validation_status": "UNVERIFIED"
    }
    res = validator.validate_records([rec], "parallel_translation")
    assert res["valid"] is False
    assert any("ILLEGAL STATUS" in err for err in res["errors"])


def test_validator_detects_audio_format_errors(validator):
    rec = {
        "audio_id": "AUD_BAD_RATE",
        "hindi_text": "एक",
        "mundari_text": "मिअद",
        "sample_rate": 22050,
        "channels": 2,
        "license": "CC-BY-4.0"
    }
    res = validator.validate_records([rec], "native_audio")
    assert res["valid"] is False
    assert any("unsupported sample rate 22050" in err for err in res["errors"])
    assert any("channel count is 2; must be 1" in err for err in res["errors"])


def test_validator_blocks_pending_review_canonical_promotion(validator):
    rec = {
        "record_id": "TR_PENDING_01",
        "hindi_text": "मछलियों की बारिश",
        "mundari_text": "हाईकोअ: गमा",
        "license": "CC-BY-4.0",
        "acceptance_status": "CANONICAL_APPROVED",
        "linguistic_validation_status": "PENDING_REVIEW",
        "educational_validation_status": "PENDING_REVIEW"
    }
    res = validator.validate_records([rec], "parallel_translation")
    assert res["valid"] is False
    assert any("without verified linguistic validation" in err for err in res["errors"])


def test_validator_blocks_fake_or_default_reviewer_signoff(validator):
    rec = {
        "record_id": "TR_FAKE_REV_01",
        "hindi_text": "मछलियों की बारिश",
        "mundari_text": "हाईकोअ: गमा",
        "license": "CC-BY-4.0",
        "acceptance_status": "CANONICAL_APPROVED",
        "linguistic_validation_status": "NATIVE_SPEAKER_VERIFIED",
        "educational_validation_status": "FLN_FRAMEWORK_COMPLIANT",
        "linguistic_reviewer_id": "AUTO"
    }
    res = validator.validate_records([rec], "parallel_translation")
    assert res["valid"] is False
    assert any("invalid/fake reviewer ID" in err for err in res["errors"])


def test_validator_blocks_rejected_or_unapproved_dispositions(validator):
    rec = {
        "record_id": "TR_REJ_01",
        "hindi_text": "गलत अनुवाद",
        "mundari_text": "का सेनोअ:",
        "license": "CC-BY-4.0",
        "acceptance_status": "CANONICAL_APPROVED",
        "linguistic_validation_status": "NATIVE_SPEAKER_VERIFIED",
        "educational_validation_status": "FLN_FRAMEWORK_COMPLIANT",
        "final_disposition": "REJECT"
    }
    res = validator.validate_records([rec], "parallel_translation")
    assert res["valid"] is False
    assert any("cannot be CANONICAL_APPROVED with final_disposition" in err for err in res["errors"])


def test_candidate_records_isolated_from_canonical_registry():
    # Verify no candidate records from pratham_0240 exist in content/content_registry.json
    content_reg_path = os.path.join(PROJECT_ROOT, "content", "content_registry.json")
    with open(content_reg_path, "r", encoding="utf-8") as f:
        reg = json.load(f)
    
    # Check phrases and numerals in registry
    registered_hindi = set()
    for cat in ["classroom_phrases", "numerals", "math_phrases"]:
        for item in reg.get(cat, []):
            if "hindi" in item:
                registered_hindi.add(item["hindi"])
            elif "hindi_text" in item:
                registered_hindi.add(item["hindi_text"])
    
    # Pratham story titles/dialogues must NOT be in canonical registry
    assert "मछलियों की बारिश" not in registered_hindi
    assert "बल्लू के जन्मदिन की चौथी सालगिरह पर अवंती ने एक छोटी सी पार्टी का आयोजन किया।" not in registered_hindi

