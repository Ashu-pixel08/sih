"""
test_ui_backend_integration.py - UI to Backend Integration & Governance Verification
SIH260042: AI-Powered Vernacular Pedagogy and Real-Time Translation Tool
"""

import json
import os
import re
import unittest

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_HTML = os.path.join(WORKSPACE_ROOT, "frontend", "index.html")
CONTENT_REGISTRY = os.path.join(WORKSPACE_ROOT, "content", "content_registry.json")
PHRASEBOOK = os.path.join(WORKSPACE_ROOT, "content", "translations", "classroom_phrasebook.json")
DOCS_DIR = os.path.join(WORKSPACE_ROOT, "docs")
ANDROID_CONTRACT_DIR = os.path.join(WORKSPACE_ROOT, "android", "contract")


class TestUIBackendIntegration(unittest.TestCase):
    """Tests that the frontend reference UI is properly integrated with the backend AI/data architecture,
    strictly adhering to identity, audio, offline, performance, and governance rules."""

    def test_frontend_html_identity_and_structure(self):
        """Verify frontend/index.html exists, has valid structure, and does NOT use prohibited external branding."""
        self.assertTrue(os.path.exists(FRONTEND_HTML), "frontend/index.html must exist")
        with open(FRONTEND_HTML, "r", encoding="utf-8") as f:
            html = f.read()

        # Prohibited branding assertion: PALASH AI must NOT be used as application identity
        self.assertNotIn("PALASH AI", html, "Must not use external program/initiative name as app identity")

        # Project-specific / configurable identity assertion
        self.assertIn("APP_NAME_PENDING", html, "Must feature project-specific platform identity")
        self.assertIn("Learn in Your Language. Teach with Confidence.", html)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("DB =", html, "Must contain embedded canonical database")

        # Must not contain unresolved raw bracketed placeholders
        raw_placeholders = re.findall(r"\[verified.*?\]", html, re.IGNORECASE)
        self.assertEqual(len(raw_placeholders), 0, f"Found unresolved placeholders: {raw_placeholders}")

    def test_audio_and_text_status_strict_separation(self):
        """Verify audio status is strictly SYNTHETIC_PROTOTYPE and separated from text status."""
        with open(FRONTEND_HTML, "r", encoding="utf-8") as f:
            html = f.read()

        # Must NOT claim authentic or native Mundari audio
        self.assertNotIn("authentic Mundari audio", html.lower(), "Must not claim authentic audio")
        self.assertNotIn("native Mundari recording", html.lower(), "Must not claim native recording")
        self.assertNotIn("verified pronunciation audio", html.lower(), "Must not claim verified audio")

        # Must explicitly label audio as SYNTHETIC_PROTOTYPE
        self.assertIn("SYNTHETIC_PROTOTYPE (PENDING HUMAN VALIDATION)", html)
        self.assertIn("Play Prototype Audio", html)

    def test_module_scope_and_demonstration_distinction(self):
        """Verify Numbers 1-20 is documented as a demonstration module within a broader platform."""
        with open(FRONTEND_HTML, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn("Demonstration Module", html)
        self.assertIn("controlled demonstration module of the broader FLN architecture", html)

    def test_offline_and_performance_honest_reporting(self):
        """Verify offline status and performance metrics are honestly reported."""
        with open(FRONTEND_HTML, "r", encoding="utf-8") as f:
            html = f.read()

        # Must NOT claim 100% offline operational before physical Android validation
        self.assertNotIn("100% OFFLINE OPERATIONAL", html)
        self.assertIn("OFFLINE ARCHITECTURE READY — PHYSICAL ANDROID VALIDATION PENDING", html)

        # Performance separation: must distinguish measured desktop from estimated Android
        self.assertIn("12.4 ms", html)
        self.assertIn("DESKTOP_MEASURED", html)
        self.assertIn("ESTIMATED", html)

        # Classroom networking: must claim contract ready, not implemented transport
        self.assertIn("CLASSROOM SESSION CONTRACT READY", html)

    def test_ui_backend_data_parity(self):
        """Verify embedded database in frontend matches canonical content_registry.json and phrasebook."""
        with open(FRONTEND_HTML, "r", encoding="utf-8") as f:
            html = f.read()

        with open(CONTENT_REGISTRY, "r", encoding="utf-8") as f:
            reg = json.load(f)

        # Check all 20 numerals from content_registry are represented in the HTML
        for item in reg["items"]:
            num = item["number"]
            mundari = item["mundari_text"]
            phonetic = item["mundari_phonetic"]
            self.assertIn(mundari, html, f"Mundari numeral {num} ({mundari}) must be in UI")
            self.assertIn(phonetic, html, f"Phonetic {phonetic} for numeral {num} must be in UI")

        # Check core classroom phrases from phrasebook
        with open(PHRASEBOOK, "r", encoding="utf-8") as f:
            pb = json.load(f)

        for p in pb["phrases"][:5]:
            self.assertIn(p["hindi_text"], html)
            self.assertIn(p["mundari_text"], html)

    def test_teacher_translation_adapter_simulation(self):
        """Simulate the backendTranslate function logic used in UI."""
        with open(CONTENT_REGISTRY, "r", encoding="utf-8") as f:
            reg = json.load(f)
        num_dict = {item["hindi_text"]: item["mundari_text"] for item in reg["items"]}

        # 1. Exact numeral lookup
        self.assertEqual(num_dict.get("एक"), "मिअद")
        self.assertEqual(num_dict.get("दो"), "बारिया")
        self.assertEqual(num_dict.get("बीस"), "हिसि")

        # 2. Out-of-vocabulary check
        unknown_term = "कंप्यूटर"
        self.assertNotIn(unknown_term, num_dict)

    def test_worksheet_templates_coverage(self):
        """Verify the 5 canonical worksheet templates are referenced and renderable."""
        with open(FRONTEND_HTML, "r", encoding="utf-8") as f:
            html = f.read()

        required_ws_types = ["recognition", "counting", "matching", "sequencing", "missing_numbers"]
        for ws_type in required_ws_types:
            self.assertIn(ws_type, html, f"Worksheet type {ws_type} must be supported in UI")

    def test_android_kotlin_contracts_completeness(self):
        """Verify all Android Kotlin contract files exist and define required interfaces."""
        expected_files = [
            "SpeechModels.kt",
            "TranslationModels.kt",
            "EducationalModels.kt",
            "SessionModels.kt",
            "AudioPreprocessor.kt",
            "PipelineContracts.kt",
            "ClassroomModels.kt",
            "ClassroomContracts.kt",
            "ProgressModels.kt",
        ]
        for fname in expected_files:
            fpath = os.path.join(ANDROID_CONTRACT_DIR, fname)
            self.assertTrue(os.path.exists(fpath), f"Missing Android contract file: {fname}")
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("package org.sih260042.pedagogy", content)

    def test_documentation_spec_conformance(self):
        """Verify documentation files exist, use correct identity, and cover all governance requirements."""
        ui_integration_doc = os.path.join(DOCS_DIR, "ui-backend-integration.md")
        ui_state_doc = os.path.join(DOCS_DIR, "ui-state-contract.md")

        self.assertTrue(os.path.exists(ui_integration_doc), "docs/ui-backend-integration.md must exist")
        self.assertTrue(os.path.exists(ui_state_doc), "docs/ui-state-contract.md must exist")

        with open(ui_integration_doc, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("PALASH AI", content, "Prohibited branding must not be in integration doc")
        self.assertIn("APP_NAME_PENDING", content)
        self.assertIn("Demonstration / MVP Module", content)
        self.assertIn("SYNTHETIC_PROTOTYPE", content)
        self.assertIn("OFFLINE ARCHITECTURE READY — PHYSICAL ANDROID VALIDATION PENDING", content)
        self.assertIn("CLASSROOM SESSION CONTRACT READY", content)
        self.assertIn("DESKTOP_MEASURED", content)
        self.assertIn("ANDROID_ESTIMATED", content)

        with open(ui_state_doc, "r", encoding="utf-8") as f:
            state_content = f.read()
        self.assertNotIn("PALASH AI", state_content, "Prohibited branding must not be in state doc")
        self.assertIn("EXACT_CANONICAL_LOOKUP", state_content)
        self.assertIn("CORPUS_ATTESTED", state_content)
        self.assertIn("SYNTHETIC_PROTOTYPE", state_content)
        self.assertIn("IDLE", state_content)
        self.assertIn("LISTENING", state_content)
        self.assertIn("PROCESSING", state_content)
        self.assertIn("REVIEW", state_content)
        self.assertIn("FALLBACK", state_content)
        self.assertIn("BROADCAST", state_content)

    def test_bidirectional_translation_ui_support(self):
        """Verify frontend/index.html includes bidirectional translation and disclosures."""
        with open(FRONTEND_HTML, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn("translationDirection", html, "Must include translationDirection in state")
        self.assertIn("toggleDirection()", html, "Must include toggleDirection handler")
        self.assertIn("Mundari ➔ Hindi", html, "Must include Mundari to Hindi UI direction")
        self.assertIn("Hindi ➔ Mundari", html, "Must include Hindi to Mundari UI direction")
        self.assertIn("WEB PROTOTYPE ONLY — browser speech recognition may require network", html)
        self.assertIn("lacks native support for Mundari", html)


if __name__ == "__main__":
    unittest.main()
