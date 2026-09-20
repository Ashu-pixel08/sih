"""
tests/test_educational_content_layer.py
Unit and integration tests for the Educational Content Layer:
- EducationalContentManager ingestion and dataset integrity
- 159 educational vocabulary records and 16 categories
- Image manifest verification on disk (130 valid images, 29 abstract records)
- Promotion status and validation badge integrity (unverified held for review)
- Server API endpoints (/api/educational/vocabulary, /api/educational/categories, image streaming)
- Frontend contract verification (Flashcards, 7 practice modes, 8 worksheet question types, classroom broadcast)
- Developer/ML cleanliness verification
"""

import json
import os
import sys
import re
import urllib.request
import pytest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ai.educational_content import get_educational_content_manager


class TestEducationalContentManager:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.mgr = get_educational_content_manager()

    def test_total_dataset_records(self):
        items = self.mgr.get_all_vocabulary()
        assert len(items) == 159, f"Expected 159 records, got {len(items)}"

    def test_categories_count_and_derivation(self):
        cats = self.mgr.get_categories()
        assert len(cats) == 16, f"Expected 16 categories, got {len(cats)}"
        cat_names = [c["name"] for c in cats]
        expected_cats = [
            "Animals", "Aquatic Animals", "Birds", "Body Parts", "Colors",
            "Family", "Flowers", "Food", "Grains", "Insects",
            "Months", "Shapes", "Things", "Vegetables", "Vehicles", "Weeks"
        ]
        for expected in expected_cats:
            assert expected in cat_names, f"Category '{expected}' missing from derived categories"

    def test_image_existence_and_manifest_counts(self):
        items = self.mgr.get_all_vocabulary()
        with_images = [it for it in items if it["image_exists"]]
        abstract_items = [it for it in items if not it["image_exists"]]

        assert len(with_images) == 130, f"Expected 130 valid image items, got {len(with_images)}"
        assert len(abstract_items) == 29, f"Expected 29 abstract items, got {len(abstract_items)}"

        # Every item declared as having an image MUST physically exist on disk
        missing_on_disk = []
        for it in with_images:
            if not os.path.exists(it["image_disk_path"]):
                missing_on_disk.append((it["english"], it["image_disk_path"]))
        assert len(missing_on_disk) == 0, f"Found {len(missing_on_disk)} missing images on disk: {missing_on_disk[:5]}"

    def test_data_validation_integrity(self):
        items = self.mgr.get_all_vocabulary()
        verified = [it for it in items if it["is_verified"]]
        unverified = [it for it in items if not it["is_verified"]]

        assert len(verified) == 95, f"Expected 95 verified items, got {len(verified)}"
        assert len(unverified) == 64, f"Expected 64 unverified items, got {len(unverified)}"

        # Strict safety check: NO unverified item may ever be labeled 'VERIFIED EDUCATIONAL'
        for uv in unverified:
            assert uv["validation_badge"] != "VERIFIED EDUCATIONAL", (
                f"Unverified item '{uv['english']}' has illegitimate VERIFIED EDUCATIONAL badge"
            )
            assert "HELD FOR REVIEW" in uv["validation_badge"], (
                f"Unverified item '{uv['english']}' must state HELD FOR REVIEW"
            )

    def test_category_filtering(self):
        animals = self.mgr.get_vocabulary_by_category("Animals")
        assert len(animals) == 10
        weeks = self.mgr.get_vocabulary_by_category("Weeks")
        assert len(weeks) == 7
        months = self.mgr.get_vocabulary_by_category("Months")
        assert len(months) == 12

    def test_search_filtering(self):
        elephant_matches = self.mgr.search_vocabulary("elephant")
        assert len(elephant_matches) >= 1
        assert any(m["english"].lower() == "elephant" for m in elephant_matches)

        hindi_matches = self.mgr.search_vocabulary("हाथी")
        assert len(hindi_matches) >= 1


class TestEducationalApiEndpoints:
    BASE_URL = "http://localhost:8080"

    def test_vocabulary_endpoint(self):
        try:
            req = urllib.request.urlopen(f"{self.BASE_URL}/api/educational/vocabulary")
            assert req.status == 200
            data = json.loads(req.read().decode("utf-8"))
            assert data["total"] == 159
            assert len(data["items"]) == 159
            assert len(data["categories"]) == 16
        except urllib.error.URLError:
            pytest.skip("Local test server is not running on port 8080")

    def test_categories_endpoint(self):
        try:
            req = urllib.request.urlopen(f"{self.BASE_URL}/api/educational/categories")
            assert req.status == 200
            data = json.loads(req.read().decode("utf-8"))
            assert data["total_categories"] == 16
            assert data["total_vocabulary"] == 159
        except urllib.error.URLError:
            pytest.skip("Local test server is not running on port 8080")

    def test_filtered_vocabulary_endpoint(self):
        try:
            req = urllib.request.urlopen(f"{self.BASE_URL}/api/educational/vocabulary?category=Birds")
            assert req.status == 200
            data = json.loads(req.read().decode("utf-8"))
            assert data["total"] == 10
            assert all(x["category"] == "Birds" for x in data["items"])

            req_ver = urllib.request.urlopen(f"{self.BASE_URL}/api/educational/vocabulary?verified_only=true")
            assert req_ver.status == 200
            data_ver = json.loads(req_ver.read().decode("utf-8"))
            assert data_ver["total"] == 95
            assert all(x["is_verified"] for x in data_ver["items"])
        except urllib.error.URLError:
            pytest.skip("Local test server is not running on port 8080")

    def test_image_streaming_endpoint(self):
        try:
            req = urllib.request.urlopen(f"{self.BASE_URL}/data/custom/images/Animals/Elephant.jpg")
            assert req.status == 200
            content = req.read()
            assert len(content) > 10000
            assert req.headers.get_content_type() in ("image/jpeg", "image/jpg")
        except urllib.error.URLError:
            pytest.skip("Local test server is not running on port 8080")


class TestFrontendEducationalContract:
    @pytest.fixture(autouse=True)
    def load_html(self):
        html_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            self.html = f.read()

    def test_flashcards_system_present(self):
        assert "function flashcards()" in self.html
        assert "function setFlashcardCategory(" in self.html
        assert "category-pill-bar" in self.html
        assert "flashcard-image" in self.html
        assert "broadcastVocabCard" in self.html
        assert "playVocabAudio" in self.html
        assert "loadEducationalVocabulary" in self.html

    def test_all_seven_practice_modes_present(self):
        assert "function studentPractice()" in self.html
        assert "generateEducationalPracticeQuestions" in self.html
        assert "Mode A: 🖼️ Image ➔ Hindi" in self.html
        assert "Mode B: 🖼️ Image ➔ Mundari" in self.html
        assert "Mode C: 🇮🇳 Hindi ➔ Mundari" in self.html
        assert "Mode D: 🏹 Mundari ➔ Hindi" in self.html
        assert "Mode E: 🎯 Word ➔ Image" in self.html
        assert "Mode F: 🔗 Match Pairs" in self.html
        assert "Mode G: 🎲 Mixed Practice Quiz" in self.html
        assert "Shaabaash!" in self.html or "शाबाश!" in self.html

    def test_all_eight_worksheet_types_present(self):
        assert "function worksheet()" in self.html
        assert "renderWorksheetPreview()" in self.html
        assert "type_1" in self.html
        assert "type_2" in self.html
        assert "type_3" in self.html
        assert "type_4" in self.html
        assert "type_5" in self.html
        assert "type_6" in self.html
        assert "type_7" in self.html
        assert "type_8" in self.html
        assert "worksheet-doc-sheet" in self.html
        assert "Teacher's Answer Key" in self.html or "शिक्षक उत्तर कुंजी" in self.html
        assert "downloadWorksheetHtml()" in self.html

    def test_classroom_broadcast_integration(self):
        assert "broadcast_vocab" in self.html
        assert "broadcast_practice" in self.html
        assert "broadcast-spotlight-card" in self.html
        assert "TEACHER LIVE FLASHCARD" in self.html

    def test_ml_cleanliness_in_educational_views(self):
        fc_start = self.html.find("function flashcards()")
        fc_end = self.html.find("// PHASE 4: STUDENT -> IMAGE-BASED PRACTICE")
        flashcards_code = self.html[fc_start:fc_end]

        pr_start = self.html.find("function studentPractice()")
        pr_end = self.html.find("// PHASE 5: TEACHER -> DETAILED BILINGUAL WORKSHEET")
        practice_code = self.html[pr_start:pr_end]

        ws_start = self.html.find("function worksheet()")
        ws_end = self.html.find("// PHASE 6: TEACHER -> STUDENT PROGRESS")
        worksheet_code = self.html[ws_start:ws_end]

        for section_name, code in [("flashcards", flashcards_code), ("practice", practice_code), ("worksheet", worksheet_code)]:
            assert "bleu" not in code.lower(), f"{section_name} exposes BLEU score"
            assert "chrf" not in code.lower(), f"{section_name} exposes ChrF score"
            assert "subword" not in code.lower(), f"{section_name} exposes subword tokens"
            assert "beam size" not in code.lower(), f"{section_name} exposes beam size"
