"""
ai/speech/audio_quality_gate.py
=============================================================================
SIH260042: Bhasha Setu Audio & Pronunciation Quality Gate
=============================================================================
Enforces strict programmatic validation on synthesized speech before playback:
1. Valid 16-bit PCM WAV headers (mono, 16 kHz).
2. Numerical validity (zero NaN, zero Inf).
3. Amplitude health (RMS in valid dBFS band, zero severe clipping).
4. Silence & pause sanity (no excessive leading/trailing silence or abnormal dead pauses).
5. Duration plausibility against character/syllable bounds.
6. Honest status labeling:
   - AUDIO_READY (passed all quality checks)
   - AUDIO_PROTOTYPE_PENDING_VALIDATION (synthetic prototype; acoustic checks passed)
   - AUDIO_SYNTHETIC_UNVERIFIED (uncontrolled neural output requiring review)
   - AUDIO_FAILED (failed acoustic or phonetic quality gate)
   * NOTE: AUDIO_VERIFIED is STRICTLY PROHIBITED unless provenance is certified human field audio.
=============================================================================
"""

import io
import math
import wave
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np


@dataclass
class AudioQualityResult:
    """Outcome of audio quality gate evaluation."""
    is_valid: bool
    status: str  # AUDIO_READY, AUDIO_PROTOTYPE_PENDING_VALIDATION, AUDIO_SYNTHETIC_UNVERIFIED, AUDIO_FAILED
    rejection_reasons: List[str] = field(default_factory=list)
    duration_sec: float = 0.0
    sample_rate: int = 16000
    channels: int = 1
    rms_dbfs: float = -100.0
    peak_dbfs: float = -100.0
    clipping_samples: int = 0
    silence_ratio: float = 0.0
    max_silence_run_ms: float = 0.0
    metadata: Dict[str, any] = field(default_factory=dict)


class AudioQualityGate:
    """Evaluates speech audio bytes against acoustic, phonetic, and provenance standards."""

    def __init__(
        self,
        expected_sample_rate: int = 16000,
        max_clipping_samples: int = 5,
        min_rms_dbfs: float = -38.0,
        max_rms_dbfs: float = -6.0,
        max_silence_ratio_word: float = 0.80,
        max_silence_ratio_sentence: float = 0.55,
        max_internal_pause_ms: float = 700.0,
    ):
        self.expected_sample_rate = expected_sample_rate
        self.max_clipping_samples = max_clipping_samples
        self.min_rms_dbfs = min_rms_dbfs
        self.max_rms_dbfs = max_rms_dbfs
        self.max_silence_ratio_word = max_silence_ratio_word
        self.max_silence_ratio_sentence = max_silence_ratio_sentence
        self.max_internal_pause_ms = max_internal_pause_ms

    @staticmethod
    def trim_silence(
        waveform: np.ndarray,
        sample_rate: int = 16000,
        threshold: float = 0.015,
        pad_ms: float = 70.0
    ) -> np.ndarray:
        """Trims leading and trailing silence with a natural acoustic padding ramp."""
        if len(waveform) == 0:
            return waveform
        win = int(0.020 * sample_rate)
        hop = int(0.010 * sample_rate)
        pad = int((pad_ms / 1000.0) * sample_rate)

        energies = [np.sqrt(np.mean(waveform[i:i + win] ** 2)) for i in range(0, len(waveform) - win, hop)]
        active = [i for i, e in enumerate(energies) if e >= threshold]
        if not active:
            return waveform
        start_sample = max(0, active[0] * hop - pad)
        end_sample = min(len(waveform), active[-1] * hop + win + pad)
        return waveform[start_sample:end_sample]

    def validate_audio(
        self,
        audio_bytes: bytes,
        text: str,
        language: str,
        provenance: str = "SYNTHETIC_GENERATED_TTS"
    ) -> AudioQualityResult:
        rejection_reasons = []

        if not audio_bytes or len(audio_bytes) < 44:
            return AudioQualityResult(
                is_valid=False,
                status="AUDIO_FAILED",
                rejection_reasons=["EMPTY_OR_TRUNCATED_WAV_HEADER"]
            )

        # 1. Parse WAV header
        try:
            with io.BytesIO(audio_bytes) as buf:
                with wave.open(buf, "rb") as wf:
                    channels = wf.getnchannels()
                    sampwidth = wf.getsampwidth()
                    framerate = wf.getframerate()
                    nframes = wf.getnframes()
                    raw_data = wf.readframes(nframes)
        except Exception as ex:
            return AudioQualityResult(
                is_valid=False,
                status="AUDIO_FAILED",
                rejection_reasons=[f"CORRUPT_WAV_HEADER: {ex}"]
            )

        if channels != 1:
            rejection_reasons.append(f"UNEXPECTED_CHANNELS: got {channels}, expected 1 (mono)")
        if sampwidth != 2:
            rejection_reasons.append(f"UNEXPECTED_BIT_DEPTH: got {sampwidth*8}-bit, expected 16-bit")
        if framerate != self.expected_sample_rate:
            rejection_reasons.append(f"UNEXPECTED_SAMPLE_RATE: got {framerate} Hz, expected {self.expected_sample_rate} Hz")

        duration_sec = nframes / float(framerate) if framerate > 0 else 0.0
        if duration_sec < 0.15:
            rejection_reasons.append(f"AUDIO_TOO_SHORT: {duration_sec:.2f}s (min 0.15s)")

        # Approximate syllable-based duration bounds
        words = (text or "").strip().split()
        is_single_word = len(words) <= 1
        expected_min_dur = max(0.20, len(words) * 0.15)
        expected_max_dur = max(2.5, len(text) * 0.25 + 1.5)
        if duration_sec > expected_max_dur:
            rejection_reasons.append(f"DURATION_EXCEEDS_PLAUSIBLE_BOUND: {duration_sec:.2f}s > {expected_max_dur:.2f}s")

        # 2. Convert to float array and check numeric validity
        try:
            samples = np.frombuffer(raw_data, dtype=np.int16).astype(np.float64) / 32768.0
        except Exception as ex:
            return AudioQualityResult(
                is_valid=False,
                status="AUDIO_FAILED",
                rejection_reasons=[f"RAW_SAMPLE_DECODE_ERROR: {ex}"],
                duration_sec=duration_sec,
                sample_rate=framerate
            )

        if len(samples) == 0:
            return AudioQualityResult(
                is_valid=False,
                status="AUDIO_FAILED",
                rejection_reasons=["ZERO_AUDIO_SAMPLES"],
                duration_sec=0.0,
                sample_rate=framerate
            )

        if np.isnan(samples).any() or np.isinf(samples).any():
            rejection_reasons.append("NUMERICAL_INSTABILITY: NaN or Inf detected in audio samples")

        # 3. Amplitude & Clipping
        peak = float(np.max(np.abs(samples))) if len(samples) > 0 else 0.0
        peak_dbfs = 20.0 * math.log10(peak) if peak > 1e-8 else -100.0
        rms = float(np.sqrt(np.mean(samples ** 2))) if len(samples) > 0 else 0.0
        rms_dbfs = 20.0 * math.log10(rms) if rms > 1e-8 else -100.0

        clipping_samples = int(np.sum(np.abs(samples) >= 0.995))
        if clipping_samples > self.max_clipping_samples:
            rejection_reasons.append(f"AUDIO_CLIPPING: {clipping_samples} clipped samples")

        if rms_dbfs < self.min_rms_dbfs:
            rejection_reasons.append(f"AUDIO_TOO_QUIET: RMS is {rms_dbfs:.1f} dBFS (min {self.min_rms_dbfs} dBFS)")
        elif rms_dbfs > self.max_rms_dbfs:
            rejection_reasons.append(f"AUDIO_TOO_LOUD: RMS is {rms_dbfs:.1f} dBFS (max {self.max_rms_dbfs} dBFS)")

        # 4. Silence & Pause Analysis
        win_size = int(0.025 * framerate)
        hop_size = int(0.010 * framerate)
        silence_thresh = 0.015  # -36 dBFS
        energies = []
        if len(samples) >= win_size:
            for s in range(0, len(samples) - win_size, hop_size):
                f_rms = np.sqrt(np.mean(samples[s:s + win_size] ** 2))
                energies.append(f_rms)

        energies = np.array(energies)
        silence_frames = np.sum(energies < silence_thresh) if len(energies) > 0 else 0
        silence_ratio = float(silence_frames / len(energies)) if len(energies) > 0 else 1.0

        max_allowed_silence = self.max_silence_ratio_word if is_single_word else self.max_silence_ratio_sentence
        if silence_ratio > max_allowed_silence:
            rejection_reasons.append(f"EXCESSIVE_SILENCE: silence ratio is {silence_ratio:.2f} (max {max_allowed_silence:.2f})")

        # Internal Pause detection
        silence_run = 0
        max_silence_run = 0
        for e in energies:
            if e < silence_thresh:
                silence_run += 1
                if silence_run > max_silence_run:
                    max_silence_run = silence_run
            else:
                silence_run = 0

        max_silence_run_ms = max_silence_run * 10.0
        if not is_single_word and max_silence_run_ms > self.max_internal_pause_ms:
            rejection_reasons.append(f"ABNORMAL_INTERNAL_PAUSE: {max_silence_run_ms:.0f}ms (max {self.max_internal_pause_ms:.0f}ms)")

        # 5. Status Determination (Strict Truthfulness)
        is_valid = len(rejection_reasons) == 0

        if not is_valid:
            status = "AUDIO_FAILED"
        elif provenance == "HUMAN_FIELD_RECORDING":
            status = "AUDIO_READY"
        elif "PROTOTYPE" in provenance:
            status = "AUDIO_PROTOTYPE_PENDING_VALIDATION"
        else:
            status = "AUDIO_SYNTHETIC_UNVERIFIED"

        return AudioQualityResult(
            is_valid=is_valid,
            status=status,
            rejection_reasons=rejection_reasons,
            duration_sec=round(duration_sec, 3),
            sample_rate=framerate,
            channels=channels,
            rms_dbfs=round(rms_dbfs, 2),
            peak_dbfs=round(peak_dbfs, 2),
            clipping_samples=clipping_samples,
            silence_ratio=round(silence_ratio, 3),
            max_silence_run_ms=round(max_silence_run_ms, 1),
            metadata={
                "is_single_word": is_single_word,
                "token_length": len(text),
                "words_count": len(words)
            }
        )
