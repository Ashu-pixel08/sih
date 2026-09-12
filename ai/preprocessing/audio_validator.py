"""
Audio Validator Module for FLN Pedagogy & Speech Pipeline.

Performs comprehensive validation on audio files:
- Format verification (WAV headers, sample rate, channels, bit depth)
- Signal analysis (RMS energy, peak amplitude, digital clipping detection, silence detection)
- Quality assessment (DC offset, estimated SNR)
- Manifest generation for reproducibility and auditability.
"""

import os
import glob
import wave
import json
import struct
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import numpy as np


@dataclass
class AudioValidationResult:
    file_path: str
    file_name: str
    file_size_bytes: int
    is_valid: bool
    sample_rate: int
    channels: int
    bit_depth: int
    duration_seconds: float
    num_frames: int
    rms_energy: float
    peak_amplitude: float
    is_silent: bool
    has_clipping: bool
    dc_offset: float
    estimated_snr_db: Optional[float]
    issues: List[str]


class AudioValidator:
    """Validates audio files against classroom speech and educational audio standards."""

    def __init__(
        self,
        expected_sample_rate: Optional[int] = None,
        expected_channels: Optional[int] = None,
        min_duration_sec: float = 0.2,
        max_duration_sec: float = 15.0,
        silence_threshold_rms: float = 0.005,
        clipping_threshold: float = 0.995,
    ):
        self.expected_sample_rate = expected_sample_rate
        self.expected_channels = expected_channels
        self.min_duration_sec = min_duration_sec
        self.max_duration_sec = max_duration_sec
        self.silence_threshold_rms = silence_threshold_rms
        self.clipping_threshold = clipping_threshold

    def load_wav_as_float(self, file_path: str) -> tuple[np.ndarray, int, int, int]:
        """
        Loads WAV file into float32 array in range [-1.0, 1.0].
        Returns (audio_data, sample_rate, channels, bit_depth).
        """
        with wave.open(file_path, "rb") as wf:
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            sample_rate = wf.getframerate()
            num_frames = wf.getnframes()
            raw_bytes = wf.readframes(num_frames)

        bit_depth = sampwidth * 8

        if sampwidth == 1:  # 8-bit unsigned PCM
            data = np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32)
            data = (data - 128.0) / 128.0
        elif sampwidth == 2:  # 16-bit signed PCM
            data = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)
            data = data / 32768.0
        elif sampwidth == 3:  # 24-bit signed PCM
            # Unpack 3-byte integers
            total_samples = len(raw_bytes) // 3
            data = np.zeros(total_samples, dtype=np.float32)
            for i in range(total_samples):
                sample_bytes = raw_bytes[i * 3 : (i + 1) * 3]
                # Pad to 4 bytes with sign extension
                int_val = int.from_bytes(sample_bytes, byteorder="little", signed=True)
                data[i] = int_val / 8388608.0
        elif sampwidth == 4:  # 32-bit signed PCM or float
            # Try int32 first, check scale
            raw_int32 = np.frombuffer(raw_bytes, dtype=np.int32)
            if np.max(np.abs(raw_int32)) > 1.0:
                data = raw_int32.astype(np.float32) / 2147483648.0
            else:
                data = np.frombuffer(raw_bytes, dtype=np.float32)
        else:
            raise ValueError(f"Unsupported sample width: {sampwidth} bytes ({bit_depth} bits)")

        if channels > 1:
            data = data.reshape(-1, channels)

        return data, sample_rate, channels, bit_depth

    def validate_file(self, file_path: str) -> AudioValidationResult:
        """Validates a single WAV file and returns detailed metric analysis."""
        issues = []
        file_name = os.path.basename(file_path)

        if not os.path.isfile(file_path):
            return AudioValidationResult(
                file_path=file_path,
                file_name=file_name,
                file_size_bytes=0,
                is_valid=False,
                sample_rate=0,
                channels=0,
                bit_depth=0,
                duration_seconds=0.0,
                num_frames=0,
                rms_energy=0.0,
                peak_amplitude=0.0,
                is_silent=True,
                has_clipping=False,
                dc_offset=0.0,
                estimated_snr_db=None,
                issues=["File does not exist"],
            )

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return AudioValidationResult(
                file_path=file_path,
                file_name=file_name,
                file_size_bytes=0,
                is_valid=False,
                sample_rate=0,
                channels=0,
                bit_depth=0,
                duration_seconds=0.0,
                num_frames=0,
                rms_energy=0.0,
                peak_amplitude=0.0,
                is_silent=True,
                has_clipping=False,
                dc_offset=0.0,
                estimated_snr_db=None,
                issues=["File is empty (0 bytes)"],
            )

        try:
            audio, sr, ch, bit_depth = self.load_wav_as_float(file_path)
        except Exception as e:
            return AudioValidationResult(
                file_path=file_path,
                file_name=file_name,
                file_size_bytes=file_size,
                is_valid=False,
                sample_rate=0,
                channels=0,
                bit_depth=0,
                duration_seconds=0.0,
                num_frames=0,
                rms_energy=0.0,
                peak_amplitude=0.0,
                is_silent=True,
                has_clipping=False,
                dc_offset=0.0,
                estimated_snr_db=None,
                issues=[f"Corrupted or invalid WAV header: {str(e)}"],
            )

        # Convert to mono for scalar analysis if multi-channel
        mono_audio = np.mean(audio, axis=1) if ch > 1 else audio
        num_frames = len(mono_audio)
        duration = num_frames / float(sr) if sr > 0 else 0.0

        # Calculations
        rms = float(np.sqrt(np.mean(mono_audio**2))) if num_frames > 0 else 0.0
        peak = float(np.max(np.abs(mono_audio))) if num_frames > 0 else 0.0
        dc_offset = float(np.mean(mono_audio)) if num_frames > 0 else 0.0
        is_silent = rms < self.silence_threshold_rms
        has_clipping = peak >= self.clipping_threshold

        # Estimated SNR: ratio of speech frames (> 10% peak) to noise floor frames (< 5% peak)
        frame_len = int(0.025 * sr)  # 25 ms frames
        if frame_len > 0 and num_frames >= frame_len:
            num_win = num_frames // frame_len
            frames = mono_audio[: num_win * frame_len].reshape(num_win, frame_len)
            frame_rms = np.sqrt(np.mean(frames**2, axis=1))
            max_rms = float(np.max(frame_rms)) if len(frame_rms) > 0 else 0.0
            if max_rms > 1e-6:
                signal_frames = frame_rms[frame_rms > 0.1 * max_rms]
                noise_frames = frame_rms[frame_rms < 0.05 * max_rms]
                signal_power = float(np.mean(signal_frames**2)) if len(signal_frames) > 0 else 0.0
                noise_power = float(np.mean(noise_frames**2)) if len(noise_frames) > 0 else 0.0
                if noise_power > 1e-10 and signal_power > 0:
                    estimated_snr_db = float(10.0 * np.log10(signal_power / noise_power))
                else:
                    estimated_snr_db = None
            else:
                estimated_snr_db = None
        else:
            estimated_snr_db = None

        # Issue checks
        if self.expected_sample_rate and sr != self.expected_sample_rate:
            issues.append(f"Sample rate {sr} Hz != expected {self.expected_sample_rate} Hz")
        if self.expected_channels and ch != self.expected_channels:
            issues.append(f"Channel count {ch} != expected {self.expected_channels}")
        if duration < self.min_duration_sec:
            issues.append(f"Duration {duration:.2f}s is below minimum {self.min_duration_sec:.2f}s")
        if duration > self.max_duration_sec:
            issues.append(f"Duration {duration:.2f}s exceeds maximum {self.max_duration_sec:.2f}s")
        if is_silent:
            issues.append(f"Audio appears silent (RMS={rms:.6f} < threshold {self.silence_threshold_rms})")
        if has_clipping:
            issues.append(f"Digital clipping detected (Peak amplitude={peak:.4f} >= {self.clipping_threshold})")
        if abs(dc_offset) > 0.05:
            issues.append(f"High DC offset detected ({dc_offset:.4f})")

        is_valid = len(issues) == 0

        return AudioValidationResult(
            file_path=file_path,
            file_name=file_name,
            file_size_bytes=file_size,
            is_valid=is_valid,
            sample_rate=sr,
            channels=ch,
            bit_depth=bit_depth,
            duration_seconds=round(duration, 4),
            num_frames=num_frames,
            rms_energy=round(rms, 6),
            peak_amplitude=round(peak, 4),
            is_silent=is_silent,
            has_clipping=has_clipping,
            dc_offset=round(dc_offset, 6),
            estimated_snr_db=round(estimated_snr_db, 2) if estimated_snr_db is not None else None,
            issues=issues,
        )

    def validate_directory(self, dir_path: str, pattern: str = "**/*.wav") -> Dict[str, Any]:
        """Validates all matching audio files in directory and returns summary report."""
        search_path = os.path.join(dir_path, pattern)
        files = glob.glob(search_path, recursive=True)
        results = [self.validate_file(f) for f in sorted(files)]

        total_files = len(results)
        valid_files = sum(1 for r in results if r.is_valid)
        corrupt_files = sum(1 for r in results if not r.is_valid and r.file_size_bytes == 0)
        silent_files = sum(1 for r in results if r.is_silent)
        clipping_files = sum(1 for r in results if r.has_clipping)
        total_duration = sum(r.duration_seconds for r in results)

        return {
            "directory": dir_path,
            "pattern": pattern,
            "total_files": total_files,
            "valid_files": valid_files,
            "invalid_files": total_files - valid_files,
            "corrupt_files": corrupt_files,
            "silent_files": silent_files,
            "clipping_files": clipping_files,
            "total_duration_minutes": round(total_duration / 60.0, 2),
            "results": [asdict(r) for r in results],
        }

    def generate_manifest(self, dir_path: str, output_manifest_path: str) -> Dict[str, Any]:
        """Runs directory validation and writes the output manifest to JSON."""
        summary = self.validate_directory(dir_path)
        os.makedirs(os.path.dirname(output_manifest_path), exist_ok=True)
        with open(output_manifest_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        return summary


if __name__ == "__main__":
    import sys

    validator = AudioValidator()
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    print(f"Validating audio in: {target_dir}")
    report = validator.validate_directory(target_dir)
    print(f"Total files: {report['total_files']}")
    print(f"Valid files: {report['valid_files']}")
    print(f"Invalid files: {report['invalid_files']}")
    print(f"Total duration: {report['total_duration_minutes']} minutes")
