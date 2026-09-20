"""
ai/ml_translation/quality_gate.py
=============================================================================
SIH260042: Neural Machine Translation Quality Gate & Linguistic Guardrails
=============================================================================
Inspects generated translations from the neural Seq2Seq model before they reach
the teacher UI or downstream pipeline. Rejects outputs exhibiting:
  1. Severe repetition (duplicate consecutive words, low lexical diversity)
  2. Empty or near-empty output (<2 chars, 0 words)
  3. Pathological punctuation (>35% punctuation, runs of punctuation)
  4. Excessive source copying (>70% verbatim Hindi word overlap on long queries)
  5. Degenerate token confidence (<0.03)

If the quality gate fails, the engine falls back to corpus retrieval or safe OOV,
preventing gibberish or hallucinated content from reaching classroom teachers.
=============================================================================
"""

import re
import string
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

from ai.translation.hindi_normalizer import normalize_hindi


@dataclass
class QualityGateResult:
    is_valid: bool
    rejection_reasons: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    ui_status: str = "AI TRANSLATION — REVIEW"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TranslationQualityGate:
    """
    Automated safety and linguistic consistency gate for neural translation.
    """

    def __init__(
        self,
        min_score: float = 0.12,
        max_source_copy_ratio: float = 0.70,
        min_unique_word_ratio: float = 0.60,
        max_punctuation_ratio: float = 0.35,
        max_consecutive_word_repeat: int = 1
    ):
        self.min_score = min_score
        self.max_source_copy_ratio = max_source_copy_ratio
        self.min_unique_word_ratio = min_unique_word_ratio
        self.max_punctuation_ratio = max_punctuation_ratio
        self.max_consecutive_word_repeat = max_consecutive_word_repeat

    def clean_text_for_analysis(self, text: str) -> str:
        """Removes punctuation and normalizes spacing for lexical analysis."""
        t = re.sub(r'[।,?!;:\-\.\(\)\"\'\[\]\/]', ' ', text)
        return re.sub(r'\s+', ' ', t).strip()

    def validate(
        self,
        translated_text: str,
        source_text: str,
        model_score: float = 1.0
    ) -> QualityGateResult:
        reasons: List[str] = []
        metrics: Dict[str, Any] = {}

        stripped = translated_text.strip()
        cleaned = self.clean_text_for_analysis(stripped)
        words = [w for w in cleaned.split() if w]
        char_count = len(stripped)

        metrics["char_count"] = char_count
        metrics["word_count"] = len(words)
        metrics["model_score"] = round(model_score, 4)

        # 1. Empty or near-empty check
        if char_count < 2 or len(words) == 0:
            reasons.append("EMPTY_OR_NEAR_EMPTY")
            return QualityGateResult(is_valid=False, rejection_reasons=reasons, metrics=metrics)

        # 2. Devanagari script presence check (if source contains Devanagari)
        src_has_devanagari = bool(re.search(r'[\u0900-\u097F]', source_text))
        tgt_has_devanagari = bool(re.search(r'[\u0900-\u097F]', stripped))
        if src_has_devanagari and not tgt_has_devanagari:
            reasons.append("MISSING_DEVANAGARI_SCRIPT")

        # 3. Pathological punctuation checks
        punct_chars = re.findall(r'[।,?!;:\-\.\(\)\"\'\[\]\/]', stripped)
        punct_ratio = len(punct_chars) / max(1, char_count)
        metrics["punct_ratio"] = round(punct_ratio, 3)

        if punct_ratio > self.max_punctuation_ratio:
            reasons.append("EXCESSIVE_PUNCTUATION_RATIO")

        # Repeated punctuation marks (e.g., '।।।', '...', ':::')
        if re.search(r'([।,?!;:\-\.\(\)\"\'\[\]\/])\s*\1{2,}', stripped):
            reasons.append("PATHOLOGICAL_PUNCTUATION_RUN")

        # 4. Severe repetition checks
        # 4a. Consecutive duplicate words (e.g. 'होड़ोको होड़ोको' or 'मेनाः मेनाः')
        consecutive_repeats = 0
        for i in range(len(words) - 1):
            if words[i] == words[i + 1]:
                consecutive_repeats += 1
        metrics["consecutive_word_repeats"] = consecutive_repeats
        if consecutive_repeats > self.max_consecutive_word_repeat:
            reasons.append("CONSECUTIVE_WORD_REPETITION")

        # 4b. Low lexical diversity (vocabulary collapse)
        if len(words) >= 4:
            unique_ratio = len(set(words)) / len(words)
            metrics["unique_word_ratio"] = round(unique_ratio, 3)
            if unique_ratio < self.min_unique_word_ratio:
                reasons.append("LOW_LEXICAL_DIVERSITY")

        # 4c. Runaway character repetition (e.g. 'कककक')
        if re.search(r'(\S)\1{3,}', stripped):
            reasons.append("RUNAWAY_CHARACTER_REPETITION")

        # 5. Excessive source copying (model failing to translate and merely echoing Hindi)
        src_clean = self.clean_text_for_analysis(source_text)
        src_words = set(src_clean.split())
        if stripped == source_text.strip() and len(words) >= 1:
            reasons.append("EXCESSIVE_SOURCE_COPYING")
            metrics["source_overlap_ratio"] = 1.0
        elif len(src_words) >= 2 and len(words) >= 2:
            overlap = set(words).intersection(src_words)
            overlap_ratio = len(overlap) / max(1, min(len(words), len(src_words)))
            metrics["source_overlap_ratio"] = round(overlap_ratio, 3)
            if overlap_ratio >= self.max_source_copy_ratio:
                reasons.append("EXCESSIVE_SOURCE_COPYING")

        # 6. Degenerate or low token confidence check
        if model_score < self.min_score:
            reasons.append("LOW_GENERATION_CONFIDENCE")
            if model_score < 0.05:
                reasons.append("DEGENERATE_MODEL_SCORE")

        is_valid = (len(reasons) == 0)
        ui_status = self.classify_ui_status(is_tier1_verified=False, quality_gate_passed=is_valid, has_text=(char_count >= 2))

        return QualityGateResult(
            is_valid=is_valid,
            rejection_reasons=reasons,
            metrics=metrics,
            ui_status=ui_status
        )

    @staticmethod
    def classify_ui_status(is_tier1_verified: bool = False, quality_gate_passed: bool = True, has_text: bool = True) -> str:
        """
        Classifies UI translation status per educational safety requirements:
        - VERIFIED EDUCATIONAL: deterministic verified registry
        - AI TRANSLATION — REVIEW: neural model output that passed safety gate
        - TRANSLATION UNAVAILABLE: low confidence or failed safety checks
        """
        if is_tier1_verified:
            return "VERIFIED EDUCATIONAL"
        elif quality_gate_passed and has_text:
            return "AI TRANSLATION — REVIEW"
        else:
            return "TRANSLATION UNAVAILABLE"
