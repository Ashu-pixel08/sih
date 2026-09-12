"""
ai/training/synthetic_simulation_harness.py
=============================================================================
SIH260042: AI-Powered Vernacular Pedagogy & Real-Time Translation
Synthetic Pipeline Validation & Simulation Harness
=============================================================================

CRITICAL POLICY & COMPLIANCE MANDATE:
------------------------------------
LABEL: SYNTHETIC / PIPELINE VALIDATION ONLY.

This simulation harness is designed EXCLUSIVELY for:
1. Validating training loop convergence and gradient updates.
2. Validating tensor shapes [1, 101, 64, 1] and [1, 21].
3. Validating speaker-aware splitting mechanics.
4. Validating TFLite export and FP32/INT8 parity checks.

This synthetic data MUST NOT be presented as real Mundari speech data,
and MUST NEVER be used to make claims about actual linguistic recognition accuracy.
=============================================================================
"""

from typing import List, Optional

import numpy as np

from ai.training.dataset_loader import AudioSampleMeta


class SyntheticSimulationHarness:
    """
    Generates synthetic spectrogram samples with known harmonic patterns
    for end-to-end training and export pipeline validation.
    """

    HARNESS_LABEL = "SYNTHETIC / PIPELINE VALIDATION ONLY"

    def __init__(
        self,
        num_classes: int = 21,
        time_steps: int = 101,
        mel_bins: int = 64,
        seed: int = 42,
    ):
        self.num_classes = num_classes
        self.time_steps = time_steps
        self.mel_bins = mel_bins
        self.seed = seed

    def generate_synthetic_spectrogram(
        self,
        class_idx: int,
        rng: np.random.RandomState,
        noise_floor: float = 0.1,
    ) -> np.ndarray:
        """
        Generates a synthetic [101, 64] spectrogram.
        Class 0: Flat ambient noise / silence.
        Classes 1-20: Class-specific frequency resonant ridges + temporal envelope.
        """
        # Base ambient noise floor
        spec = rng.normal(loc=-3.0, scale=0.5, size=(self.time_steps, self.mel_bins)).astype(np.float32)

        if class_idx == 0:
            # Silence / ambient background noise
            return spec

        # Create class-specific harmonic resonances
        center_bin_1 = int(5 + (class_idx * 2.5)) % self.mel_bins
        center_bin_2 = int(15 + (class_idx * 2.0)) % self.mel_bins

        # Temporal envelope (speech burst in center 40 frames)
        t_center = self.time_steps // 2
        t_envelope = np.exp(-0.5 * ((np.arange(self.time_steps) - t_center) / 15.0) ** 2)

        # Inject energy into specific Mel bins modulated by temporal envelope
        spec[:, center_bin_1] += (3.5 * t_envelope).astype(np.float32)
        if center_bin_1 + 1 < self.mel_bins:
            spec[:, center_bin_1 + 1] += (2.0 * t_envelope).astype(np.float32)
        if center_bin_1 - 1 >= 0:
            spec[:, center_bin_1 - 1] += (2.0 * t_envelope).astype(np.float32)

        spec[:, center_bin_2] += (2.5 * t_envelope).astype(np.float32)

        return spec

    def generate_dataset(
        self,
        samples_per_class: int = 10,
        num_mock_speakers: int = 4,
    ) -> List[AudioSampleMeta]:
        """
        Generates a balanced synthetic dataset across 21 classes with mock speaker IDs.
        """
        rng = np.random.RandomState(self.seed)
        samples: List[AudioSampleMeta] = []
        speakers = [f"mock_speaker_{i+1:02d}" for i in range(num_mock_speakers)]

        for cls_idx in range(self.num_classes):
            label_id = "_background_" if cls_idx == 0 else f"num_{cls_idx:02d}"
            for s_idx in range(samples_per_class):
                spk = speakers[s_idx % num_mock_speakers]
                sample_id = f"synth_{label_id}_{s_idx:03d}_{spk}"
                spec = self.generate_synthetic_spectrogram(cls_idx, rng)

                meta = AudioSampleMeta(
                    sample_id=sample_id,
                    file_path=None,
                    spectrogram=spec,
                    label_idx=cls_idx,
                    label_id=label_id,
                    speaker_id=spk,
                    duration_sec=1.0,
                    category="SYNTHETIC_PIPELINE_VALIDATION",
                )
                samples.append(meta)

        return samples
