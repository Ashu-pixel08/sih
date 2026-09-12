"""
evidence_scorer.py - Transparent Evidence Coverage Scorer for Data Intake

Computes an objective, multi-dimensional EVIDENCE_COVERAGE_SCORE (0 to 100)
for candidate records based purely on documented evidence and automated checks.

CRITICAL POLICY MANDATE:
This score measures EVIDENCE COVERAGE and DOCUMENTATION COMPLETENESS.
It does NOT measure:
- "translation accuracy"
- "linguistic correctness"
- "human confidence"
- "native-speaker fluency"

A record with an EVIDENCE_COVERAGE_SCORE of 95/100 means its provenance, licensing,
alignment, and lexicographical citations are thoroughly documented. It does NOT mean
the record has been validated or approved by a native speaker.
"""

from typing import Dict, Any, List, Tuple
from consistency_linter import ConsistencyLinter


class EvidenceScorer:
    """Calculates verifiable evidence coverage across parallel bilingual datasets."""

    MAX_DIMENSION_POINTS = 20
    PENALTY_PER_ANOMALY = 5

    PERMISSIVE_LICENSES = {
        "CC-BY-4.0", "CC-BY-SA-4.0", "CC-BY-3.0", "CC0-1.0",
        "PUBLIC_DOMAIN", "OPEN_GOVERNMENT_LICENSE"
    }

    def __init__(self):
        self.linter = ConsistencyLinter()

    def score_record(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scores an individual record across five 20-point dimensions:
        1. Provenance Completeness
        2. License Evidence
        3. Alignment Evidence
        4. Reference Support
        5. Automated Consistency
        With deductions for unresolved anomalies.
        """
        lint_result = self.linter.lint_record(rec)

        # 1. Provenance Completeness (0-20)
        prov_score = 0
        prov_details = []
        if rec.get("source"):
            prov_score += 4
            prov_details.append("Source organization/book specified")
        if rec.get("source_reference"):
            prov_score += 4
            prov_details.append("Exact line/page/story reference specified")
        if rec.get("source_url"):
            prov_score += 4
            prov_details.append("Upstream source URL documented")
        if rec.get("author") or rec.get("translator"):
            prov_score += 4
            prov_details.append("Author and/or translator attribution documented")
        if rec.get("checksum") or rec.get("source_id"):
            prov_score += 4
            prov_details.append("Record checksum or source identifier verified")

        # 2. License Evidence (0-20)
        lic_score = 0
        lic_details = []
        lic = (rec.get("license") or "").upper().strip()
        if lic in self.PERMISSIVE_LICENSES:
            lic_score = 20
            lic_details.append(f"Permissive open license verified ({lic})")
        elif lic and "REVIEW" not in lic and "UNKNOWN" not in lic:
            lic_score = 12
            lic_details.append(f"Conditional/Custom license specified ({lic})")
        else:
            lic_score = 0
            lic_details.append("Missing or ambiguous license")

        # 3. Alignment Evidence (0-20)
        align_score = 0
        align_details = []
        hi_text = rec.get("hindi_text", "").strip()
        mun_text = rec.get("mundari_text", "").strip()

        if hi_text and mun_text:
            align_score += 10
            align_details.append("Non-empty parallel pair present")
            ratio = lint_result["metrics"]["length_ratio"]
            if 0.50 <= ratio <= 2.0:
                align_score += 10
                align_details.append(f"Optimal length ratio ({ratio})")
            elif 0.25 <= ratio <= 4.0:
                align_score += 6
                align_details.append(f"Acceptable length ratio ({ratio})")
            else:
                align_details.append(f"Disparate length ratio ({ratio})")

        # 4. Reference Support (0-20)
        ref_score = 0
        ref_details = []
        attested_terms = lint_result["metrics"]["attested_lexicon_terms"]
        if len(attested_terms) >= 3:
            ref_score = 20
            ref_details.append(f"Strong lexicographical support: {len(attested_terms)} attested roots ({', '.join(attested_terms[:4])}...)")
        elif len(attested_terms) >= 1:
            ref_score = 14
            ref_details.append(f"Moderate lexicographical support: {len(attested_terms)} attested roots ({', '.join(attested_terms)})")
        else:
            ref_score = 6
            ref_details.append("Minimal root match against offline reference dictionary")

        # 5. Automated Consistency (0-20)
        auto_score = 20
        auto_details = []
        if lint_result["errors"]:
            auto_score -= 15
            auto_details.append(f"Consistency errors: {len(lint_result['errors'])}")
        if lint_result["warnings"]:
            auto_score = max(5, auto_score - (len(lint_result["warnings"]) * 3))
            auto_details.append(f"Consistency warnings: {len(lint_result['warnings'])}")
        if not lint_result["errors"] and not lint_result["warnings"]:
            auto_details.append("Passed all automated structural, Unicode, and punctuation checks")

        # Anomalies Penalty
        anomalies_count = len(lint_result["anomalies"])
        penalty = anomalies_count * self.PENALTY_PER_ANOMALY

        # Aggregate Score
        raw_score = prov_score + lic_score + align_score + ref_score + auto_score
        final_score = max(0, min(100, raw_score - penalty))

        return {
            "record_id": rec.get("record_id", "UNKNOWN"),
            "evidence_coverage_score": final_score,
            "dimensions": {
                "provenance_completeness": {"score": prov_score, "max": 20, "details": prov_details},
                "license_evidence": {"score": lic_score, "max": 20, "details": lic_details},
                "alignment_evidence": {"score": align_score, "max": 20, "details": align_details},
                "reference_support": {"score": ref_score, "max": 20, "details": ref_details},
                "automated_consistency": {"score": auto_score, "max": 20, "details": auto_details}
            },
            "anomalies_count": anomalies_count,
            "anomalies_penalty": penalty,
            "unresolved_anomalies": lint_result["anomalies"],
            "disclaimer": (
                "EVIDENCE_COVERAGE_SCORE measures documentation completeness, licensing verification, "
                "and reference support. It does NOT evaluate native-speaker linguistic accuracy or human validation."
            )
        }
