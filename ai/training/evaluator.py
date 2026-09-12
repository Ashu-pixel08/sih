"""
ai/training/evaluator.py
=============================================================================
SIH260042: AI-Powered Vernacular Pedagogy & Real-Time Translation
Comprehensive Evaluation, Confusion Matrix & Confidence Analysis Module
=============================================================================

POLICY & COMPLIANCE:
- Generates 21x21 confusion matrix, precision, recall, F1, and confidence calibration.
- Enforces strict anti-fabrication: If real numeral test support is missing,
  reports "MISSING — SUFFICIENT LABELED 1–20 SPEECH DATA" rather than fake accuracy.
=============================================================================
"""

import json
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
from torch.utils.data import DataLoader


class SpeechModelEvaluator:
    """
    Evaluates 21-class spoken numeral classifier on a test dataset.
    Computes confusion matrix, per-class metrics, confidence analysis,
    and enforces data sufficiency policy checks.
    """

    def __init__(
        self,
        class_names: Optional[List[str]] = None,
        confidence_threshold: float = 0.65,
        margin_threshold: float = 0.20,
    ):
        self.class_names = class_names or (
            ["_background_"] + [f"num_{i:02d}" for i in range(1, 21)]
        )
        self.num_classes = len(self.class_names)
        self.confidence_threshold = confidence_threshold
        self.margin_threshold = margin_threshold

    @torch.no_grad()
    def evaluate(
        self,
        model: nn.Module,
        data_loader: DataLoader,
        dataset_category: str = "REAL",
    ) -> Dict[str, Any]:
        """
        Runs full evaluation over DataLoader.
        Returns complete metrics dictionary.
        """
        model.eval()
        device = next(model.parameters()).device

        all_preds: List[int] = []
        all_targets: List[int] = []
        all_confs: List[float] = []
        all_margins: List[float] = []
        all_probs: List[np.ndarray] = []

        for batch_x, batch_y, _ in data_loader:
            batch_x = batch_x.to(device)
            # Forward pass: get probabilities
            if hasattr(model, "forward"):
                probs = model(batch_x, return_probabilities=True)
            else:
                logits = model(batch_x)
                probs = torch.softmax(logits, dim=-1)

            probs_np = probs.cpu().numpy()
            for p, target in zip(probs_np, batch_y.numpy()):
                sorted_idx = np.argsort(p)[::-1]
                top_class = int(sorted_idx[0])
                top_conf = float(p[top_class])
                sec_conf = float(p[sorted_idx[1]]) if len(sorted_idx) > 1 else 0.0
                margin = float(top_conf - sec_conf)

                all_preds.append(top_class)
                all_targets.append(int(target))
                all_confs.append(top_conf)
                all_margins.append(margin)
                all_probs.append(p)

        y_true = np.array(all_targets)
        y_pred = np.array(all_preds)
        confs = np.array(all_confs)
        margins = np.array(all_margins)

        total_samples = len(y_true)
        if total_samples == 0:
            return {
                "status": "EMPTY_TEST_SET",
                "message": "No test samples provided for evaluation.",
                "total_samples": 0,
            }

        # Check real data support for numerals 1-20
        numeral_targets = [y for y in y_true if y > 0]
        numeral_support_count = len(numeral_targets)

        if dataset_category != "SYNTHETIC_PIPELINE_VALIDATION" and numeral_support_count < 20:
            sufficiency_status = "MISSING — SUFFICIENT LABELED 1–20 SPEECH DATA"
            claim_permitted = False
        elif dataset_category == "SYNTHETIC_PIPELINE_VALIDATION":
            sufficiency_status = "SYNTHETIC / PIPELINE VALIDATION ONLY"
            claim_permitted = False
        else:
            sufficiency_status = "EVALUATION_COMPLETE"
            claim_permitted = True

        # Confusion Matrix (21x21)
        cm = confusion_matrix(
            y_true,
            y_pred,
            labels=list(range(self.num_classes)),
        )

        # Per-class Precision, Recall, F1, Support
        p_class, r_class, f1_class, s_class = precision_recall_fscore_support(
            y_true,
            y_pred,
            labels=list(range(self.num_classes)),
            zero_division=0,
        )

        per_class_metrics = {}
        for i in range(self.num_classes):
            name = self.class_names[i]
            per_class_metrics[f"{i:02d}_{name}"] = {
                "precision": round(float(p_class[i]), 4),
                "recall": round(float(r_class[i]), 4),
                "f1_score": round(float(f1_class[i]), 4),
                "support": int(s_class[i]),
            }

        # Global accuracy and macro metrics
        correct_mask = y_true == y_pred
        overall_accuracy = float(np.mean(correct_mask)) if total_samples > 0 else 0.0

        # Confidence Analysis
        correct_confs = confs[correct_mask] if np.any(correct_mask) else np.array([])
        incorrect_confs = confs[~correct_mask] if np.any(~correct_mask) else np.array([])

        avg_conf_correct = float(np.mean(correct_confs)) if len(correct_confs) > 0 else 0.0
        avg_conf_incorrect = float(np.mean(incorrect_confs)) if len(incorrect_confs) > 0 else 0.0

        # Rejection Analysis at Confidence Threshold (0.65) and Margin (0.20)
        rejected_mask = (confs < self.confidence_threshold) | (margins < self.margin_threshold) | (y_pred == 0)
        rejection_rate = float(np.mean(rejected_mask))

        # High-confidence errors: predicted != target, but confidence >= 0.65
        hi_conf_errors = (~correct_mask) & (confs >= self.confidence_threshold) & (y_pred != 0)
        hi_conf_error_rate = float(np.mean(hi_conf_errors))

        return {
            "evaluation_status": sufficiency_status,
            "production_accuracy_claim_permitted": claim_permitted,
            "dataset_category": dataset_category,
            "total_test_samples": total_samples,
            "numeral_samples_evaluated": numeral_support_count,
            "overall_accuracy": round(overall_accuracy, 4),
            "macro_f1": round(float(np.mean(f1_class)), 4),
            "confidence_analysis": {
                "average_confidence_correct": round(avg_conf_correct, 4),
                "average_confidence_incorrect": round(avg_conf_incorrect, 4),
                "rejection_rate_at_threshold": round(rejection_rate, 4),
                "high_confidence_error_rate": round(hi_conf_error_rate, 4),
                "confidence_threshold": self.confidence_threshold,
                "margin_threshold": self.margin_threshold,
            },
            "per_class_metrics": per_class_metrics,
            "confusion_matrix_shape": list(cm.shape),
            "confusion_matrix": cm.tolist(),
        }

    def format_markdown_report(self, report: Dict[str, Any]) -> str:
        """Formats evaluation summary in readable Markdown."""
        lines = [
            "# Speech Classifier Evaluation Report",
            f"**Status**: `{report.get('evaluation_status')}`",
            f"**Production Claim Permitted**: `{report.get('production_accuracy_claim_permitted')}`",
            f"**Dataset Category**: `{report.get('dataset_category')}`",
            f"**Total Samples**: {report.get('total_test_samples')}",
            f"**Overall Accuracy**: {report.get('overall_accuracy')}",
            f"**Macro F1**: {report.get('macro_f1')}",
            "",
            "## Confidence & Edge Rejection Analysis",
            f"- Avg Confidence (Correct): {report.get('confidence_analysis', {}).get('average_confidence_correct')}",
            f"- Avg Confidence (Incorrect): {report.get('confidence_analysis', {}).get('average_confidence_incorrect')}",
            f"- Rejection Rate (< 0.65 threshold / background): {report.get('confidence_analysis', {}).get('rejection_rate_at_threshold')}",
            f"- High-Confidence Error Rate: {report.get('confidence_analysis', {}).get('high_confidence_error_rate')}",
            "",
            "## Data Limitation Notice",
            "> " + (
                "Real isolated 1-20 speech recordings are currently missing. "
                "Accuracy figures reflect pipeline mechanics or synthetic validation only."
                if not report.get("production_accuracy_claim_permitted")
                else "Evaluated on verified test data."
            ),
        ]
        return "\n".join(lines)
