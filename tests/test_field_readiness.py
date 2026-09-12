"""
tests/test_field_readiness.py
=============================================================================
SIH260042: Unit Tests for Pre-Field Collection Readiness Auditor
=============================================================================

PURPOSE:
- Validates that the pre-field readiness auditor accurately evaluates:
  1. Complete pre-field readiness of target catalogs, schemas, docs, and tooling.
  2. Strict preservation of data limitations (MISSING, UNVERIFIED, PENDING).
  3. Detection of missing schemas, corrupted files, or missing classes as blocking errors.
  4. Incoming session bundle verification (.tar.gz extraction, SHA-256, schema validation).
  5. Detection of corrupted/tampered files inside an incoming field bundle.
=============================================================================
"""

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

from ai.data_collection.check_field_readiness import FieldReadinessAuditor
from ai.data_collection.field_session_packager import FieldSessionPackager


class TestFieldReadinessAuditor(unittest.TestCase):
    """Test suite validating pre-field data collection readiness auditor."""

    @classmethod
    def setUpClass(cls):
        cls.auditor = FieldReadinessAuditor(workspace_root)
        cls.test_sandbox = os.path.join(workspace_root, "data", "processed", "test_readiness_sandbox")
        os.makedirs(cls.test_sandbox, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_sandbox):
            shutil.rmtree(cls.test_sandbox, ignore_errors=True)

    def test_pre_field_readiness_audit_passes(self):
        """Verifies the live codebase passes all 10 pre-field audit points."""
        report = self.auditor.run_pre_field_audit()

        self.assertEqual(report.overall_readiness, "READY_TO_RECEIVE_FIELD_DATA")
        self.assertEqual(len(report.blocking_errors), 0, f"Unexpected blocking errors: {report.blocking_errors}")
        self.assertEqual(report.target_catalog_status, "PASSED")
        self.assertEqual(report.total_canonical_classes, 21)
        self.assertEqual(len(report.missing_classes), 0)
        self.assertEqual(report.qa_validator_status, "OPERATIONAL")
        self.assertEqual(report.schema_status, "VALID")
        self.assertEqual(report.packaging_tool_status, "OPERATIONAL")

    def test_honest_data_limitation_reporting(self):
        """Verifies honest status labeling: real audio MISSING, accuracy UNVERIFIED."""
        report = self.auditor.run_pre_field_audit()

        self.assertEqual(report.real_audio_status, "MISSING")
        self.assertEqual(report.speech_accuracy_status, "UNVERIFIED")
        self.assertEqual(report.native_verification_status, "PENDING")
        self.assertEqual(report.current_real_recordings_count, 0)
        self.assertEqual(report.current_native_speakers_count, 0)

    def test_inspect_session_bundle_validation(self):
        """Verifies inspect_session_bundle passes on a validly created field package."""
        session_dir = os.path.join(self.test_sandbox, "valid_session")
        packager = FieldSessionPackager(session_dir, workspace_root)
        packager.init_session("SESS_READINESS_01", "Murhu Primary School", "REC_01")
        packager.register_speaker("SPK_C01", "CHILD_GIRL", age=7)

        # Generate simple valid audio
        wav_path = os.path.join(self.test_sandbox, "sample.wav")
        total_samples = 16000
        audio = (0.22 * np.sin(2 * np.pi * 300.0 * np.linspace(0, 1.0, total_samples)) * 32767).astype(np.int16)
        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(audio.tobytes())

        rec = packager.ingest_audio_take(wav_path, "SPK_C01", "num_01")
        packager.record_linguistic_review(rec["recording_id"], "REV_01", "ACCEPTED", "EXCELLENT_NATIVE")

        receipt = packager.package_session()
        archive_path = receipt["archive_path"]

        # Now test auditor inspection
        res = self.auditor.inspect_session_bundle(archive_path)
        self.assertTrue(res["is_valid"], f"Inspection failed: {res.get('errors')}")
        self.assertEqual(len(res["errors"]), 0)

    def test_inspect_session_bundle_catches_tampered_file(self):
        """Verifies inspect_session_bundle detects SHA-256 mismatch when a file is modified."""
        session_dir = os.path.join(self.test_sandbox, "tamper_session")
        packager = FieldSessionPackager(session_dir, workspace_root)
        packager.init_session("SESS_TAMPER_01", "Murhu Primary School", "REC_01")
        packager.register_speaker("SPK_C01", "CHILD_GIRL", age=7)

        wav_path = os.path.join(self.test_sandbox, "sample2.wav")
        audio = (0.22 * np.sin(2 * np.pi * 300.0 * np.linspace(0, 1.0, 16000)) * 32767).astype(np.int16)
        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(audio.tobytes())

        rec = packager.ingest_audio_take(wav_path, "SPK_C01", "num_01")
        packager.record_linguistic_review(rec["recording_id"], "REV_01", "ACCEPTED", "EXCELLENT_NATIVE")

        receipt = packager.package_session()
        archive_path = receipt["archive_path"]

        # Tamper: extract, modify a file, and re-archive
        tamper_dir = os.path.join(self.test_sandbox, "tamper_extract")
        os.makedirs(tamper_dir, exist_ok=True)
        with tarfile.open(archive_path, "r:gz") as tar:
            if hasattr(tarfile, "data_filter"):
                tar.extractall(tamper_dir, filter="data")
            else:
                tar.extractall(tamper_dir)

        # Append corrupted byte to config
        cfg_p = os.path.join(tamper_dir, os.listdir(tamper_dir)[0], "session_config.json")
        with open(cfg_p, "a", encoding="utf-8") as fp:
            fp.write("/* TAMPERED */")

        # Re-pack with the modified file
        tampered_archive = os.path.join(self.test_sandbox, "tampered_bundle.tar.gz")
        with tarfile.open(tampered_archive, "w:gz") as tar:
            for item in os.listdir(tamper_dir):
                tar.add(os.path.join(tamper_dir, item), arcname=item)

        # Inspect tampered bundle
        res = self.auditor.inspect_session_bundle(tampered_archive)
        self.assertFalse(res["is_valid"], "Tampered archive must fail validation")
        self.assertTrue(any("SHA-256 mismatch" in err for err in res["errors"]))


if __name__ == "__main__":
    unittest.main()
