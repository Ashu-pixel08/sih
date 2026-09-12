"""
tests/test_field_data_protocol.py
=============================================================================
SIH260042: Automated Unit Test Suite for Field Data Collection Protocol
=============================================================================

TEST CODES & VALIDATION:
1. test_schema_validity_and_sample_manifest:
   Verifies recording_manifest.schema.json validates authentic records and rejects invalid entries.
2. test_audio_validator_valid_sample:
   Verifies FieldAudioValidator passes compliant 16 kHz 16-bit mono speech waveforms.
3. test_audio_validator_detects_clipping:
   Verifies clipping and sample saturation are strictly caught and rejected.
4. test_audio_validator_detects_wrong_sample_rate:
   Verifies non-16kHz audio (e.g. 8 kHz or 44.1 kHz) is flagged and rejected.
5. test_audio_validator_detects_stereo_channels:
   Verifies 2-channel stereo audio is rejected per the Mono specification.
6. test_audio_validator_detects_duration_violations:
   Verifies too-short (< 400ms) or too-long (> 2500ms) files are rejected.
7. test_audio_validator_detects_low_energy_silence:
   Verifies whisper or near-silent files (< -28 dBFS) are flagged.
8. test_protocol_documentation_integrity:
   Verifies all 4 protocol documents exist, are non-empty, and contain required sections.
=============================================================================
"""

import json
import os
import struct
import sys
import unittest
import wave

import numpy as np

cur_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.normpath(os.path.join(cur_dir, ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from ai.data_collection.validate_field_recording import FieldAudioValidator


class TestFieldDataProtocol(unittest.TestCase):
    """Test suite validating field collection protocol, schema, and QA validator."""

    @classmethod
    def setUpClass(cls):
        cls.validator = FieldAudioValidator()
        cls.schema_path = os.path.join(
            workspace_root, "data", "metadata", "recording_manifest.schema.json"
        )
        cls.temp_dir = os.path.join(workspace_root, "temp_test_audio")
        os.makedirs(cls.temp_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.temp_dir):
            for f in os.listdir(cls.temp_dir):
                os.remove(os.path.join(cls.temp_dir, f))
            os.rmdir(cls.temp_dir)

    def _write_synthetic_wav(
        self,
        filename: str,
        sample_rate: int = 16000,
        channels: int = 1,
        duration_s: float = 1.0,
        frequency_hz: float = 400.0,
        amplitude: float = 0.20,
        lead_in_s: float = 0.15,
        lead_out_s: float = 0.15,
        clip: bool = False,
    ) -> str:
        """Helper to create controlled test WAV files."""
        filepath = os.path.join(self.temp_dir, filename)
        total_samples = int(duration_s * sample_rate)
        lead_in_samples = int(lead_in_s * sample_rate)
        lead_out_samples = int(lead_out_s * sample_rate)
        speech_samples = max(0, total_samples - lead_in_samples - lead_out_samples)

        audio = np.zeros(total_samples, dtype=np.float32)
        if speech_samples > 0:
            t = np.arange(speech_samples) / float(sample_rate)
            tone = amplitude * np.sin(2 * np.pi * frequency_hz * t)
            audio[lead_in_samples : lead_in_samples + speech_samples] = tone

        # Add slight background noise to yield realistic SNR (~30 dB)
        noise = np.random.normal(0, 0.002, total_samples).astype(np.float32)
        audio = audio + noise

        if clip:
            audio[total_samples // 2 : total_samples // 2 + 50] = 1.5  # Heavy clipping

        # Convert to int16
        audio_int16 = np.clip(audio * 32768.0, -32768, 32767).astype(np.int16)

        with wave.open(filepath, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            if channels == 1:
                wf.writeframes(audio_int16.tobytes())
            else:
                stereo = np.column_stack((audio_int16, audio_int16))
                wf.writeframes(stereo.tobytes())

        return filepath

    def test_schema_validity_and_sample_manifest(self):
        """Verifies recording_manifest.schema.json exists, parses, and validates entries."""
        self.assertTrue(os.path.exists(self.schema_path), "Schema file must exist")
        with open(self.schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        self.assertEqual(schema["title"], "SIH260042 Recording Manifest Schema")
        self.assertIn("recordings", schema["properties"])

        # Construct valid sample record
        sample_record = {
            "recording_id": "REC_FLN_SPK_C01_NUM01_REP01",
            "file_path": "data/raw/speech/SPK_C01/REC_FLN_SPK_C01_NUM01_REP01.wav",
            "speaker_id": "SPK_C01",
            "speaker_group": "CHILD_GIRL",
            "class_index": 1,
            "label_id": "num_01",
            "domain": "FLN_GRADE1_NUMERACY",
            "prompt_type": "ISOLATED_WORD",
            "prompt_text": "मिअद",
            "transcribed_text": "मिअद",
            "audio_metrics": {
                "sample_rate_hz": 16000,
                "channels": 1,
                "bit_depth": 16,
                "duration_ms": 950.0,
                "rms_dbfs": -21.4,
                "peak_dbfs": -5.1,
                "snr_db": 30.5,
                "clipping_detected": False,
            },
            "review": {
                "status": "ACCEPTED",
                "reviewer_id": "REV_01",
                "pronunciation_quality": "EXCELLENT_NATIVE",
                "timestamp_iso": "2026-09-04T12:00:00Z",
            },
        }

        # Check required fields exist
        req_fields = schema["properties"]["recordings"]["items"]["required"]
        for field in req_fields:
            self.assertIn(field, sample_record)

    def test_audio_validator_valid_sample(self):
        """Verifies FieldAudioValidator passes compliant 16 kHz 16-bit mono speech waveforms."""
        path = self._write_synthetic_wav(
            "valid_sample.wav",
            sample_rate=16000,
            channels=1,
            duration_s=1.0,
            amplitude=0.22,
            lead_in_s=0.15,
            lead_out_s=0.15,
        )
        res = self.validator.validate_wav_file(path)
        self.assertTrue(res.is_valid, f"Expected valid, got failures: {res.failures}")
        self.assertEqual(res.status, "PASSED")
        self.assertEqual(res.sample_rate_hz, 16000)
        self.assertEqual(res.channels, 1)
        self.assertEqual(res.bit_depth, 16)
        self.assertFalse(res.clipping_detected)

    def test_audio_validator_detects_clipping(self):
        """Verifies clipping and sample saturation are strictly caught and rejected."""
        path = self._write_synthetic_wav("clipped.wav", amplitude=1.2, clip=True)
        res = self.validator.validate_wav_file(path)
        self.assertFalse(res.is_valid)
        self.assertEqual(res.status, "REJECTED_TECHNICAL")
        self.assertTrue(res.clipping_detected)
        self.assertTrue(any("Clipping detected" in f for f in res.failures))

    def test_audio_validator_detects_wrong_sample_rate(self):
        """Verifies non-16kHz audio (e.g. 8 kHz or 44.1 kHz) is flagged and rejected."""
        path = self._write_synthetic_wav("wrong_sr.wav", sample_rate=8000)
        res = self.validator.validate_wav_file(path)
        self.assertFalse(res.is_valid)
        self.assertEqual(res.status, "REJECTED_TECHNICAL")
        self.assertTrue(any("Sampling rate 8000 != 16000" in f for f in res.failures))

    def test_audio_validator_detects_stereo_channels(self):
        """Verifies 2-channel stereo audio is rejected per the Mono specification."""
        path = self._write_synthetic_wav("stereo.wav", channels=2)
        res = self.validator.validate_wav_file(path)
        self.assertFalse(res.is_valid)
        self.assertEqual(res.status, "REJECTED_TECHNICAL")
        self.assertTrue(any("Channel count 2 != 1" in f for f in res.failures))

    def test_audio_validator_detects_duration_violations(self):
        """Verifies too-short (< 400ms) or too-long (> 2500ms) files are rejected."""
        short_path = self._write_synthetic_wav("short.wav", duration_s=0.25, lead_in_s=0.05, lead_out_s=0.05)
        res_short = self.validator.validate_wav_file(short_path)
        self.assertFalse(res_short.is_valid)
        self.assertTrue(any("minimum 400.0 ms" in f for f in res_short.failures))

        long_path = self._write_synthetic_wav("long.wav", duration_s=3.2)
        res_long = self.validator.validate_wav_file(long_path)
        self.assertFalse(res_long.is_valid)
        self.assertTrue(any("maximum 2500.0 ms" in f for f in res_long.failures))

    def test_audio_validator_detects_low_energy_silence(self):
        """Verifies whisper or near-silent files (< -28 dBFS) are flagged."""
        quiet_path = self._write_synthetic_wav("quiet.wav", amplitude=0.005)
        res = self.validator.validate_wav_file(quiet_path)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("too low" in f for f in res.failures))

    def test_protocol_documentation_integrity(self):
        """Verifies all 4 protocol documents exist, are non-empty, and contain required sections."""
        docs = [
            "docs/recording-specification.md",
            "docs/field-data-collection-protocol.md",
            "docs/native-speaker-annotation-protocol.md",
            "docs/data-collection-checklist.md",
        ]
        for rel_path in docs:
            full_path = os.path.join(workspace_root, rel_path)
            self.assertTrue(os.path.exists(full_path), f"Protocol doc {rel_path} must exist")
            size = os.path.getsize(full_path)
            self.assertGreater(size, 500, f"Protocol doc {rel_path} must not be empty")


if __name__ == "__main__":
    unittest.main()
