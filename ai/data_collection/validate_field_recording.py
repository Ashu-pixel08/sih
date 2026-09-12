"""
ai/data_collection/validate_field_recording.py
=============================================================================
SIH260042: AI-Powered Vernacular Pedagogy & Real-Time Translation
Automated Field Audio Acceptance & Quality Assurance Validator
=============================================================================

PURPOSE:
- Enforces the strict Recording Specification on field WAV audio files:
  1. Header & Format: RIFF WAVE, PCM 16-bit, 16000 Hz, Mono.
  2. Signal Energy: RMS between -28.0 dBFS and -16.0 dBFS.
  3. Clipping: Zero clipped samples (peak < -1.0 dBFS).
  4. Timing: Duration between 400ms and 2500ms; lead-in silence >= 50ms.
  5. Noise / SNR: Estimated SNR >= 22.0 dB.
  6. DC Offset: Absolute mean sample <= 0.005.
- Automatically generates machine-readable validation reports and classifies
  audio into ACCEPTED vs REJECTED_TECHNICAL.
=============================================================================
"""

import argparse
import json
import math
import os
import struct
import sys
import wave
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

cur_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.normpath(os.path.join(cur_dir, "..", ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)


@dataclass
class AudioValidationResult:
    """Detailed diagnostic results of an audio file technical inspection."""
    file_path: str
    file_name: str
    is_valid: bool
    status: str  # "PASSED", "REJECTED_TECHNICAL"
    sample_rate_hz: int
    channels: int
    bit_depth: int
    duration_ms: float
    rms_dbfs: float
    peak_dbfs: float
    estimated_snr_db: float
    clipping_detected: bool
    dc_offset: float
    lead_in_silence_ms: float
    lead_out_silence_ms: float
    failures: List[str]
    warnings: List[str]


class FieldAudioValidator:
    """
    Automated gatekeeper validating incoming field audio against project specifications.
    """

    # Mandatory technical bounds
    TARGET_SAMPLE_RATE: int = 16000
    TARGET_CHANNELS: int = 1
    TARGET_BIT_DEPTH: int = 16

    # Signal-level thresholds
    MIN_RMS_DBFS: float = -28.0
    MAX_RMS_DBFS: float = -16.0
    MAX_PEAK_DBFS: float = -1.0  # At least 1.0 dB headroom
    MIN_SNR_DB: float = 22.0
    MIN_DURATION_MS: float = 400.0
    MAX_DURATION_MS: float = 2500.0
    MIN_LEAD_IN_MS: float = 50.0
    MIN_LEAD_OUT_MS: float = 50.0
    MAX_DC_OFFSET: float = 0.005
    MIN_BG_RMS_DBFS: float = -55.0
    MAX_BG_RMS_DBFS: float = -20.0

    def validate_wav_file(self, wav_path: str, is_background: bool = False) -> AudioValidationResult:
        """Inspects a single WAV file against all technical criteria."""
        failures: List[str] = []
        warnings: List[str] = []
        file_name = os.path.basename(wav_path)

        if not os.path.exists(wav_path):
            return AudioValidationResult(
                file_path=wav_path,
                file_name=file_name,
                is_valid=False,
                status="REJECTED_TECHNICAL",
                sample_rate_hz=0,
                channels=0,
                bit_depth=0,
                duration_ms=0.0,
                rms_dbfs=-100.0,
                peak_dbfs=-100.0,
                estimated_snr_db=0.0,
                clipping_detected=False,
                dc_offset=0.0,
                lead_in_silence_ms=0.0,
                lead_out_silence_ms=0.0,
                failures=["File does not exist on disk."],
                warnings=[],
            )

        # 1. Inspect RIFF WAVE Header
        try:
            with wave.open(wav_path, "rb") as wf:
                channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                sample_rate = wf.getframerate()
                num_frames = wf.getnframes()
                raw_bytes = wf.readframes(num_frames)
        except Exception as e:
            return AudioValidationResult(
                file_path=wav_path,
                file_name=file_name,
                is_valid=False,
                status="REJECTED_TECHNICAL",
                sample_rate_hz=0,
                channels=0,
                bit_depth=0,
                duration_ms=0.0,
                rms_dbfs=-100.0,
                peak_dbfs=-100.0,
                estimated_snr_db=0.0,
                clipping_detected=False,
                dc_offset=0.0,
                lead_in_silence_ms=0.0,
                lead_out_silence_ms=0.0,
                failures=[f"Corrupted or invalid WAV header: {str(e)}"],
                warnings=[],
            )

        bit_depth = sample_width * 8
        duration_ms = (num_frames / float(sample_rate)) * 1000.0 if sample_rate > 0 else 0.0

        if channels != self.TARGET_CHANNELS:
            failures.append(f"Channel count {channels} != {self.TARGET_CHANNELS} (must be mono).")
        if sample_rate != self.TARGET_SAMPLE_RATE:
            failures.append(f"Sampling rate {sample_rate} != {self.TARGET_SAMPLE_RATE} Hz.")
        if bit_depth != self.TARGET_BIT_DEPTH:
            failures.append(f"Bit depth {bit_depth} != {self.TARGET_BIT_DEPTH} bit PCM.")

        if failures:
            # Fatal format mismatches prevent signal math
            return AudioValidationResult(
                file_path=wav_path,
                file_name=file_name,
                is_valid=False,
                status="REJECTED_TECHNICAL",
                sample_rate_hz=sample_rate,
                channels=channels,
                bit_depth=bit_depth,
                duration_ms=round(duration_ms, 2),
                rms_dbfs=-100.0,
                peak_dbfs=-100.0,
                estimated_snr_db=0.0,
                clipping_detected=False,
                dc_offset=0.0,
                lead_in_silence_ms=0.0,
                lead_out_silence_ms=0.0,
                failures=failures,
                warnings=warnings,
            )

        # 2. Convert PCM to Float32 [-1.0, +1.0]
        audio_int16 = np.frombuffer(raw_bytes, dtype=np.int16)
        if len(audio_int16) == 0:
            failures.append("Audio file contains 0 audio frames (empty stream).")
            return AudioValidationResult(
                file_path=wav_path,
                file_name=file_name,
                is_valid=False,
                status="REJECTED_TECHNICAL",
                sample_rate_hz=sample_rate,
                channels=channels,
                bit_depth=bit_depth,
                duration_ms=0.0,
                rms_dbfs=-100.0,
                peak_dbfs=-100.0,
                estimated_snr_db=0.0,
                clipping_detected=False,
                dc_offset=0.0,
                lead_in_silence_ms=0.0,
                lead_out_silence_ms=0.0,
                failures=failures,
                warnings=warnings,
            )

        audio = audio_int16.astype(np.float32) / 32768.0

        # 3. Peak Amplitude & Clipping Detection
        peak = float(np.max(np.abs(audio)))
        peak_dbfs = 20.0 * math.log10(peak) if peak > 1e-9 else -100.0

        # Check for saturated samples (clipped at +32767 or -32768)
        clipped_samples = int(np.sum((audio_int16 >= 32760) | (audio_int16 <= -32760)))
        clipping_detected = clipped_samples > 0 or peak_dbfs >= self.MAX_PEAK_DBFS
        if clipping_detected:
            failures.append(
                f"Clipping detected: peak {peak_dbfs:.2f} dBFS exceeds limit {self.MAX_PEAK_DBFS} dBFS "
                f"({clipped_samples} saturated samples)."
            )

        # 4. RMS Energy
        rms = float(np.sqrt(np.mean(audio**2)))
        rms_dbfs = 20.0 * math.log10(rms) if rms > 1e-9 else -100.0

        if is_background:
            if rms_dbfs < self.MIN_BG_RMS_DBFS:
                failures.append(f"Background energy {rms_dbfs:.2f} dBFS is too low (< {self.MIN_BG_RMS_DBFS} dBFS).")
            elif rms_dbfs > self.MAX_BG_RMS_DBFS:
                failures.append(f"Background energy {rms_dbfs:.2f} dBFS is too loud (> {self.MAX_BG_RMS_DBFS} dBFS).")
        else:
            if rms_dbfs < self.MIN_RMS_DBFS:
                failures.append(f"Audio energy {rms_dbfs:.2f} dBFS is too low (< {self.MIN_RMS_DBFS} dBFS).")
            elif rms_dbfs > self.MAX_RMS_DBFS:
                failures.append(f"Audio energy {rms_dbfs:.2f} dBFS is too loud (> {self.MAX_RMS_DBFS} dBFS).")

        # 5. Utterance Duration Limits
        max_dur = 60000.0 if is_background else self.MAX_DURATION_MS
        if duration_ms < self.MIN_DURATION_MS:
            failures.append(f"Utterance duration {duration_ms:.1f} ms < minimum {self.MIN_DURATION_MS} ms.")
        elif duration_ms > max_dur:
            failures.append(f"Utterance duration {duration_ms:.1f} ms > maximum {max_dur} ms.")

        # 6. DC Offset
        dc_offset = float(np.mean(audio))
        if abs(dc_offset) > self.MAX_DC_OFFSET:
            failures.append(f"DC offset {dc_offset:.4f} exceeds threshold {self.MAX_DC_OFFSET}.")

        # 7. Lead-in and Lead-out Silence (10ms frames)
        frame_size = int(0.010 * sample_rate)  # 160 samples
        frame_energies: List[float] = []
        for i in range(0, len(audio) - frame_size + 1, frame_size):
            pwr = float(np.mean(audio[i : i + frame_size] ** 2))
            frame_energies.append(pwr)

        noise_floor_pwr = np.percentile(frame_energies, 10) if frame_energies else 1e-9
        speech_pwr_thresh = max(1e-6, noise_floor_pwr * 4.0)

        lead_in_frames = 0
        for pwr in frame_energies:
            if pwr < speech_pwr_thresh:
                lead_in_frames += 1
            else:
                break
        lead_in_ms = lead_in_frames * 10.0

        lead_out_frames = 0
        for pwr in reversed(frame_energies):
            if pwr < speech_pwr_thresh:
                lead_out_frames += 1
            else:
                break
        lead_out_ms = lead_out_frames * 10.0

        if not is_background:
            if lead_in_ms < self.MIN_LEAD_IN_MS:
                failures.append(f"Lead-in silence {lead_in_ms:.1f} ms < {self.MIN_LEAD_IN_MS} ms (possible onset cutoff).")
            if lead_out_ms < self.MIN_LEAD_OUT_MS:
                failures.append(f"Lead-out silence {lead_out_ms:.1f} ms < {self.MIN_LEAD_OUT_MS} ms (possible offset cutoff).")

        # 8. Estimated SNR
        signal_pwr = float(np.percentile(frame_energies, 90)) if frame_energies else 1e-6
        snr_db = 10.0 * math.log10(signal_pwr / (noise_floor_pwr + 1e-12))
        if not is_background and snr_db < self.MIN_SNR_DB:
            failures.append(f"Estimated SNR {snr_db:.1f} dB is below minimum threshold {self.MIN_SNR_DB} dB.")

        is_valid = len(failures) == 0
        status = "PASSED" if is_valid else "REJECTED_TECHNICAL"

        return AudioValidationResult(
            file_path=wav_path,
            file_name=file_name,
            is_valid=is_valid,
            status=status,
            sample_rate_hz=sample_rate,
            channels=channels,
            bit_depth=bit_depth,
            duration_ms=round(duration_ms, 2),
            rms_dbfs=round(rms_dbfs, 2),
            peak_dbfs=round(peak_dbfs, 2),
            estimated_snr_db=round(snr_db, 2),
            clipping_detected=clipping_detected,
            dc_offset=round(dc_offset, 6),
            lead_in_silence_ms=round(lead_in_ms, 1),
            lead_out_silence_ms=round(lead_out_ms, 1),
            failures=failures,
            warnings=warnings,
        )

    def validate_batch(self, wav_paths: List[str]) -> Dict[str, Any]:
        """Validates an entire batch of audio files and outputs an audit summary."""
        results: List[AudioValidationResult] = []
        for p in wav_paths:
            res = self.validate_wav_file(p)
            results.append(res)

        total = len(results)
        passed = sum(1 for r in results if r.is_valid)
        rejected = total - passed

        return {
            "total_files": total,
            "passed_files": passed,
            "rejected_files": rejected,
            "pass_rate_pct": round((passed / total) * 100.0, 1) if total > 0 else 0.0,
            "results": [asdict(r) for r in results],
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Field Audio Quality Validator")
    parser.add_argument("input_path", help="Path to a WAV file or directory of WAV files")
    args = parser.parse_args()

    validator = FieldAudioValidator()
    if os.path.isfile(args.input_path):
        res = validator.validate_wav_file(args.input_path)
        print(json.dumps(asdict(res), indent=2))
    elif os.path.isdir(args.input_path):
        files = [os.path.join(args.input_path, f) for f in os.listdir(args.input_path) if f.endswith(".wav")]
        summary = validator.validate_batch(files)
        print(json.dumps(summary, indent=2))
    else:
        print(f"Error: {args.input_path} is neither a file nor a directory.")
        sys.exit(1)
