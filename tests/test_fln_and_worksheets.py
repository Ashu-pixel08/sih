import os
import json
import unittest
from xml.etree import ElementTree as ET

from content.fln.fln_content_engine import FLNContentEngine
from content.flashcards.flashcard_generator import FlashcardGenerator
from content.worksheets.worksheet_generator import WorksheetGenerator

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestFLNAndWorksheets(unittest.TestCase):

    def setUp(self):
        self.engine = FLNContentEngine()
        self.card_gen = FlashcardGenerator()
        self.ws_gen = WorksheetGenerator()

    def test_curriculum_model_structure(self):
        """Verify that curriculum_model.json exists and defines required FLN framework."""
        curr_path = os.path.join(BASE_DIR, "content", "fln", "curriculum_model.json")
        self.assertTrue(os.path.isfile(curr_path), "curriculum_model.json must exist")

        with open(curr_path, "r", encoding="utf-8") as f:
            curr = json.load(f)

        self.assertEqual(curr["grade"], 1)
        self.assertEqual(curr["subject"], "Mathematics")
        self.assertEqual(curr["fln_domain"], "Foundational Numeracy")
        self.assertEqual(curr["topic"], "Numbers 1-20")
        self.assertEqual(curr["nipun_alignment"]["status"], "UNVERIFIED — PENDING SOURCE VALIDATION")
        self.assertGreaterEqual(len(curr["core_competencies"]), 4)
        self.assertGreaterEqual(len(curr["learning_activity_types"]), 4)

    def test_fln_lessons_completeness_1_to_20(self):
        """Verify all 20 FLN lessons are complete, structured, and sequentially accessible."""
        lessons = self.engine.get_all_lessons()
        self.assertEqual(len(lessons), 20, "Must provide exactly 20 lessons for 1-20")

        for idx, lesson in enumerate(lessons, 1):
            self.assertEqual(lesson.number, idx)
            self.assertEqual(lesson.class_index, idx)
            self.assertTrue(lesson.hindi_content["word"].strip())
            self.assertTrue(lesson.hindi_content["numeral"].strip())
            self.assertTrue(lesson.mundari_content["word"].strip())
            self.assertTrue(lesson.mundari_content["root"].strip())
            self.assertTrue(lesson.mundari_content["phonetic"].strip())
            self.assertEqual(lesson.audio_status, "MISSING")
            self.assertEqual(lesson.flashcard_status, "GENERATED_PROTOTYPE (PENDING HUMAN VALIDATION)")
            self.assertEqual(lesson.nipun_verification_status, "UNVERIFIED — PENDING SOURCE VALIDATION")

    def test_teacher_hindi_to_mundari_bridge(self):
        """Verify teacher Hindi input is correctly translated to Mundari pedagogy."""
        # Test Hindi word query
        res_word = self.engine.bridge_teacher_input("पाँच")
        self.assertTrue(res_word["matched"])
        self.assertEqual(res_word["lesson"]["number"], 5)
        self.assertEqual(res_word["lesson"]["mundari_content"]["word"], "मोड़ेया")

        # Test Hindi numeral query
        res_numeral = self.engine.bridge_teacher_input("१४")
        self.assertTrue(res_numeral["matched"])
        self.assertEqual(res_numeral["lesson"]["number"], 14)
        self.assertEqual(res_numeral["lesson"]["mundari_content"]["word"], "गेल उपुनिया")

        # Test out of curriculum query
        res_invalid = self.engine.bridge_teacher_input("सौ")
        self.assertFalse(res_invalid["matched"])

    def test_fln_activity_generation(self):
        """Verify activity generation for all supported interactive types."""
        # Listen and identify
        act_listen = self.engine.create_activity("listen_and_identify", 7)
        self.assertEqual(act_listen.target_number, 7)
        self.assertEqual(act_listen.correct_answer, 7)
        self.assertGreaterEqual(len(act_listen.options), 3)

        # Count objects
        act_count = self.engine.create_activity("count_objects", 12)
        self.assertEqual(act_count.target_number, 12)
        self.assertEqual(act_count.prompt_data["tens"], 1)
        self.assertEqual(act_count.prompt_data["ones"], 2)

        # Missing numbers
        act_missing = self.engine.create_activity("missing_number", 4)
        self.assertEqual(act_missing.target_number, 4)
        self.assertIn(None, act_missing.prompt_data["sequence_display"])

    def test_flashcard_svg_assets_integrity(self):
        """Verify all 20 SVG flashcard files exist, are valid XML, and include provenance badges."""
        flashcard_dir = os.path.join(BASE_DIR, "content", "flashcards", "numbers")
        self.assertTrue(os.path.isdir(flashcard_dir))

        for num in range(1, 21):
            svg_path = os.path.join(flashcard_dir, f"card_{num:02d}.svg")
            self.assertTrue(os.path.isfile(svg_path), f"card_{num:02d}.svg must exist")
            self.assertGreater(os.path.getsize(svg_path), 1000, f"card_{num:02d}.svg size too small")

            with open(svg_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Must contain provenance watermark
            self.assertIn("GENERATED PROTOTYPE (PENDING HUMAN VALIDATION)", content)
            # Must contain audio MISSING reference
            self.assertIn("[MISSING]", content)
            # Must contain numeral
            self.assertIn(f">{num}<", content)

            # XML validation
            try:
                tree = ET.fromstring(content)
                self.assertTrue(tree.tag.endswith("svg"))
            except ET.ParseError as e:
                self.fail(f"card_{num:02d}.svg is not valid XML/SVG: {e}")

        # Check HTML review deck
        deck_path = os.path.join(BASE_DIR, "content", "flashcards", "flashcard_deck.html")
        self.assertTrue(os.path.isfile(deck_path), "flashcard_deck.html must exist")

    def test_worksheet_generation_and_reproducibility(self):
        """Verify all 5 worksheet types are generated in JSON and HTML and are deterministic."""
        ws_dir = os.path.join(BASE_DIR, "content", "worksheets", "generated")
        self.assertTrue(os.path.isdir(ws_dir))

        expected_types = [
            "ws_01_recognition",
            "ws_02_counting",
            "ws_03_matching",
            "ws_04_sequencing",
            "ws_05_missing_numbers",
        ]

        for ws_name in expected_types:
            json_p = os.path.join(ws_dir, f"{ws_name}.json")
            html_p = os.path.join(ws_dir, f"{ws_name}.html")

            self.assertTrue(os.path.isfile(json_p), f"{ws_name}.json must exist")
            self.assertTrue(os.path.isfile(html_p), f"{ws_name}.html must exist")

            with open(json_p, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.assertEqual(data["grade"], 1)
            self.assertEqual(data["fln_domain"], "Foundational Numeracy")
            self.assertIn("GENERATED_PROTOTYPE", data["provenance_status"])
            self.assertGreater(len(data["problems"]), 0, f"Worksheet {ws_name} must have problems")

        # Reproducibility test: identical seed produces identical JSON
        doc1 = self.ws_gen.generate_number_recognition_worksheet(seed=123)
        doc2 = self.ws_gen.generate_number_recognition_worksheet(seed=123)
        self.assertEqual(doc1, doc2, "Worksheet generation must be 100% deterministic given the same seed")


if __name__ == "__main__":
    unittest.main()
