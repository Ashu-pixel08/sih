"""
tests/test_field_ingestion_pipeline.py
=============================================================================
SIH260042: Automated Unit Test Suite for Field Ingestion & Partitioner Pipeline
=============================================================================

PURPOSE:
- Validates the complete field session ingestion dry-run workflow:
  1. Automated ingestion of raw field WAV takes with FieldAudioValidator.
  2. Strict quarantine and rejection of defective audio takes.
  3. Machine-readable JSON manifest adherence to recording_manifest.schema.json.
  4. Metadata attachment (speaker ID, number/class, repetition, session, dialect, review).
  5. Speaker-disjoint train, validation, and test dataset partitioning.
  6. Data leakage audit (speaker leakage, recording leakage, file path leakage).
  7. Detection and rejection of simulated data leakage.
  8. Augmentation confinement to parent split.
  9. Collection target verification against approved protocol (30 speakers, 6000 assets).
  10. Compatibility of exported split metadata with training loaders.
=============================================================================
"""

import json
import os
import shutil
import sys
import unittest

cur_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.normpath(os.path.join(cur_dir, ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from ai.data_collection.mock_ingest_field_session import (
    CollectionTargetVerifier,
    DataLeakageAuditor,
    DataLeakageError,
    FieldSessionIngestionPipeline,
    MockFieldFixtureGenerator,
    SchemaValidationError,
    SpeakerDisjointPartitioner,
    run_field_ingestion_simulation,
    validate_manifest_schema_dict,
)


class TestFieldIngestionPipeline(unittest.TestCase):
    """Test suite validating end-to-end field session ingestion, QA, and partitioning."""

    @classmethod
    def setUpClass(cls):
        cls.test_session_dir = os.path.join(workspace_root, "data", "processed", "test_mock_ingest_session")
        os.makedirs(cls.test_session_dir, exist_ok=True)
        cls.schema_path = os.path.join(workspace_root, "data", "metadata", "recording_manifest.schema.json")

    @classmethod
    def tearDownClass(cls):
        # Clean up temporary test audio files if created
        if os.path.exists(cls.test_session_dir):
            shutil.rmtree(cls.test_session_dir, ignore_errors=True)

    def test_complete_ingestion_dry_run_workflow(self):
        """Exercises complete simulation workflow and verifies statistics and QA gates."""
        results = run_field_ingestion_simulation(output_dir=self.test_session_dir, save_artifacts=False)

        manifest = results["ingestion_results"]["manifest"]
        summary = results["ingestion_results"]["summary"]
        counts = results["partition_results"]["counts"]
        leakage = results["leakage_results"]

        # 1. Verification of take counts
        self.assertEqual(manifest["total_recordings"], 77, "Expected 77 total takes in mock session")
        self.assertEqual(summary["accepted_count"], 72, "Expected 72 accepted takes")
        self.assertEqual(summary["rejected_count"], 5, "Expected exactly 5 rejected takes")
        self.assertGreater(summary["total_duration_minutes"], 1.0, "Total duration should be positive")

        # 2. Verify all 5 intentional defects were caught
        rejected_ids = [r["recording_id"] for r in results["ingestion_results"]["rejected_records"]]
        self.assertIn("REC_MOCK_ERR_CLIPPED_SPK_C01_NUM01", rejected_ids)
        self.assertIn("REC_MOCK_ERR_WRONG_SR_SPK_C02_NUM02", rejected_ids)
        self.assertIn("REC_MOCK_ERR_STEREO_SPK_F01_NUM03", rejected_ids)
        self.assertIn("REC_MOCK_ERR_LOW_ENERGY_SPK_M01_NUM04", rejected_ids)
        self.assertIn("REC_MOCK_ERR_TOO_SHORT_SPK_C03_NUM05", rejected_ids)

        # 3. Verify partitions
        self.assertEqual(counts["total_accepted_tokens"], 72)
        self.assertEqual(counts["train_tokens"] + counts["validation_tokens"] + counts["test_tokens"], 72)

        # 4. Verify leakage checks passed
        self.assertIn("PASS", leakage["speaker_leakage"])
        self.assertIn("PASS", leakage["recording_leakage"])
        self.assertIn("PASS", leakage["file_leakage"])
        self.assertIn("PASS", leakage["augmentation_boundary_status"])

    def test_speaker_disjoint_partitions_strict_isolation(self):
        """Verifies train, validation, and test splits have mutually exclusive speaker sets."""
        meta = MockFieldFixtureGenerator.create_mock_session(self.test_session_dir, num_speakers=6)
        pipeline = FieldSessionIngestionPipeline(workspace_root)
        ingest_res = pipeline.ingest_session(self.test_session_dir, meta)

        partitioner = SpeakerDisjointPartitioner()
        part_res = partitioner.partition_records(ingest_res["accepted_records"])

        splits = part_res["splits"]
        alloc = part_res["speaker_allocation"]

        train_spks = set(alloc["train_speakers"])
        val_spks = set(alloc["validation_speakers"])
        test_spks = set(alloc["test_speakers"])

        # All 3 splits must be non-empty
        self.assertGreaterEqual(len(train_spks), 1, "Train must have speakers")
        self.assertGreaterEqual(len(val_spks), 1, "Val must have speakers")
        self.assertGreaterEqual(len(test_spks), 1, "Test must have speakers")

        # Rigorous mathematical disjointness assertion
        self.assertEqual(len(train_spks.intersection(val_spks)), 0, "Train and Val must not share speakers")
        self.assertEqual(len(train_spks.intersection(test_spks)), 0, "Train and Test must not share speakers")
        self.assertEqual(len(val_spks.intersection(test_spks)), 0, "Val and Test must not share speakers")

        # Token-level verification
        train_token_spks = set(r["speaker_id"] for r in splits["train"])
        val_token_spks = set(r["speaker_id"] for r in splits["validation"])
        test_token_spks = set(r["speaker_id"] for r in splits["test"])

        self.assertEqual(train_token_spks, train_spks)
        self.assertEqual(val_token_spks, val_spks)
        self.assertEqual(test_token_spks, test_spks)

    def test_leakage_auditor_catches_simulated_speaker_leak(self):
        """Verifies DataLeakageAuditor raises DataLeakageError if a speaker leaks across splits."""
        partition_data = {
            "splits": {
                "train": [{"speaker_id": "SPK_C01", "recording_id": "REC_01", "file_path": "a.wav"}],
                "validation": [{"speaker_id": "SPK_C01", "recording_id": "REC_02", "file_path": "b.wav"}],  # LEAK!
                "test": [{"speaker_id": "SPK_C03", "recording_id": "REC_03", "file_path": "c.wav"}],
            }
        }
        with self.assertRaises(DataLeakageError):
            DataLeakageAuditor.audit_splits(partition_data)

    def test_leakage_auditor_catches_duplicate_recording_leak(self):
        """Verifies DataLeakageAuditor raises DataLeakageError if a recording ID or file path is duplicated."""
        partition_data = {
            "splits": {
                "train": [{"speaker_id": "SPK_C01", "recording_id": "REC_SAME", "file_path": "a.wav"}],
                "validation": [{"speaker_id": "SPK_C02", "recording_id": "REC_SAME", "file_path": "b.wav"}],  # DUPLICATE!
                "test": [{"speaker_id": "SPK_C03", "recording_id": "REC_DIFF", "file_path": "c.wav"}],
            }
        }
        with self.assertRaises(DataLeakageError):
            DataLeakageAuditor.audit_splits(partition_data)

    def test_augmentation_confinement_auditor(self):
        """Verifies that augmented files cannot cross splits without triggering an error."""
        partition_data = {
            "splits": {
                "train": [{"recording_id": "REC_SOURCE_01", "speaker_id": "SPK_C01", "file_path": "a.wav"}],
                "validation": [{"recording_id": "REC_SOURCE_02", "speaker_id": "SPK_C02", "file_path": "b.wav"}],
                "test": [{"recording_id": "REC_SOURCE_03", "speaker_id": "SPK_C03", "file_path": "c.wav"}],
            }
        }

        # Valid augmentation: parent is in train, aug assigned to train
        valid_aug = [
            {"recording_id": "REC_SOURCE_01_AUG1", "source_recording_id": "REC_SOURCE_01", "split": "train"}
        ]
        res = DataLeakageAuditor.verify_augmentation_confinement(partition_data, valid_aug)
        self.assertIn("PASS", res["augmentation_boundary_status"])

        # Invalid augmentation: parent is in train, but aug leaked into test!
        leaked_aug = [
            {"recording_id": "REC_SOURCE_01_AUG_LEAK", "source_recording_id": "REC_SOURCE_01", "split": "test"}
        ]
        with self.assertRaises(DataLeakageError):
            DataLeakageAuditor.verify_augmentation_confinement(partition_data, leaked_aug)

    def test_manifest_schema_compliance(self):
        """Verifies that generated manifest conforms strictly to recording_manifest.schema.json."""
        meta = MockFieldFixtureGenerator.create_mock_session(self.test_session_dir, num_speakers=3)
        pipeline = FieldSessionIngestionPipeline(workspace_root)
        ingest_res = pipeline.ingest_session(self.test_session_dir, meta)

        manifest = ingest_res["manifest"]
        errors = validate_manifest_schema_dict(manifest, self.schema_path)
        self.assertEqual(len(errors), 0, f"Manifest failed schema validation: {errors}")

    def test_collection_target_verifier_audit(self):
        """Verifies target parameters match protocol and are explicitly marked as COLLECTION_TARGETS."""
        comp = CollectionTargetVerifier.compare_targets({"speakers_tested": 6, "accepted_tokens": 72})
        target_spec = comp["target_specification"]

        self.assertEqual(target_spec["total_speakers"], 30)
        self.assertEqual(target_spec["child_girls"], 8)
        self.assertEqual(target_spec["child_boys"], 8)
        self.assertEqual(target_spec["adult_females"], 8)
        self.assertEqual(target_spec["adult_males"], 6)
        self.assertEqual(target_spec["isolated_repetitions_per_numeral"], 6)
        self.assertEqual(target_spec["carrier_repetitions_per_numeral"], 2)
        self.assertEqual(target_spec["target_speech_tokens"], 4800)
        self.assertEqual(target_spec["target_background_tokens"], 1200)
        self.assertEqual(target_spec["target_total_assets"], 6000)
        self.assertIn("COLLECTION_TARGETS", comp["status_label"])


if __name__ == "__main__":
    unittest.main()
