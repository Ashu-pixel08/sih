"""
ai/speech/speech_classifier.py
=============================================================================
SIH260042: AI-Powered Vernacular Pedagogy & Real-Time Translation
Lightweight 2D Spectrogram CNN Speech Classifier (MobileNetV3 Style)
=============================================================================

STATUS POLICY & DISCLAIMER:
---------------------------
RESEARCH / BASELINE IMPLEMENTATION / ARCHITECTURE VALIDATION ONLY.
This model architecture is implemented to validate the edge inference pipeline,
input/output contracts, and Android deployment readiness. Because the available
public speech corpus lacks sufficient isolated recordings for numbers 1–20,
this model MUST NOT be presented as a production-ready Mundari speech recognizer
until sufficient native-speaker recordings are acquired.

INPUT CONTRACT:
- Shape: [Batch, 101, 64, 1] (NHWC) or [Batch, 1, 101, 64] (NCHW)
- Mel Frequency Bins: 64
- Time Frames: 101 (1.00s audio at 16 kHz, 25ms window, 10ms hop)
- Dtype: Float32

OUTPUT CONTRACT:
- Shape: [Batch, 21]
- Class 0: _background_ (silence, noise, unclassified vocalization)
- Classes 1–20: num_01 to num_20 (Mundari numerals 1 to 20)
- Activation: Softmax probabilities summing to 1.0
=============================================================================
"""

import json
import os
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import torch
import torch.nn as nn


class DepthwiseSeparableConv(nn.Module):
    """
    Lightweight 2D Depthwise Separable Convolution block.
    Combines spatial filtering (depthwise 3x3) with channel mixing (pointwise 1x1).
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        stride: Union[int, Tuple[int, int]] = 1,
        expansion: int = 1,
    ):
        super().__init__()
        mid_channels = in_channels * expansion

        # Optional expansion pointwise conv
        layers: List[nn.Module] = []
        if expansion != 1:
            layers.extend(
                [
                    nn.Conv2d(
                        in_channels,
                        mid_channels,
                        kernel_size=1,
                        bias=False,
                    ),
                    nn.BatchNorm2d(mid_channels),
                    nn.ReLU6(inplace=True),
                ]
            )
        else:
            mid_channels = in_channels

        # Depthwise 3x3 conv
        layers.extend(
            [
                nn.Conv2d(
                    mid_channels,
                    mid_channels,
                    kernel_size=3,
                    stride=stride,
                    padding=1,
                    groups=mid_channels,
                    bias=False,
                ),
                nn.BatchNorm2d(mid_channels),
                nn.ReLU6(inplace=True),
            ]
        )

        # Pointwise 1x1 projection
        layers.extend(
            [
                nn.Conv2d(
                    mid_channels,
                    out_channels,
                    kernel_size=1,
                    bias=False,
                ),
                nn.BatchNorm2d(out_channels),
            ]
        )

        self.block = nn.Sequential(*layers)
        self.use_residual = (
            stride == 1
            if isinstance(stride, int)
            else (stride[0] == 1 and stride[1] == 1)
        ) and in_channels == out_channels

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.use_residual:
            return x + self.block(x)
        return self.block(x)


class LightweightSpectrogramCNN(nn.Module):
    """
    Lightweight 2D Spectrogram Convolutional Neural Network for 21-class
    spoken numeral classification on low-power edge devices.
    """

    def __init__(
        self,
        num_classes: int = 21,
        input_time_steps: int = 101,
        input_mel_bins: int = 64,
        dropout_rate: float = 0.2,
        registry_path: Optional[str] = None,
    ):
        super().__init__()
        self.num_classes = num_classes
        self.input_time_steps = input_time_steps
        self.input_mel_bins = input_mel_bins
        self.dropout_rate = dropout_rate

        # Initial standard convolution: [1, 101, 64] -> [16, 51, 32]
        self.conv1 = nn.Sequential(
            nn.Conv2d(
                in_channels=1,
                out_channels=16,
                kernel_size=3,
                stride=2,
                padding=1,
                bias=False,
            ),
            nn.BatchNorm2d(16),
            nn.ReLU6(inplace=True),
        )

        # Stage 1: [16, 51, 32] -> [32, 51, 32]
        self.ds1 = DepthwiseSeparableConv(16, 32, stride=1, expansion=2)

        # Stage 2: [32, 51, 32] -> [48, 26, 16]
        self.ds2 = DepthwiseSeparableConv(32, 48, stride=2, expansion=2)

        # Stage 3: [48, 26, 16] -> [64, 26, 16]
        self.ds3 = DepthwiseSeparableConv(48, 64, stride=1, expansion=2)

        # Stage 4: [64, 26, 16] -> [96, 13, 8]
        self.ds4 = DepthwiseSeparableConv(64, 96, stride=2, expansion=2)

        # Stage 5: [96, 13, 8] -> [128, 13, 8]
        self.ds5 = DepthwiseSeparableConv(96, 128, stride=1, expansion=2)

        # Fixed static average pooling to guarantee zero loop overhead in TFLite/FlatBuffers
        self.pool = nn.AvgPool2d(kernel_size=(13, 8))

        # Classifier head
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128, 64),
            nn.ReLU6(inplace=True),
            nn.Dropout(p=dropout_rate),
            nn.Linear(64, num_classes),
        )

        # Load class metadata from content registry
        self.class_labels: List[str] = self._load_class_labels(registry_path)

    def _load_class_labels(self, registry_path: Optional[str]) -> List[str]:
        """Loads canonical 21 class IDs from content registry."""
        if registry_path is None:
            # Look up standard path
            cur_dir = os.path.dirname(os.path.abspath(__file__))
            registry_path = os.path.normpath(
                os.path.join(cur_dir, "..", "..", "content", "content_registry.json")
            )

        if os.path.exists(registry_path):
            with open(registry_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            labels = ["_background_"] * self.num_classes
            labels[0] = data.get("background_class", {}).get(
                "label_id", "_background_"
            )
            for item in data.get("items", []):
                idx = item["class_index"]
                if 0 <= idx < self.num_classes:
                    labels[idx] = item["label_id"]
            return labels
        else:
            # Fallback standard IDs
            labels = ["_background_"] + [f"num_{i:02d}" for i in range(1, 21)]
            return labels

    def forward(
        self,
        x: torch.Tensor,
        return_probabilities: bool = True,
    ) -> torch.Tensor:
        """
        Forward pass.
        Accepts:
            x: [B, 101, 64, 1] (NHWC) or [B, 1, 101, 64] (NCHW)
        Returns:
            Logits [B, 21] if return_probabilities=False
            Softmax Probabilities [B, 21] if return_probabilities=True
        """
        # Adapt NHWC to NCHW if needed
        if x.dim() == 4 and x.shape[-1] == 1:
            x = x.permute(0, 3, 1, 2)
        elif x.dim() == 3:
            # [B, 101, 64] -> [B, 1, 101, 64]
            x = x.unsqueeze(1)

        h = self.conv1(x)
        h = self.ds1(h)
        h = self.ds2(h)
        h = self.ds3(h)
        h = self.ds4(h)
        h = self.ds5(h)
        h = self.pool(h)
        logits = self.classifier(h)

        if return_probabilities:
            return torch.softmax(logits, dim=-1)
        return logits

    @torch.no_grad()
    def predict(
        self,
        spectrogram: np.ndarray,
        confidence_threshold: float = 0.65,
        margin_threshold: float = 0.20,
    ) -> Dict[str, Any]:
        """
        Runs edge-grade deterministic prediction on a single spectrogram.
        Implements the standardized model interface from implementation_plan.md.
        """
        self.eval()

        if isinstance(spectrogram, np.ndarray):
            tensor = torch.from_numpy(spectrogram).float()
        else:
            tensor = spectrogram.float()

        # Ensure batch dimension
        if tensor.dim() == 2:  # [101, 64]
            tensor = tensor.unsqueeze(0).unsqueeze(0)  # [1, 1, 101, 64]
        elif tensor.dim() == 3:
            if tensor.shape[-1] == 1:  # [101, 64, 1]
                tensor = tensor.unsqueeze(0).permute(0, 3, 1, 2)  # [1, 1, 101, 64]
            else:  # [1, 101, 64]
                tensor = tensor.unsqueeze(1)  # [1, 1, 101, 64]
        elif tensor.dim() == 4 and tensor.shape[-1] == 1:  # [1, 101, 64, 1]
            tensor = tensor.permute(0, 3, 1, 2)

        probs = self.forward(tensor, return_probabilities=True).squeeze(0)
        probs_np = probs.cpu().numpy()

        sorted_indices = np.argsort(probs_np)[::-1]
        top_idx = int(sorted_indices[0])
        top_confidence = float(probs_np[top_idx])
        second_confidence = (
            float(probs_np[sorted_indices[1]]) if len(sorted_indices) > 1 else 0.0
        )
        margin = float(top_confidence - second_confidence)

        label = (
            self.class_labels[top_idx]
            if top_idx < len(self.class_labels)
            else f"class_{top_idx}"
        )

        is_confident = (
            top_confidence >= confidence_threshold
            and margin >= margin_threshold
            and top_idx != 0
        )

        return {
            "class_index": top_idx,
            "label": label,
            "confidence": round(top_confidence, 4),
            "margin": round(margin, 4),
            "is_confident": is_confident,
            "probabilities": [round(float(p), 5) for p in probs_np],
        }

    def count_parameters(self) -> int:
        """Returns total trainable parameter count."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def get_model_summary(self) -> Dict[str, Any]:
        """Returns architectural summary and memory metrics."""
        params = self.count_parameters()
        fp32_size_kb = (params * 4) / 1024.0
        int8_est_kb = params / 1024.0
        return {
            "architecture": "LightweightSpectrogramCNN",
            "num_classes": self.num_classes,
            "parameters": params,
            "fp32_size_kb": round(fp32_size_kb, 2),
            "int8_est_kb": round(int8_est_kb, 2),
            "input_tensor_shape": [1, self.input_time_steps, self.input_mel_bins, 1],
            "output_tensor_shape": [1, self.num_classes],
            "status": "RESEARCH / PIPELINE VALIDATION ONLY",
        }
