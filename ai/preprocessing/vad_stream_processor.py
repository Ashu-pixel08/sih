"""
ai/preprocessing/vad_stream_processor.py
=============================================================================
SIH260042: AI-Powered Vernacular Pedagogy & Real-Time Translation
Streaming Voice Activity Detector (VAD) & Audio Endpointing Subsystem
=============================================================================

PURPOSE & HARDWARE CONSTRAINTS:
- Real edge microphones deliver audio in streaming 20–50 ms chunks.
- In rural classrooms, ambient noise (chatter, footsteps, desk taps) is common.
- This module implements an adaptive dual-feature VAD (Short-Time Energy + ZCR)
  with dynamic noise-floor tracking to:
  1. Continuously monitor the microphone in low-power idle mode.
  2. Detect speech onset and endpoint without cutting off word endings.
  3. Reject short transient clicks (< 120 ms).
  4. Format the captured utterance into the exact 16,000-sample (1.0s) window
     required by the downstream AudioPreprocessor and Speech Classifier.
=============================================================================
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np


class VADState(Enum):
    IDLE = "IDLE"
    ONSET_CANDIDATE = "ONSET_CANDIDATE"
    IN_SPEECH = "IN_SPEECH"
    HANGOVER = "HANGOVER"
    ENDPOINT_DETECTED = "ENDPOINT_DETECTED"


@dataclass
class VADConfig:
    sample_rate: int = 16000
    chunk_size_samples: int = 320  # 20 ms at 16 kHz
    initial_noise_floor_db: float = -50.0
    min_noise_floor_db: float = -65.0
    speech_threshold_margin_db: float = 12.0  # dB above noise floor
    min_speech_duration_ms: float = 120.0     # Reject transient clicks shorter than 120ms
    max_speech_duration_ms: float = 3000.0    # Hard cut for isolated word vocabulary
    hangover_duration_ms: float = 300.0       # Hold speech active across short pauses
    target_window_samples: int = 16000        # 1.0s output window for downstream model
    noise_adapt_rate: float = 0.05            # Exponential moving average for noise floor


class StreamingVADProcessor:
    """
    Real-time streaming Voice Activity Detector and Speech Endpointing processor.
    """

    def __init__(self, config: Optional[VADConfig] = None):
        self.config = config or VADConfig()
        self.state = VADState.IDLE

        # Noise tracking
        self.noise_floor_db = self.config.initial_noise_floor_db
        self.threshold_db = self.noise_floor_db + self.config.speech_threshold_margin_db

        # Frame counters
        chunk_ms = (self.config.chunk_size_samples / self.config.sample_rate) * 1000.0
        self.min_speech_frames = max(1, int(self.config.min_speech_duration_ms / chunk_ms))
        self.max_speech_frames = max(1, int(self.config.max_speech_duration_ms / chunk_ms))
        self.hangover_frames = max(1, int(self.config.hangover_duration_ms / chunk_ms))

        # State tracking
        self.speech_frame_count = 0
        self.silence_frame_count = 0
        self.audio_buffer: List[float] = []
        self.history_metrics: List[Dict[str, float]] = []

    def compute_short_time_energy(self, chunk: np.ndarray) -> float:
        """Computes root-mean-square energy in decibels (dBFS)."""
        ste = float(np.mean(chunk**2))
        if ste <= 1e-12:
            return -100.0
        return float(10.0 * math.log10(ste))

    def compute_zero_crossing_rate(self, chunk: np.ndarray) -> float:
        """Computes rate of sign changes across successive audio samples."""
        if len(chunk) < 2:
            return 0.0
        signs = np.sign(chunk)
        signs[signs == 0] = 1
        zero_crossings = np.sum(np.abs(signs[1:] - signs[:-1])) / 2.0
        return float(zero_crossings / (len(chunk) - 1))

    def adapt_noise_floor(self, current_energy_db: float) -> None:
        """Slowly updates noise floor estimate during confirmed silence."""
        alpha = self.config.noise_adapt_rate
        # Only adapt downward or slowly upward to prevent speech from raising noise floor
        if current_energy_db < self.noise_floor_db + 6.0:
            self.noise_floor_db = (1.0 - alpha) * self.noise_floor_db + alpha * current_energy_db
            self.noise_floor_db = max(getattr(self.config, "min_noise_floor_db", -65.0), self.noise_floor_db)
            self.threshold_db = self.noise_floor_db + self.config.speech_threshold_margin_db

    def reset(self) -> None:
        """Resets the state machine and clears the audio buffer."""
        self.state = VADState.IDLE
        self.speech_frame_count = 0
        self.silence_frame_count = 0
        self.audio_buffer.clear()

    def process_chunk(self, chunk: np.ndarray) -> Optional[np.ndarray]:
        """
        Processes a single streaming audio chunk.
        Returns:
            np.ndarray of exactly target_window_samples (16,000 Float32) when
            an utterance endpoint is confirmed, or None while listening.
        """
        if chunk.ndim > 1:
            chunk = np.mean(chunk, axis=1)

        energy_db = self.compute_short_time_energy(chunk)
        zcr = self.compute_zero_crossing_rate(chunk)
        is_speech_frame = energy_db >= self.threshold_db

        self.history_metrics.append({
            "energy_db": round(energy_db, 2),
            "zcr": round(zcr, 4),
            "threshold_db": round(self.threshold_db, 2),
            "is_speech": is_speech_frame,
            "state": self.state.value,
        })

        extracted_utterance: Optional[np.ndarray] = None

        if self.state == VADState.IDLE:
            if is_speech_frame:
                self.state = VADState.ONSET_CANDIDATE
                self.speech_frame_count = 1
                self.audio_buffer.extend(chunk.tolist())
            else:
                self.adapt_noise_floor(energy_db)

        elif self.state == VADState.ONSET_CANDIDATE:
            self.audio_buffer.extend(chunk.tolist())
            if is_speech_frame:
                self.speech_frame_count += 1
                if self.speech_frame_count >= 2:
                    self.state = VADState.IN_SPEECH
            else:
                # Glitch / noise spike - reset back to IDLE
                self.reset()

        elif self.state == VADState.IN_SPEECH:
            self.audio_buffer.extend(chunk.tolist())

            if is_speech_frame:
                self.speech_frame_count += 1
                if self.speech_frame_count >= self.max_speech_frames:
                    # Max duration exceeded - trigger endpoint
                    extracted_utterance = self._extract_standard_window()
                    self.reset()
            else:
                self.state = VADState.HANGOVER
                self.silence_frame_count = 1

        elif self.state == VADState.HANGOVER:
            self.audio_buffer.extend(chunk.tolist())
            if is_speech_frame:
                # Speech resumed within hangover window
                self.state = VADState.IN_SPEECH
                self.speech_frame_count += 1
                self.silence_frame_count = 0
            else:
                self.silence_frame_count += 1
                if self.silence_frame_count >= self.hangover_frames:
                    # Endpoint reached!
                    if self.speech_frame_count >= self.min_speech_frames:
                        extracted_utterance = self._extract_standard_window()
                    self.reset()

        return extracted_utterance

    def _extract_standard_window(self) -> np.ndarray:
        """
        Extracts and centers the recorded audio buffer into exactly 16,000 samples.
        """
        raw_audio = np.array(self.audio_buffer, dtype=np.float32)
        target_len = self.config.target_window_samples
        current_len = len(raw_audio)

        if current_len == target_len:
            return raw_audio

        if current_len < target_len:
            pad_total = target_len - current_len
            pad_left = pad_total // 2
            pad_right = pad_total - pad_left
            return np.pad(raw_audio, (pad_left, pad_right), mode="constant")

        # If longer than target_len, extract energy-centered window
        window_size = target_len
        step = max(1, self.config.chunk_size_samples)
        best_idx = 0
        max_energy = -1.0
        for start in range(0, current_len - window_size + 1, step):
            segment = raw_audio[start : start + window_size]
            energy = float(np.sum(segment**2))
            if energy > max_energy:
                max_energy = energy
                best_idx = start

        return raw_audio[best_idx : best_idx + window_size].copy()

    def process_continuous_audio(self, audio: np.ndarray) -> List[np.ndarray]:
        """
        Convenience method: Simulates streaming playback of a long continuous audio
        array through the VAD and returns all captured 1.0s utterances.
        """
        self.reset()
        chunk_size = self.config.chunk_size_samples
        captured: List[np.ndarray] = []

        for start in range(0, len(audio) - chunk_size + 1, chunk_size):
            chunk = audio[start : start + chunk_size]
            res = self.process_chunk(chunk)
            if res is not None:
                captured.append(res)

        # Flush final utterance if audio stream ended while in speech or hangover
        if self.state in [VADState.IN_SPEECH, VADState.HANGOVER]:
            if self.speech_frame_count >= self.min_speech_frames:
                captured.append(self._extract_standard_window())
            self.reset()

        return captured
