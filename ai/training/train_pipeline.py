"""
ai/training/train_pipeline.py
=============================================================================
SIH260042: AI-Powered Vernacular Pedagogy & Real-Time Translation
End-to-End Training Loop, Checkpointing & Evaluation Pipeline
=============================================================================

EXECUTION MODES:
1. --mode synthetic:
   Executes pipeline validation using the synthetic simulation harness.
   Validates convergence, backpropagation, checkpointing, and evaluation.
   LABEL: SYNTHETIC / PIPELINE VALIDATION ONLY.

2. --mode real:
   Scans available real Mundari speech recordings.
   If real 1-20 numeral samples are insufficient (current reality: 0 isolated samples),
   it produces an honest audit report and refuses to fabricate labels.
=============================================================================
"""

import argparse
import json
import os
import random
import sys
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

cur_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.normpath(os.path.join(cur_dir, "..", ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from ai.speech.speech_classifier import LightweightSpectrogramCNN
from ai.training.augmentation import SpectrogramAugmentation
from ai.training.dataset_loader import (
    AudioSampleMeta,
    DatasetManager,
    MundariSpeechDataset,
)
from ai.training.evaluator import SpeechModelEvaluator
from ai.training.synthetic_simulation_harness import SyntheticSimulationHarness


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class TrainingPipeline:
    def __init__(self, config_path: Optional[str] = None):
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        self.workspace_root = os.path.normpath(os.path.join(cur_dir, "..", ".."))

        if config_path is None:
            config_path = os.path.join(cur_dir, "train_config.json")

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.checkpoint_dir = os.path.join(
            self.workspace_root, self.config["paths"]["checkpoint_dir"]
        )
        os.makedirs(self.checkpoint_dir, exist_ok=True)

        set_seed(self.config["training"]["random_seed"])

    def train_epoch(
        self,
        model: nn.Module,
        loader: DataLoader,
        optimizer: torch.optim.Optimizer,
        criterion: nn.Module,
        device: torch.device,
    ) -> float:
        model.train()
        total_loss = 0.0
        n_batches = 0

        for batch_x, batch_y, _ in loader:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)

            optimizer.zero_grad()
            # Request logits for loss computation
            logits = model(batch_x, return_probabilities=False)
            loss = criterion(logits, batch_y)
            loss.backward()

            # Gradient clipping
            clip_val = self.config["training"]["gradient_clip_norm"]
            nn.utils.clip_grad_norm_(model.parameters(), clip_val)

            optimizer.step()
            total_loss += loss.item()
            n_batches += 1

        return total_loss / max(1, n_batches)

    @torch.no_grad()
    def validate(
        self,
        model: nn.Module,
        loader: DataLoader,
        criterion: nn.Module,
        device: torch.device,
    ) -> float:
        model.eval()
        total_loss = 0.0
        n_batches = 0

        for batch_x, batch_y, _ in loader:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)
            logits = model(batch_x, return_probabilities=False)
            loss = criterion(logits, batch_y)
            total_loss += loss.item()
            n_batches += 1

        return total_loss / max(1, n_batches)

    def run_synthetic_pipeline(self) -> Dict[str, Any]:
        """
        Executes complete training and evaluation pipeline on synthetic data.
        Validates pipeline mechanics, convergence, and checkpoints.
        """
        print("\n=======================================================")
        print("RUNNING TRAINING PIPELINE (SYNTHETIC / VALIDATION ONLY)")
        print("=======================================================")

        harness = SyntheticSimulationHarness(
            num_classes=self.config["model"]["num_classes"],
            seed=self.config["training"]["random_seed"],
        )
        samples = harness.generate_dataset(samples_per_class=12, num_mock_speakers=4)
        print(f"Generated {len(samples)} synthetic spectrogram samples across 21 classes.")

        dataset_mgr = DatasetManager()
        audit = dataset_mgr.audit_coverage(samples)
        print(f"Audit Status: {audit['sufficiency_status']}")

        train_s, val_s, test_s = dataset_mgr.split_speaker_aware(samples, seed=42)
        print(f"Splits -> Train: {len(train_s)}, Val: {len(val_s)}, Test: {len(test_s)}")

        # Training augmentation (STRICTLY for train split)
        aug_cfg = self.config["augmentation"]
        train_aug = SpectrogramAugmentation(
            time_mask_max=aug_cfg["time_mask_max_frames"],
            freq_mask_max=aug_cfg["freq_mask_max_bins"],
            p=aug_cfg["apply_probability"],
            seed=42,
        )

        train_ds = MundariSpeechDataset(train_s, augmentation=train_aug, is_training=True)
        val_ds = MundariSpeechDataset(val_s, augmentation=None, is_training=False)
        test_ds = MundariSpeechDataset(test_s, augmentation=None, is_training=False)

        batch_size = self.config["training"]["batch_size"]
        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)
        test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)

        device = torch.device("cpu")
        model = LightweightSpectrogramCNN(
            num_classes=self.config["model"]["num_classes"],
            dropout_rate=self.config["model"]["dropout_rate"],
        ).to(device)

        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=self.config["training"]["learning_rate"],
            weight_decay=self.config["training"]["weight_decay"],
        )
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=self.config["training"]["max_epochs"]
        )

        best_val_loss = float("inf")
        best_checkpoint_path = os.path.join(self.checkpoint_dir, "best_model.pt")

        epochs = min(10, self.config["training"]["max_epochs"])  # fast validation run
        print(f"\nTraining for {epochs} epochs...")

        history = []
        for epoch in range(1, epochs + 1):
            train_loss = self.train_epoch(model, train_loader, optimizer, criterion, device)
            val_loss = self.validate(model, val_loader, criterion, device)
            scheduler.step()

            history.append({"epoch": epoch, "train_loss": round(train_loss, 4), "val_loss": round(val_loss, 4)})

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                torch.save(
                    {
                        "epoch": epoch,
                        "model_state_dict": model.state_dict(),
                        "optimizer_state_dict": optimizer.state_dict(),
                        "val_loss": val_loss,
                        "config": self.config,
                        "pipeline_label": "SYNTHETIC / PIPELINE VALIDATION ONLY",
                    },
                    best_checkpoint_path,
                )

            if epoch % 2 == 0 or epoch == epochs:
                print(f"Epoch {epoch:02d}/{epochs:02d} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f}")

        print(f"\nBest model checkpoint saved to: {best_checkpoint_path}")

        # Load best weights for test evaluation
        checkpoint = torch.load(best_checkpoint_path, weights_only=False)
        model.load_state_dict(checkpoint["model_state_dict"])

        evaluator = SpeechModelEvaluator(
            confidence_threshold=self.config["thresholds"]["confidence_threshold"],
            margin_threshold=self.config["thresholds"]["margin_threshold"],
        )
        eval_results = evaluator.evaluate(
            model=model,
            data_loader=test_loader,
            dataset_category="SYNTHETIC_PIPELINE_VALIDATION",
        )

        eval_report_path = os.path.join(self.checkpoint_dir, "synthetic_eval_report.json")
        with open(eval_report_path, "w", encoding="utf-8") as f:
            json.dump(eval_results, f, indent=2)

        print(f"Evaluation report saved to: {eval_report_path}")
        print(f"Accuracy (Synthetic Mechanics): {eval_results['overall_accuracy']}")
        print(f"Rejection Rate (<0.65 conf): {eval_results['confidence_analysis']['rejection_rate_at_threshold']}")
        print("Status: SYNTHETIC / PIPELINE VALIDATION ONLY — Success!")

        return {
            "status": "SUCCESS",
            "mode": "SYNTHETIC / PIPELINE VALIDATION ONLY",
            "checkpoint_path": best_checkpoint_path,
            "eval_report_path": eval_report_path,
            "metrics": eval_results,
            "training_history": history,
        }

    def run_real_corpus_audit(self) -> Dict[str, Any]:
        """
        Audits real speech corpus for training readiness.
        Enforces policy: If isolated 1-20 recordings are missing,
        reports MISSING without fabricating labels.
        """
        print("\n=======================================================")
        print("AUDITING REAL MUNDARI SPEECH CORPUS FOR TRAINING")
        print("=======================================================")

        manifest_path = os.path.join(self.workspace_root, self.config["paths"]["raw_manifest"])
        if not os.path.exists(manifest_path):
            return {
                "status": "MISSING_MANIFEST",
                "message": f"Manifest not found at {manifest_path}",
            }

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        valid_items = [r for r in manifest.get("results", []) if r.get("is_valid", False)]
        print(f"Total valid speech files in corpus: {len(valid_items)}")

        # Construct background/ambient training samples from valid files
        speech_samples: List[AudioSampleMeta] = []
        for item in valid_items:
            fpath = item.get("file_path")
            spk = "female" if "female" in str(fpath).lower() else "male"
            meta = AudioSampleMeta(
                sample_id=item["file_name"],
                file_path=fpath,
                spectrogram=None,
                label_idx=0,  # Background/speech sentence
                label_id="_background_",
                speaker_id=spk,
                duration_sec=item.get("duration_seconds", 3.0),
                category="REAL_BACKGROUND",
            )
            speech_samples.append(meta)

        dataset_mgr = DatasetManager()
        audit = dataset_mgr.audit_coverage(speech_samples)

        print("\nReal Corpus Audit Result:")
        print(f"- Total Real Audio Samples: {audit['total_samples']}")
        print(f"- Missing Numeral Classes Count: {audit['missing_class_count']}/20")
        print(f"- Sufficiency Status: {audit['sufficiency_status']}")

        audit_report_path = os.path.join(self.checkpoint_dir, "real_data_training_audit.json")
        with open(audit_report_path, "w", encoding="utf-8") as f:
            json.dump(audit, f, indent=2)

        print(f"\nAudit saved to: {audit_report_path}")
        return audit


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Speech Classifier Training Pipeline")
    parser.add_argument(
        "--mode",
        choices=["synthetic", "real"],
        default="synthetic",
        help="Execution mode: synthetic (pipeline validation) or real (corpus audit)",
    )
    args = parser.parse_args()

    pipeline = TrainingPipeline()
    if args.mode == "synthetic":
        pipeline.run_synthetic_pipeline()
    else:
        pipeline.run_real_corpus_audit()
