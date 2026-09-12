import os
import json
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CANONICAL_PATH = os.path.join(BASE_DIR, "content", "translations", "canonical_numbers_1_20.json")
REGISTRY_PATH = os.path.join(BASE_DIR, "content", "content_registry.json")


class TestContentRegistry(unittest.TestCase):

    def test_files_exist_and_are_valid_json(self):
        """Verify that both canonical dataset and registry JSON files exist and parse cleanly."""
        self.assertTrue(os.path.isfile(CANONICAL_PATH), f"Missing canonical file at {CANONICAL_PATH}")
        self.assertTrue(os.path.isfile(REGISTRY_PATH), f"Missing registry file at {REGISTRY_PATH}")

        with open(CANONICAL_PATH, "r", encoding="utf-8") as f:
            canonical = json.load(f)
        self.assertIsInstance(canonical, dict, "Canonical root must be a JSON object")
        self.assertIn("metadata", canonical, "Canonical must have metadata")
        self.assertIn("numbers", canonical, "Canonical must have numbers list")

        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            registry = json.load(f)
        self.assertIsInstance(registry, dict, "Registry root must be a JSON object")
        self.assertIn("background_class", registry, "Registry must have background_class")
        self.assertIn("items", registry, "Registry must have items list")

    def test_item_counts_and_indexing(self):
        """Verify that there are exactly 20 numbers, indexed contiguously 1 to 20."""
        with open(CANONICAL_PATH, "r", encoding="utf-8") as f:
            canonical = json.load(f)
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            registry = json.load(f)

        numbers = canonical["numbers"]
        reg_items = registry["items"]

        self.assertEqual(len(numbers), 20, f"Expected 20 canonical numbers, found {len(numbers)}")
        self.assertEqual(len(reg_items), 20, f"Expected 20 registry items, found {len(reg_items)}")
        self.assertEqual(registry["total_classes"], 21, "Total classes in registry must be 21 (0 to 20)")

        # Check background class (Index 0)
        bg = registry["background_class"]
        self.assertEqual(bg["class_index"], 0)
        self.assertEqual(bg["label_id"], "_background_")

        # Check contiguous sequence 1..20
        class_indices_canonical = [item["class_index"] for item in numbers]
        numbers_canonical = [item["number"] for item in numbers]
        self.assertEqual(class_indices_canonical, list(range(1, 21)), "Canonical class indices must be 1..20")
        self.assertEqual(numbers_canonical, list(range(1, 21)), "Canonical numbers must be 1..20")

        class_indices_reg = [item["class_index"] for item in reg_items]
        numbers_reg = [item["number"] for item in reg_items]
        self.assertEqual(class_indices_reg, list(range(1, 21)), "Registry class indices must be 1..20")
        self.assertEqual(numbers_reg, list(range(1, 21)), "Registry numbers must be 1..20")

    def test_bilingual_data_integrity(self):
        """Verify all bilingual text fields are populated, valid, and contain expected Devanagari script."""
        with open(CANONICAL_PATH, "r", encoding="utf-8") as f:
            canonical = json.load(f)

        for item in canonical["numbers"]:
            idx = item["class_index"]
            # Non-empty assertions
            self.assertTrue(item["hindi_numeral"].strip(), f"Empty hindi_numeral for item {idx}")
            self.assertTrue(item["hindi_word"].strip(), f"Empty hindi_word for item {idx}")
            self.assertTrue(item["mundari_numeral"].strip(), f"Empty mundari_numeral for item {idx}")
            self.assertTrue(item["mundari_word"].strip(), f"Empty mundari_word for item {idx}")
            self.assertTrue(item["mundari_root"].strip(), f"Empty mundari_root for item {idx}")
            self.assertTrue(item["mundari_phonetic_latin"].strip(), f"Empty phonetic for item {idx}")
            self.assertTrue(len(item["variants_attested"]) > 0, f"No variants attested for item {idx}")

            # Script validation: check Devanagari characters in Hindi and Mundari words
            hi_has_devanagari = any(0x0900 <= ord(c) <= 0x097F for c in item["hindi_word"])
            self.assertTrue(hi_has_devanagari, f"Hindi word '{item['hindi_word']}' lacks Devanagari characters")

            mu_has_devanagari = any(0x0900 <= ord(c) <= 0x097F for c in item["mundari_word"])
            self.assertTrue(mu_has_devanagari, f"Mundari word '{item['mundari_word']}' lacks Devanagari characters")

    def test_honest_verification_status_no_fabrication(self):
        """
        CRITICAL POLICY TEST:
        Verify that verification statuses strictly reflect physical reality.
        - Linguistic status must distinguish between CORPUS_ATTESTED and LINGUISTICALLY_REVIEWED.
        - EDUCATIONALLY_CANONICAL and NATIVE_SPEAKER_VERIFIED must be False until validated.
        - Audio files are MISSING, and audio_status MUST be MISSING.
        - Generated flashcards must be clearly labeled as GENERATED_PROTOTYPE (never falsely claiming VERIFIED).
        """
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            registry = json.load(f)

        for item in registry["items"]:
            idx = item["class_index"]
            ver_status = item["verification_status"]

            self.assertIn("CORPUS_ATTESTED", ver_status)
            self.assertIn("LINGUISTICALLY_REVIEWED", ver_status)
            self.assertIn("EDUCATIONALLY_CANONICAL", ver_status)
            self.assertIn("NATIVE_SPEAKER_VERIFIED", ver_status)

            self.assertFalse(
                ver_status["EDUCATIONALLY_CANONICAL"],
                f"Item {idx} cannot claim EDUCATIONALLY_CANONICAL without official curriculum sign-off",
            )
            self.assertFalse(
                ver_status["NATIVE_SPEAKER_VERIFIED"],
                f"Item {idx} cannot claim NATIVE_SPEAKER_VERIFIED without native speaker review",
            )

            # Check audio asset (must be MISSING)
            audio_rel_path = item["audio_asset"]
            audio_full_path = os.path.join(BASE_DIR, audio_rel_path)
            self.assertFalse(os.path.isfile(audio_full_path), f"Audio file {audio_rel_path} should not exist yet")
            self.assertEqual(
                item["audio_status"],
                "MISSING",
                f"Item {idx}: audio file does not exist on disk, audio_status MUST be 'MISSING'",
            )

            # Check flashcard asset (must physically exist and be marked GENERATED_PROTOTYPE)
            card_rel_path = item["flashcard_asset"]
            card_full_path = os.path.join(BASE_DIR, card_rel_path)
            self.assertTrue(os.path.isfile(card_full_path), f"Flashcard file {card_rel_path} must exist on disk")
            self.assertGreater(os.path.getsize(card_full_path), 0, f"Flashcard file {card_rel_path} must be non-empty")
            self.assertEqual(
                item["flashcard_status"],
                "GENERATED_PROTOTYPE (PENDING HUMAN VALIDATION)",
                f"Item {idx}: flashcard must be labeled GENERATED_PROTOTYPE, found {item['flashcard_status']}",
            )

    def test_educational_framework_alignment(self):
        """Verify NIPUN Bharat and FLN Grade 1 metadata alignment and UNVERIFIED flag."""
        with open(CANONICAL_PATH, "r", encoding="utf-8") as f:
            canonical = json.load(f)

        for item in canonical["numbers"]:
            idx = item["class_index"]
            self.assertEqual(item["grade"], 1, f"Item {idx}: Grade must be 1")
            self.assertEqual(item["subject"], "Mathematics", f"Item {idx}: Subject must be Mathematics")
            self.assertEqual(item["fln_domain"], "Foundational Numeracy", f"Item {idx}: Domain must be Foundational Numeracy")
            self.assertEqual(item["topic"], "Numbers 1-20", f"Item {idx}: Topic must be Numbers 1-20")

            self.assertEqual(
                item["nipun_verification_status"],
                "UNVERIFIED — PENDING SOURCE VALIDATION",
                f"Item {idx}: nipun_verification_status must be 'UNVERIFIED — PENDING SOURCE VALIDATION'",
            )
            self.assertTrue(
                "UNVERIFIED — PENDING SOURCE VALIDATION" in item["nipun_competency_code"],
                f"Item {idx}: nipun_competency_code must flag UNVERIFIED source validation",
            )

    def test_canonical_and_registry_parity(self):
        """Verify 1-to-1 data parity between canonical dataset and runtime content registry."""
        with open(CANONICAL_PATH, "r", encoding="utf-8") as f:
            canonical = json.load(f)
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            registry = json.load(f)

        num_dict = {item["class_index"]: item for item in canonical["numbers"]}
        reg_dict = {item["class_index"]: item for item in registry["items"]}

        for idx in range(1, 21):
            num_item = num_dict[idx]
            reg_item = reg_dict[idx]

            self.assertEqual(reg_item["number"], num_item["number"])
            self.assertEqual(reg_item["hindi_numeral"], num_item["hindi_numeral"])
            self.assertEqual(reg_item["hindi_text"], num_item["hindi_word"])
            self.assertEqual(reg_item["mundari_numeral"], num_item["mundari_numeral"])
            self.assertEqual(reg_item["mundari_text"], num_item["mundari_word"])
            self.assertEqual(reg_item["mundari_root"], num_item["mundari_root"])
            self.assertEqual(reg_item["mundari_phonetic"], num_item["mundari_phonetic_latin"])
            self.assertEqual(reg_item["variants_attested"], num_item["variants_attested"])
            self.assertEqual(reg_item["audio_asset"], num_item["audio_target_file"])
            self.assertEqual(reg_item["audio_status"], num_item["audio_status"])
            self.assertEqual(reg_item["flashcard_asset"], num_item["flashcard_target_file"])
            self.assertEqual(reg_item["flashcard_status"], num_item["flashcard_status"])
            self.assertEqual(reg_item["nipun_competency_code"], num_item["nipun_competency_code"])
            self.assertEqual(reg_item["nipun_verification_status"], num_item["nipun_verification_status"])


if __name__ == "__main__":
    unittest.main()
