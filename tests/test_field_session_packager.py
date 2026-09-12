"""
tests/test_field_session_packager.py
=============================================================================
SIH260042: Unit Tests for Field Data Intake Tooling & Session Packager
=============================================================================

TEST CODES & SPECIFICATIONS:
1. test_valid_session_creation:
   Verifies directory layout, session_config.json creation, and initialization state.
2. test_anonymized_speaker_registration_and_pii_rejection:
   Verifies valid speaker registration and strict rejection of invalid formats or PII.
3. test_valid_recording_ingestion_and_raw_processed_separation:
   Verifies raw WAV is stored in raw_recordings/ and QA-passed file in processed/accepted/.
4. test_invalid_recording_rejection_and_quarantine:
   Verifies clipped/defective audio is rejected and placed in processed/rejected/.
5. test_duplicate_recording_detection:
   Verifies attempting to ingest the same take twice raises DuplicateRecordingError.
6. test_missing_metadata_handling:
   Verifies unregistered speakers and unknown targets raise appropriate errors.
7. test_human_linguistic_review_recording:
   Verifies linguistic review updates status and prevents automated validation claims.
8. test_manifest_generation_and_schema_conformance:
   Verifies generated recording_manifest.json strictly satisfies recording_manifest.schema.json.
9. test_speaker_disjoint_partitioning_and_leakage_audit:
   Verifies zero speaker overlap across train/val/test splits.
10. test_coverage_matrix_report_generation:
    Verifies Speaker x Target coverage matrix and demographic summary.
11. test_packaging_reproducibility_and_checksums:
    Verifies creation of .tar.gz bundle, checksums.sha256 calculation, and session receipt.
=============================================================================
"""

import hashlib
import json
import os
import shutil
import sys
import tarfile
import unittest
import wave

import numpy as np

cur_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.normpath(os.path.join(cur_dir, ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from ai.data_collection.field_session_packager import (
    AnonymizationError,
    DuplicateRecordingError,
    FieldSessionPackager,
    TargetLookupError,
)
from ai.data_collection.mock_ingest_field_session import (
    DataLeakageError,
    validate_manifest_schema_dict,
)


class TestFieldSessionPackager(unittest.TestCase):
    """Test suite validating FieldSessionPackager offline field toolkit."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = os.path.join(workspace_root, "data", "processed", "test_field_packager_session")
        cls.audio_source_dir = os.path.join(workspace_root, "data", "processed", "test_temp_audio_sources")
        cls.schema_path = os.path.join(workspace_root, "data", "metadata", "recording_manifest.schema.json")
        os.makedirs(cls.test_dir, exist_ok=True)
        os.makedirs(cls.audio_source_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir, ignore_errors=True)
        if os.path.exists(cls.audio_source_dir):
            shutil.rmtree(cls.audio_source_dir, ignore_errors=True)

    def setUp(self):
        # Fresh packager per test
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)
        self.packager = FieldSessionPackager(self.test_dir, workspace_root)
        self.packager.init_session(
            session_id="SESS_20260904_TEST_01",
            location="Khunti Test School",
            recorder_id="TEST_RECORDER_01",
        )

    def _create_wav(
        self,
        filename: str,
        sample_rate: int = 16000,
        channels: int = 1,
        duration_s: float = 1.0,
        amplitude: float = 0.22,
        clip: bool = False,
    ) -> str:
        """Helper to create dummy audio source file."""
        filepath = os.path.join(self.audio_source_dir, filename)
        total_samples = int(duration_s * sample_rate)
        lead_in = int(0.15 * sample_rate)
        lead_out = int(0.15 * sample_rate)
        speech_len = max(0, total_samples - lead_in - lead_out)

        audio = np.zeros(total_samples, dtype=np.float32)
        if speech_len > 0:
            t = np.arange(speech_len) / float(sample_rate)
            tone = amplitude * np.sin(2 * np.pi * 300.0 * t)
            audio[lead_in : lead_in + speech_len] = tone

        noise = np.random.normal(0, 0.002, total_samples).astype(np.float32)
        audio = audio + noise

        if clip:
            audio[total_samples // 2 : total_samples // 2 + 100] = 1.8

        audio_int16 = np.clip(audio * 32768.0, -32768, 32767).astype(np.int16)

        with wave.open(filepath, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            if channels == 1:
                wf.writeframes(audio_int16.tobytes())
            else:
                stereo = np.column_stack((audio_int16, audio_int16))
                wf.writeframes(stereo.tobytes())

        return filepath

    def test_valid_session_creation(self):
        """Verifies session layout and config creation."""
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "session_config.json")))
        self.assertTrue(os.path.exists(self.packager.raw_dir))
        self.assertTrue(os.path.exists(self.packager.accepted_dir))
        self.assertTrue(os.path.exists(self.packager.rejected_dir))
        self.assertTrue(os.path.exists(self.packager.metadata_dir))

        with open(os.path.join(self.test_dir, "session_config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertEqual(cfg["session_id"], "SESS_20260904_TEST_01")
        self.assertEqual(cfg["status"], "ACTIVE_RECORDING")

    def test_anonymized_speaker_registration_and_pii_rejection(self):
        """Verifies anonymized IDs are accepted and PII is strictly rejected."""
        # 1. Valid registration
        spk = self.packager.register_speaker("SPK_C01", "CHILD_GIRL", age=7, dialect_region="Naguri (Khunti)")
        self.assertEqual(spk["speaker_id"], "SPK_C01")
        self.assertEqual(spk["speaker_group"], "CHILD_GIRL")

        # 2. Invalid ID format
        with self.assertRaises(AnonymizationError):
            self.packager.register_speaker("John_Doe", "CHILD_BOY")  # Not SPK_[FMC]xx

        with self.assertRaises(AnonymizationError):
            self.packager.register_speaker("STUDENT_12", "CHILD_GIRL")

        # 3. PII injection attempt
        with self.assertRaises(AnonymizationError):
            self.packager.register_speaker("SPK_C02", "CHILD_GIRL", pii_metadata={"name": "Sita Munda", "roll_no": 14})

    def test_valid_recording_ingestion_and_raw_processed_separation(self):
        """Verifies raw audio is saved in raw/ and accepted file in processed/accepted/."""
        self.packager.register_speaker("SPK_C01", "CHILD_GIRL", age=7)
        wav_path = self._create_wav("clean_take.wav")

        res = self.packager.ingest_audio_take(
            wav_source_path=wav_path,
            speaker_id="SPK_C01",
            target_id="num_01",
            repetition=1,
        )

        self.assertEqual(res["technical_validation"]["status"], "PASSED_TECHNICAL")
        self.assertTrue(res["technical_validation"]["is_valid"])

        # Check raw separation
        expected_name = f"{res['recording_id']}.wav"
        raw_file = os.path.join(self.packager.raw_dir, expected_name)
        accepted_file = os.path.join(self.packager.accepted_dir, expected_name)
        rejected_file = os.path.join(self.packager.rejected_dir, expected_name)

        self.assertTrue(os.path.exists(raw_file), "Raw file must exist in raw_recordings/")
        self.assertTrue(os.path.exists(accepted_file), "Accepted file must exist in processed_recordings/accepted/")
        self.assertFalse(os.path.exists(rejected_file), "Accepted file must NOT exist in processed_recordings/rejected/")

    def test_invalid_recording_rejection_and_quarantine(self):
        """Verifies defective takes are rejected and quarantined into processed/rejected/."""
        self.packager.register_speaker("SPK_C01", "CHILD_GIRL", age=7)
        clipped_wav = self._create_wav("clipped_take.wav", clip=True)

        res = self.packager.ingest_audio_take(
            wav_source_path=clipped_wav,
            speaker_id="SPK_C01",
            target_id="num_02",
            repetition=1,
        )

        self.assertEqual(res["technical_validation"]["status"], "REJECTED_TECHNICAL")
        self.assertFalse(res["technical_validation"]["is_valid"])
        self.assertTrue(res["audio_metrics"]["clipping_detected"])

        expected_name = f"{res['recording_id']}.wav"
        raw_file = os.path.join(self.packager.raw_dir, expected_name)
        accepted_file = os.path.join(self.packager.accepted_dir, expected_name)
        rejected_file = os.path.join(self.packager.rejected_dir, expected_name)

        self.assertTrue(os.path.exists(raw_file), "Raw file must exist")
        self.assertFalse(os.path.exists(accepted_file), "Rejected file must NOT exist in accepted/")
        self.assertTrue(os.path.exists(rejected_file), "Rejected file MUST exist in rejected/")

    def test_duplicate_recording_detection(self):
        """Verifies ingesting identical take raises DuplicateRecordingError."""
        self.packager.register_speaker("SPK_C01", "CHILD_GIRL", age=7)
        wav_path = self._create_wav("take1.wav")

        self.packager.ingest_audio_take(wav_path, "SPK_C01", "num_01", repetition=1)

        with self.assertRaises(DuplicateRecordingError):
            self.packager.ingest_audio_take(wav_path, "SPK_C01", "num_01", repetition=1, allow_overwrite=False)

    def test_missing_metadata_handling(self):
        """Verifies unregistered speakers and unknown targets raise errors."""
        wav_path = self._create_wav("test.wav")

        # Unregistered speaker
        with self.assertRaises(AnonymizationError):
            self.packager.ingest_audio_take(wav_path, "SPK_UNREGISTERED_99", "num_01")

        # Registered speaker but invalid target
        self.packager.register_speaker("SPK_C01", "CHILD_GIRL")
        with self.assertRaises(TargetLookupError):
            self.packager.ingest_audio_take(wav_path, "SPK_C01", "non_existent_target_999")

    def test_human_linguistic_review_recording(self):
        """Verifies linguistic review updates status and prevents automated verification claims."""
        self.packager.register_speaker("SPK_C01", "CHILD_GIRL")
        wav = self._create_wav("take.wav")
        rec = self.packager.ingest_audio_take(wav, "SPK_C01", "num_01")

        # Initial status is UNREVIEWED
        self.assertEqual(rec["linguistic_review"]["status"], "UNREVIEWED")

        # Record human review
        updated = self.packager.record_linguistic_review(
            recording_id=rec["recording_id"],
            reviewer_id="REV_MUNDARI_01",
            linguistic_status="ACCEPTED",
            pronunciation_quality="EXCELLENT_NATIVE",
            reviewer_role="Native Mundari Primary Educator (Khunti)",
            notes="Accurate pronunciation of numeral 1 (miad).",
        )

        self.assertEqual(updated["linguistic_review"]["status"], "ACCEPTED")
        self.assertEqual(updated["linguistic_review"]["reviewer_id"], "REV_MUNDARI_01")

    def test_manifest_generation_and_schema_conformance(self):
        """Verifies generated recording_manifest.json conforms to schema."""
        self.packager.register_speaker("SPK_C01", "CHILD_GIRL")
        wav = self._create_wav("take.wav")
        rec = self.packager.ingest_audio_take(wav, "SPK_C01", "num_01")
        self.packager.record_linguistic_review(rec["recording_id"], "REV_01", "ACCEPTED", "EXCELLENT_NATIVE")

        manifest = self.packager.generate_manifest()
        errors = validate_manifest_schema_dict(manifest, self.schema_path)
        self.assertEqual(len(errors), 0, f"Manifest failed schema: {errors}")
        self.assertEqual(manifest["total_recordings"], 1)
        self.assertEqual(manifest["summary"]["accepted_count"], 1)

    def test_speaker_disjoint_partitioning_and_leakage_audit(self):
        """Verifies speaker-disjoint splits and leakage check in field session."""
        # Register 3 speakers
        self.packager.register_speaker("SPK_C01", "CHILD_GIRL")
        self.packager.register_speaker("SPK_C02", "CHILD_BOY")
        self.packager.register_speaker("SPK_F01", "ADULT_FEMALE")

        wav = self._create_wav("take.wav")
        r1 = self.packager.ingest_audio_take(wav, "SPK_C01", "num_01")
        r2 = self.packager.ingest_audio_take(wav, "SPK_C02", "num_01")
        r3 = self.packager.ingest_audio_take(wav, "SPK_F01", "num_01")

        self.packager.record_linguistic_review(r1["recording_id"], "REV_01", "ACCEPTED", "EXCELLENT_NATIVE")
        self.packager.record_linguistic_review(r2["recording_id"], "REV_01", "ACCEPTED", "EXCELLENT_NATIVE")
        self.packager.record_linguistic_review(r3["recording_id"], "REV_01", "ACCEPTED", "EXCELLENT_NATIVE")

        splits_meta = self.packager.generate_speaker_disjoint_splits()
        leakage = splits_meta["leakage_results"]

        self.assertIn("PASS", leakage["speaker_leakage"])
        self.assertIn("PASS", leakage["recording_leakage"])
        self.assertIn("PASS", leakage["file_leakage"])

    def test_coverage_matrix_report_generation(self):
        """Verifies progress matrix generates visual Speaker x Target grid."""
        self.packager.register_speaker("SPK_C01", "CHILD_GIRL")
        wav = self._create_wav("take.wav")
        r1 = self.packager.ingest_audio_take(wav, "SPK_C01", "num_01")
        self.packager.record_linguistic_review(r1["recording_id"], "REV_01", "ACCEPTED", "EXCELLENT_NATIVE")

        report = self.packager.generate_coverage_matrix_report()
        self.assertEqual(report["total_speakers_registered"], 1)
        self.assertEqual(report["accepted_takes"], 1)
        self.assertIn("Target / Class", report["coverage_matrix_text"])
        self.assertIn("SPK_C01", report["coverage_matrix_text"])
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "coverage_report.md")))

    def test_packaging_reproducibility_and_checksums(self):
        """Verifies portable .tar.gz bundle creation and checksums.sha256 calculation."""
        self.packager.register_speaker("SPK_C01", "CHILD_GIRL")
        wav = self._create_wav("take.wav")
        r1 = self.packager.ingest_audio_take(wav, "SPK_C01", "num_01")
        self.packager.record_linguistic_review(r1["recording_id"], "REV_01", "ACCEPTED", "EXCELLENT_NATIVE")

        receipt = self.packager.package_session()
        archive_path = receipt["archive_path"]

        self.assertTrue(os.path.exists(archive_path), "Archive file must exist")
        self.assertGreater(receipt["archive_size_mb"], 0.0)
        self.assertTrue(receipt["integrity_verified"])

        # Verify tar archive contents
        with tarfile.open(archive_path, "r:gz") as tar:
            members = tar.getnames()
            session_name = os.path.basename(self.test_dir)
            self.assertIn(f"{session_name}/checksums.sha256", members)
            self.assertIn(f"{session_name}/metadata/recording_manifest.json", members)
            self.assertIn(f"{session_name}/splits/session_splits.json", members)


if __name__ == "__main__":
    unittest.main()
