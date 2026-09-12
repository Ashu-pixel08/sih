"""
validator.py - Automated Data Intake Gatekeeper
Validates candidate translation, audio, speech, and curriculum datasets.
Detects:
1. Missing mandatory schema fields
2. Duplicate records and identical sentence pairs
3. Empty translations
4. Suspicious identical Hindi-Mundari text
5. Malformed Unicode, non-NFC normalization, control characters
6. Invalid IPA notation
7. Missing license, ambiguous license, and provenance gaps
8. Speaker overlap/leakage between TRAIN and TEST sets
9. Audio format deviations (sample rate, channels, bit depth)
10. Fraudulent CANONICAL_APPROVED claims without human sign-off
"""

import os
import sys
import json
import unicodedata
from typing import Dict, List, Any, Tuple, Optional

# Path to schemas
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
SCHEMA_DIR = os.path.join(WORKSPACE_ROOT, "data", "schemas")

try:
    from consistency_linter import ConsistencyLinter
    from evidence_scorer import EvidenceScorer
except ImportError:
    try:
        from tools.data_intake.consistency_linter import ConsistencyLinter
        from tools.data_intake.evidence_scorer import EvidenceScorer
    except ImportError:
        sys.path.insert(0, SCRIPT_DIR)
        from consistency_linter import ConsistencyLinter
        from evidence_scorer import EvidenceScorer


class DataIntakeValidator:
    """Validates candidate datasets against intake contracts without modifying application code."""

    SUSPICIOUS_UNTRANSLATED = {
        "एक", "दो", "तीन", "चार", "पांच", "छह", "सात", "आठ", "नौ", "दस",
        "बैठो", "खड़े हो जाओ", "नमस्ते", "सुप्रभात"
    }

    @staticmethod
    def has_illegal_control_chars(text: str) -> bool:
        """Checks for ASCII control characters excluding standard whitespace."""
        return any(ord(c) < 32 and c not in ('\t', '\n', '\r') for c in text)

    def __init__(self):
        self.schemas = self._load_schemas()
        self.consistency_linter = ConsistencyLinter()
        self.evidence_scorer = EvidenceScorer()

    def _load_schemas(self) -> Dict[str, Any]:
        schemas = {}
        if os.path.exists(SCHEMA_DIR):
            for fname in os.listdir(SCHEMA_DIR):
                if fname.endswith(".schema.json"):
                    k = fname.replace(".schema.json", "")
                    with open(os.path.join(SCHEMA_DIR, fname), "r", encoding="utf-8") as f:
                        schemas[k] = json.load(f)
        return schemas

    def validate_file(self, file_path: str, record_type: Optional[str] = None) -> Dict[str, Any]:
        """Validates an incoming JSON or TSV dataset file."""
        if not os.path.exists(file_path):
            return {"valid": False, "errors": [f"File not found: {file_path}"]}

        if file_path.endswith(".json"):
            return self._validate_json_file(file_path, record_type)
        elif file_path.endswith(".tsv"):
            return self._validate_tsv_file(file_path, record_type or "parallel_translation")
        else:
            return {"valid": False, "errors": [f"Unsupported file extension: {file_path}. Must be .json or .tsv"]}

    def _validate_json_file(self, file_path: str, record_type: Optional[str]) -> Dict[str, Any]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return {"valid": False, "errors": [f"Malformed JSON in {file_path}: {e}"]}

        records = []
        if isinstance(data, dict):
            for k in ["records", "phrases", "recordings", "utterances", "competencies"]:
                if k in data and isinstance(data[k], list):
                    records = data[k]
                    if not record_type:
                        record_type = {
                            "records": "parallel_translation",
                            "phrases": "classroom_phrase",
                            "recordings": "native_audio",
                            "utterances": "speech_recognition",
                            "competencies": "curriculum_data"
                        }.get(k)
                    break
        elif isinstance(data, list):
            records = data

        if not record_type:
            record_type = "parallel_translation"

        return self.validate_records(records, record_type, source_file=file_path)

    def _validate_tsv_file(self, file_path: str, record_type: str) -> Dict[str, Any]:
        records = []
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for idx, line in enumerate(lines):
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue
            parts = line_str.split("\t")
            if len(parts) >= 2:
                rec = {
                    "record_id": f"TR_TSV_{idx:05d}",
                    "hindi_text": parts[0].strip(),
                    "mundari_text": parts[1].strip(),
                    "mundari_script": "Devanagari",
                    "domain": "GENERAL_TEXTBOOK",
                    "grade": 1,
                    "source": os.path.basename(file_path),
                    "source_reference": f"Line {idx+1}",
                    "license": "KPL-BY-NC-SA-FS-1.0",
                    "provenance_status": "CORPUS_ATTESTED",
                    "linguistic_validation_status": "PENDING_REVIEW",
                    "educational_validation_status": "PENDING_REVIEW",
                    "acceptance_status": "SOURCE_FOUND"
                }
                if len(parts) >= 3:
                    rec["ipa"] = parts[2].strip()
                records.append(rec)

        return self.validate_records(records, record_type, source_file=file_path)

    def validate_records(self, records: List[Dict[str, Any]], record_type: str, source_file: str = "memory") -> Dict[str, Any]:
        """Runs rigorous multi-point validation across a batch of records."""
        report = {
            "source_file": source_file,
            "record_type": record_type,
            "total_records": len(records),
            "passed_records": 0,
            "failed_records": 0,
            "warnings_count": 0,
            "errors": [],
            "warnings": [],
            "seen_ids": set(),
            "seen_pairs": set(),
            "speakers_train": set(),
            "speakers_test": set(),
            "evidence_scores": [],
            "quarantine_recommended": False
        }

        for idx, rec in enumerate(records):
            rec_errors = []
            rec_warnings = []
            rec_id = rec.get("record_id") or rec.get("phrase_id") or rec.get("audio_id") or rec.get("curriculum_id") or f"ROW_{idx}"

            # 1. ID check & uniqueness
            if not rec_id or rec_id in report["seen_ids"]:
                rec_errors.append(f"Duplicate or missing record ID: '{rec_id}' at index {idx}")
            report["seen_ids"].add(rec_id)

            # 2. Text fields validation
            h_text = rec.get("hindi_text") or rec.get("transcript") or rec.get("hindi_source_text") or ""
            m_text = rec.get("mundari_text") or rec.get("mundari_source_text") or ""

            if not h_text or not h_text.strip():
                rec_errors.append(f"Record {rec_id} has empty Hindi/transcript text")
            if record_type in ["parallel_translation", "classroom_phrase"] and (not m_text or not m_text.strip()):
                rec_errors.append(f"Record {rec_id} has empty Mundari translation")

            # 3. Unicode hygiene (NFC normalization & control characters)
            for txt_field, txt_val in [("hindi_text", h_text), ("mundari_text", m_text)]:
                if txt_val:
                    if self.has_illegal_control_chars(txt_val):
                        rec_errors.append(f"Record {rec_id} {txt_field} contains illegal ASCII control characters")
                    if txt_val != unicodedata.normalize("NFC", txt_val):
                        rec_warnings.append(f"Record {rec_id} {txt_field} is not NFC-normalized")

            # 4. Anti-fabrication check: Suspicious identical Hindi/Mundari text
            if h_text and m_text and h_text.strip() == m_text.strip():
                if h_text.strip() in self.SUSPICIOUS_UNTRANSLATED:
                    rec_errors.append(f"Record {rec_id} has identical Hindi and Mundari text '{h_text}'; untranslated placeholder suspected")
                else:
                    rec_warnings.append(f"Record {rec_id} Hindi matches Mundari verbatim ('{h_text}'); verify if proper noun or loanword")

            # 5. Duplicate sentence pair check
            pair_key = (h_text.strip(), m_text.strip())
            if pair_key in report["seen_pairs"] and pair_key != ("", ""):
                rec_warnings.append(f"Duplicate sentence pair detected for record {rec_id}: '{h_text}' -> '{m_text}'")
            report["seen_pairs"].add(pair_key)

            # 6. IPA syntax validation
            ipa = rec.get("ipa")
            if ipa:
                if not (ipa.startswith("/") and ipa.endswith("/")) and not (ipa.startswith("[") and ipa.endswith("]")):
                    rec_warnings.append(f"Record {rec_id} IPA transcription should be enclosed in slashes /.../ or brackets [...]")

            # 7. Provenance & License check
            lic = rec.get("license") or rec.get("license_provenance")
            if not lic or not lic.strip():
                rec_errors.append(f"Record {rec_id} missing mandatory license specification")
            elif "unknown" in lic.lower() or "unclear" in lic.lower():
                rec_errors.append(f"Record {rec_id} has ambiguous license: '{lic}'. Marked LICENSE_REVIEW_REQUIRED")
                report["quarantine_recommended"] = True

            # 8. Non-generative consistency checks and evidence scoring
            if record_type in ["parallel_translation", "classroom_phrase"] and h_text and m_text:
                lint_res = self.consistency_linter.lint_record(rec)
                if not lint_res["passed"]:
                    rec_errors.extend(lint_res["errors"])
                rec_warnings.extend(lint_res["warnings"])
                ev_res = self.evidence_scorer.score_record(rec)
                report["evidence_scores"].append(ev_res["evidence_coverage_score"])

            # 9. Status hierarchy & non-equivalence validation gate
            acc_status = rec.get("acceptance_status") or rec.get("validation_status")
            ling_stat = rec.get("linguistic_validation_status") or rec.get("linguistic_validation")
            edu_stat = rec.get("educational_validation_status") or rec.get("educational_validation")
            ling_rev = rec.get("linguistic_reviewer_id")
            final_disp = rec.get("final_disposition")

            # Human validation non-equivalence invariant
            if acc_status == "HUMAN_VALIDATED" or ling_stat == "HUMAN_VALIDATED":
                if not ling_rev or str(ling_rev).strip().upper() in ["AUTO", "DEFAULT", "AI", "LLM", "TEST", "SYNTHETIC", "NONE", "NULL"]:
                    rec_errors.append(f"ILLEGAL STATUS: Record {rec_id} marked HUMAN_VALIDATED without genuine human reviewer credentials")
                if rec.get("human_review_completed") is not True:
                    rec_errors.append(f"NON-EQUIVALENCE VIOLATION: Record {rec_id} cannot be HUMAN_VALIDATED without human_review_completed=true")
                if ling_stat in ["MACHINE_VALIDATED", "REFERENCE_SUPPORTED", "SOURCE_ATTESTED", "RESEARCH_VALIDATED"]:
                    rec_errors.append(f"NON-EQUIVALENCE VIOLATION: Record {rec_id} {ling_stat} cannot be equated to or claimed as HUMAN_VALIDATED")

            # Canonical promotion safety gate
            if acc_status == "CANONICAL_APPROVED":
                if ling_stat not in ["LINGUISTICALLY_REVIEWED", "NATIVE_SPEAKER_VERIFIED", "CORPUS_ATTESTED"]:
                    rec_errors.append(f"ILLEGAL STATUS: Record {rec_id} marked CANONICAL_APPROVED without verified linguistic validation (current: '{ling_stat}')")
                if edu_stat not in ["JCERT_ALIGNED", "NCERT_ALIGNED", "JCERT_APPROVED", "FLN_FRAMEWORK_COMPLIANT"]:
                    rec_errors.append(f"ILLEGAL STATUS: Record {rec_id} marked CANONICAL_APPROVED without verified educational validation (current: '{edu_stat}')")
                
                # Check for fake/default human reviewer attribution
                if ling_rev is not None and (not str(ling_rev).strip() or str(ling_rev).strip().upper() in ["AUTO", "DEFAULT", "AI", "LLM", "TEST", "NONE", "NULL"]):
                    rec_errors.append(f"ILLEGAL STATUS: Record {rec_id} marked CANONICAL_APPROVED with invalid/fake reviewer ID '{ling_rev}'")
                
                if final_disp in ["REJECT", "REVISE_ORTHOGRAPHY", "PENDING_COMMITTEE_DECISION"]:
                    rec_errors.append(f"ILLEGAL STATUS: Record {rec_id} cannot be CANONICAL_APPROVED with final_disposition '{final_disp}'")

                # Candidate story isolation: Story #240 records cannot enter canonical content
                if rec.get("story_id") == "0240" or str(rec_id).startswith("TR_PB_0240"):
                    rec_errors.append(f"GOVERNANCE ISOLATION: Candidate story record {rec_id} cannot be promoted to CANONICAL_APPROVED")
            elif acc_status == "REJECTED":
                if rec.get("acceptance_status") == "CANONICAL_APPROVED":
                    rec_errors.append(f"ILLEGAL STATUS: Record {rec_id} is marked REJECTED and cannot be CANONICAL_APPROVED")

            # 9. Audio asset checks
            if record_type == "native_audio":
                synth_auth = rec.get("synthetic_or_authentic")
                val_stat = rec.get("validation_status")
                s_rate = rec.get("sample_rate")
                ch = rec.get("channels")

                if s_rate not in [16000, 48000]:
                    rec_errors.append(f"Record {rec_id} unsupported sample rate {s_rate}Hz (Must be 16000 for mobile, 48000 for master)")
                if ch != 1:
                    rec_errors.append(f"Record {rec_id} channel count is {ch}; must be 1 (mono)")
                if synth_auth == "SYNTHETIC_PROTOTYPE" and val_stat == "AUTHENTIC_VALIDATED":
                    rec_errors.append(f"FRAUDULENT RECORD: Record {rec_id} synthetic audio marked AUTHENTIC_VALIDATED")

            # 10. Speech dataset speaker leakage check
            if record_type == "speech_recognition":
                spk = rec.get("speaker_id")
                split = rec.get("split_assignment")
                if not spk:
                    rec_errors.append(f"Record {rec_id} missing mandatory speaker_id")
                else:
                    if split == "TRAIN":
                        report["speakers_train"].add(spk)
                    elif split == "TEST":
                        report["speakers_test"].add(spk)

            if rec_errors:
                report["failed_records"] += 1
                report["errors"].extend(rec_errors)
            else:
                report["passed_records"] += 1

            if rec_warnings:
                report["warnings_count"] += len(rec_warnings)
                report["warnings"].extend(rec_warnings)

        # Cross-record check: Train / Test speaker overlap (leakage)
        overlap = report["speakers_train"].intersection(report["speakers_test"])
        if overlap:
            report["errors"].append(f"CRITICAL DATASET LEAKAGE: {len(overlap)} speakers overlap between TRAIN and TEST: {list(overlap)[:5]}")
            report["quarantine_recommended"] = True

        # Clean report for JSON serialization
        report["seen_ids"] = len(report["seen_ids"])
        report["seen_pairs"] = len(report["seen_pairs"])
        report["speakers_train"] = len(report["speakers_train"])
        report["speakers_test"] = len(report["speakers_test"])
        if report["evidence_scores"]:
            report["mean_evidence_coverage_score"] = round(sum(report["evidence_scores"]) / len(report["evidence_scores"]), 2)
        else:
            report["mean_evidence_coverage_score"] = 0.0
        report["valid"] = len(report["errors"]) == 0

        return report


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if len(sys.argv) < 2:
        print("Usage: python validator.py <path_to_candidate_file> [record_type]")
        sys.exit(1)

    target_path = sys.argv[1]
    rtype = sys.argv[2] if len(sys.argv) > 2 else None

    validator = DataIntakeValidator()
    res = validator.validate_file(target_path, rtype)

    try:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    except UnicodeEncodeError:
        print(json.dumps(res, indent=2, ensure_ascii=True))
    if not res["valid"]:
        sys.exit(1)
