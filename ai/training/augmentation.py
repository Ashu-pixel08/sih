"""
ai/training/augmentation.py
=============================================================================
SIH260042: AI-Powered Vernacular Pedagogy & Real-Time Translation
Acoustic & Spectrogram Data Augmentation Pipeline
=============================================================================

CRITICAL POLICY:
- Augmentation is strictly applied ONLY during training.
- Validation and test splits MUST NEVER be augmented.
- Augmentation operations simulate rural classroom acoustics (noise, timing jitter,
  microphone sensitivity variation) to improve generalization without leaking data.
=============================================================================
"""

import random
from typing import Optional, Tuple, Union

import numpy as np
import torch


class SpectrogramAugmentation:
    """
    Augmentation pipeline for 2D Log-Mel spectrograms [101, 64] or [1, 101, 64].
    Applies SpecAugment (Time & Frequency masking), additive Gaussian noise,
    time shifts, and random gain.
    """

    def __init__(
        self,
        time_mask_max: int = 10,
        freq_mask_max: int = 8,
        time_shift_max: int = 10,
        noise_level: float = 0.05,
        gain_db_range: Tuple[float, float] = (-3.0, 3.0),
        p: float = 0.5,
        seed: Optional[int] = None,
    ):
        self.time_mask_max = time_mask_max
        self.freq_mask_max = freq_mask_max
        self.time_shift_max = time_shift_max
        self.noise_level = noise_level
        self.gain_db_range = gain_db_range
        self.p = p

        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

    def apply_time_mask(self, spec: torch.Tensor) -> torch.Tensor:
        """Masks random vertical strip (time frames)."""
        # spec is [..., Time, Freq]
        time_steps = spec.shape[-2]
        if self.time_mask_max <= 0 or time_steps <= self.time_mask_max:
            return spec

        t = random.randint(1, self.time_mask_max)
        t0 = random.randint(0, time_steps - t)
        masked = spec.clone()
        masked[..., t0 : t0 + t, :] = 0.0
        return masked

    def apply_freq_mask(self, spec: torch.Tensor) -> torch.Tensor:
        """Masks random horizontal strip (frequency bins)."""
        # spec is [..., Time, Freq]
        freq_bins = spec.shape[-1]
        if self.freq_mask_max <= 0 or freq_bins <= self.freq_mask_max:
            return spec

        f = random.randint(1, self.freq_mask_max)
        f0 = random.randint(0, freq_bins - f)
        masked = spec.clone()
        masked[..., :, f0 : f0 + f] = 0.0
        return masked

    def apply_time_shift(self, spec: torch.Tensor) -> torch.Tensor:
        """Rolls spectrogram along time axis with zero-padding."""
        shift = random.randint(-self.time_shift_max, self.time_shift_max)
        if shift == 0:
            return spec

        shifted = torch.roll(spec, shifts=shift, dims=-2)
        if shift > 0:
            shifted[..., :shift, :] = 0.0
        else:
            shifted[..., shift:, :] = 0.0
        return shifted

    def apply_additive_noise(self, spec: torch.Tensor) -> torch.Tensor:
        """Adds zero-mean Gaussian noise scaled to spec variance."""
        noise = torch.randn_like(spec) * self.noise_level
        return spec + noise

    def apply_gain(self, spec: torch.Tensor) -> torch.Tensor:
        """Applies random gain in decibels."""
        gain_db = random.uniform(self.gain_db_range[0], self.gain_db_range[1])
        gain_factor = 10.0 ** (gain_db / 20.0)
        return spec * gain_factor

    def __call__(
        self, spec: Union[torch.Tensor, np.ndarray], is_training: bool = True
    ) -> torch.Tensor:
        """
        Applies augmentation transformations with probability p.
        Strictly returns unaltered tensor if is_training=False.
        """
        if isinstance(spec, np.ndarray):
            tensor = torch.from_numpy(spec).float()
        else:
            tensor = spec.clone().float()

        # NEVER augment non-training data (prevents validation/test leakage)
        if not is_training:
            return tensor

        if random.random() < self.p:
            tensor = self.apply_time_mask(tensor)

        if random.random() < self.p:
            tensor = self.apply_freq_mask(tensor)

        if random.random() < self.p:
            tensor = self.apply_time_shift(tensor)

        if random.random() < self.p:
            tensor = self.apply_additive_noise(tensor)

        if random.random() < self.p:
            tensor = self.apply_gain(tensor)

        return tensor
