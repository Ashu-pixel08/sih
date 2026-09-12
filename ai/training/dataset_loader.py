"""
ai/training/dataset_loader.py
=============================================================================
SIH260042: AI-Powered Vernacular Pedagogy & Real-Time Translation
Dataset Loader, Class Mapping & Speaker-Aware Splitter
=============================================================================

DATA REALITY & LIMITATION:
- Current available sample contains 182 valid multi-word recordings.
- Zero isolated 1-20 recordings are present in the sample.
- Many numeral classes (15 of 20) have zero acoustic representation.
- This loader is structured to load real audio when supplied, while honestly
  documenting and reporting missing classes without fabricating labels.
=============================================================================
"""

import json
import os
import random
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import torch
from torch.utils.data import Dataset

cur_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.normpath(os.path.join(cur_dir, "..", ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from ai.preprocessing.audio_preprocessor import AudioPreprocessor
from ai.training.augmentation import SpectrogramAugmentation


@dataclass
class AudioSampleMeta:
    sample_id: str
    file_path: Optional[str]
    spectrogram: Optional[np.ndarray]  # [101, 64]
    label_idx: int  # 0 to 20
    label_id: str
    speaker_id: str
    duration_sec: float
    category: str  # "REAL_VERIFIED", "REAL_BACKGROUND", "SYNTHETIC_PIPELINE_VALIDATION"


class MundariSpeechDataset(Dataset):
    """
    PyTorch Dataset for spoken numeral audio spectrograms.
    Integrates class mapping, preprocessing, and training-only data augmentation.
    """

    def __init__(
        self,
        samples: List[AudioSampleMeta],
        augmentation: Optional[SpectrogramAugmentation] = None,
        is_training: bool = False,
    ):
        self.samples = samples
        self.augmentation = augmentation
        self.is_training = is_training

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int, str]:
        sample = self.samples[idx]
        spec_np = sample.spectrogram

        # Lazy load/preprocess if file_path is provided and spectrogram is None
        if spec_np is None and sample.file_path and os.path.exists(sample.file_path):
            preprocessor = AudioPreprocessor()
            spec_np = preprocessor.process_file_to_tensor(sample.file_path).squeeze(0).squeeze(-1)

        if spec_np is None:
            spec_np = np.zeros((101, 64), dtype=np.float32)

        # Convert to tensor: shape [1, 101, 64] (NCHW single-channel)
        spec_tensor = torch.from_numpy(spec_np).float()
        if spec_tensor.dim() == 2:
            spec_tensor = spec_tensor.unsqueeze(0)

        # Apply augmentation strictly only if is_training is True
        if self.augmentation is not None:
            spec_tensor = self.augmentation(spec_tensor, is_training=self.is_training)

        return spec_tensor, sample.label_idx, sample.sample_id


class DatasetManager:
    """
    Manages loading, audit, and speaker-aware train/val/test splitting.
    """

    def __init__(self, registry_path: Optional[str] = None):
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        self.workspace_root = os.path.normpath(os.path.join(cur_dir, "..", ".."))
        self.registry_path = registry_path or os.path.join(
            self.workspace_root, "content", "content_registry.json"
        )
        self.class_map = self._load_class_mapping()

    def _load_class_mapping(self) -> Dict[int, Dict[str, Any]]:
        """Loads canonical 21-class mapping from content_registry.json."""
        mapping = {}
        if os.path.exists(self.registry_path):
            with open(self.registry_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            bg = data.get("background_class", {})
            mapping[0] = {
                "class_index": 0,
                "label_id": bg.get("label_id", "_background_"),
                "text": bg.get("mundari_text", "मौन / एटाः"),
                "category": "background",
            }
            for item in data.get("items", []):
                idx = item["class_index"]
                mapping[idx] = {
                    "class_index": idx,
                    "label_id": item["label_id"],
                    "text": item.get("mundari_text", f"num_{idx}"),
                    "category": "numeral",
                }
        else:
            mapping[0] = {"class_index": 0, "label_id": "_background_", "text": "मौन", "category": "background"}
            for i in range(1, 21):
                mapping[i] = {"class_index": i, "label_id": f"num_{i:02d}", "text": f"num_{i:02d}", "category": "numeral"}
        return mapping

    def audit_coverage(self, samples: List[AudioSampleMeta]) -> Dict[str, Any]:
        """
        Audits sample counts per class and checks data sufficiency.
        Flags missing numeral classes with 0 samples.
        """
        counts = {i: 0 for i in range(21)}
        speaker_counts: Dict[str, int] = {}
        categories: Dict[str, int] = {}

        for s in samples:
            if 0 <= s.label_idx <= 20:
                counts[s.label_idx] += 1
            speaker_counts[s.speaker_id] = speaker_counts.get(s.speaker_id, 0) + 1
            categories[s.category] = categories.get(s.category, 0) + 1

        missing_classes = [i for i, c in counts.items() if c == 0]
        real_numeral_samples = sum(
            1 for s in samples if s.category == "REAL_VERIFIED" and s.label_idx > 0
        )

        sufficiency_status = (
            "SUFFICIENT"
            if real_numeral_samples >= 400 and len(missing_classes) == 0
            else "MISSING — SUFFICIENT LABELED 1–20 SPEECH DATA"
        )

        return {
            "total_samples": len(samples),
            "class_distribution": {
                f"class_{i:02d} ({self.class_map[i]['label_id']})": counts[i]
                for i in range(21)
            },
            "missing_class_indices": missing_classes,
            "missing_class_count": len(missing_classes),
            "speaker_distribution": speaker_counts,
            "category_distribution": categories,
            "sufficiency_status": sufficiency_status,
            "policy_note": (
                "ZERO isolated 1-20 speech recordings exist in the public sample. "
                "Production accuracy claims on 1-20 are strictly prohibited until real audio is supplied."
            ),
        }

    def split_speaker_aware(
        self,
        samples: List[AudioSampleMeta],
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        seed: int = 42,
    ) -> Tuple[List[AudioSampleMeta], List[AudioSampleMeta], List[AudioSampleMeta]]:
        """
        Partitions samples into train, val, and test splits by speaker ID
        to prevent acoustic data leakage across splits.
        """
        rng = random.Random(seed)

        # Group samples by speaker
        speakers = sorted(list(set(s.speaker_id for s in samples)))
        rng.shuffle(speakers)

        train_samples: List[AudioSampleMeta] = []
        val_samples: List[AudioSampleMeta] = []
        test_samples: List[AudioSampleMeta] = []

        if len(speakers) >= 3:
            # Partition speakers directly
            n_train = max(1, int(len(speakers) * train_ratio))
            n_val = max(1, int(len(speakers) * val_ratio))
            train_spks = set(speakers[:n_train])
            val_spks = set(speakers[n_train : n_train + n_val])
            test_spks = set(speakers[n_train + n_val :])

            for s in samples:
                if s.speaker_id in train_spks:
                    train_samples.append(s)
                elif s.speaker_id in val_spks:
                    val_samples.append(s)
                else:
                    test_samples.append(s)
        else:
            # Fallback: Stratified by class and sample if speaker count < 3
            class_groups: Dict[int, List[AudioSampleMeta]] = {}
            for s in samples:
                class_groups.setdefault(s.label_idx, []).append(s)

            for cls_idx, group in class_groups.items():
                rng.shuffle(group)
                n_total = len(group)
                n_tr = max(1, int(n_total * train_ratio)) if n_total >= 3 else n_total
                n_v = max(1, int(n_total * val_ratio)) if n_total - n_tr >= 2 else 0
                train_samples.extend(group[:n_tr])
                val_samples.extend(group[n_tr : n_tr + n_v])
                test_samples.extend(group[n_tr + n_v :])

        return train_samples, val_samples, test_samples
