"""
tests/test_teacher_voice_integration.py
=============================================================================
SIH260042: Teacher Voice Profile & Zero-Shot Conversion Integration Tests
=============================================================================
Verifies end-to-end integration and governance safeguards for the Teacher Voice:
1. Hindi "पाँच": MMS-TTS base -> OpenVoice VC -> Teacher Hindi (ACTIVE).
2. Hindi "नमस्ते": MMS-TTS base -> OpenVoice VC -> Teacher Hindi (ACTIVE).
3. Mundari "जोहार": Controlled registry -> OpenVoice VC -> Teacher Mundari (ACTIVE, PENDING).
4. Mundari "मोड़ेया": Controlled numeral -> OpenVoice VC -> Teacher Mundari (ACTIVE, PENDING).
5. Arbitrary Mundari "चिलका होबाः ओ अम।": Voice conversion BLOCKED -> Raw MMS-TTS (BLOCKED_UNCONTROLLED_MUNDARI).
6. Deterministic Caching: Second call results in cache HIT.
7. Profile Governance: Toggle, Delete profile, and cache invalidation.
8. Linguistic Governance: Status NEVER upgraded beyond PROTOTYPE_ONLY_PENDING_HUMAN_VALIDATION.
=============================================================================
"""

import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
import wave
from http.server import HTTPServer
import threading
import urllib.request
import urllib.error

PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai.speech.pronunciation_service import (
    PronunciationResult,
    PronunciationService,
    PrototypeAudioRegistryProvider,
    VitsTTSProvider,
)
from ai.speech.teacher_voice_service import (
    TeacherVoiceConverter,
    TeacherVoiceProfileManager,
)
from server import PrototypeBridgeHandler


class TestTeacherVoiceServiceCore(unittest.TestCase):
    """Verifies core service-level behavior with live models."""

    @classmethod
    def setUpClass(cls):
        cls.service = PronunciationService(project_root=PROJECT_ROOT)
        # Ensure profile is active for tests
        if cls.service.teacher_voice_manager:
            ref_path = os.path.join(PROJECT_ROOT, "scratch", "voice_conversion_test", "reference_human.wav")
            if os.path.exists(ref_path) and not cls.service.teacher_voice_manager.is_active():
                cls.service.teacher_voice_manager.enroll_from_file(ref_path)

    def test_01_profile_manager_active(self):
        """Ensure TeacherVoiceProfileManager is loaded and reports READY."""
        mgr = self.service.teacher_voice_manager
        self.assertIsNotNone(mgr)
        self.assertTrue(mgr.is_enrolled())
        self.assertTrue(mgr.is_active())
        status = mgr.get_status()
        self.assertEqual(status["status"], "READY")
        self.assertEqual(status["ui_state_label"], "Teacher voice ready")

    def test_02_hindi_paanch_teacher_voice(self):
        """Hindi 'पाँच' generates teacher-adapted synthetic speech."""
        result, err = self.service.synthesize("पाँच", "hindi", use_teacher_voice=True)
        self.assertIsNone(err)
        self.assertIsNotNone(result)
        self.assertTrue(result.teacher_voice_applied)
        self.assertEqual(result.language, "hindi")
        self.assertEqual(result.verification_status, "TEACHER_ADAPTED_SYNTHETIC")
        self.assertIn("openvoice_v2", result.engine_name)
        self.assertGreater(len(result.audio_bytes), 1000)

    def test_03_hindi_namaste_teacher_voice(self):
        """Hindi 'नमस्ते' generates teacher-adapted synthetic speech."""
        result, err = self.service.synthesize("नमस्ते", "hindi", use_teacher_voice=True)
        self.assertIsNone(err)
        self.assertIsNotNone(result)
        self.assertTrue(result.teacher_voice_applied)
        self.assertEqual(result.language, "hindi")
        self.assertEqual(result.verification_status, "TEACHER_ADAPTED_SYNTHETIC")
        self.assertGreater(len(result.audio_bytes), 1000)

    def test_04_mundari_johar_controlled_teacher_voice(self):
        """Mundari 'जोहार' from controlled registry converts toward teacher timbre but NEVER upgrades status."""
        result, err = self.service.synthesize("जोहार", "mundari", use_teacher_voice=True)
        self.assertIsNone(err)
        self.assertIsNotNone(result)
        self.assertTrue(result.teacher_voice_applied)
        self.assertEqual(result.language, "mundari")
        # STRICT GOVERNANCE: Must remain explicitly PENDING human validation
        self.assertEqual(result.verification_status, "PROTOTYPE_ONLY_PENDING_HUMAN_VALIDATION")
        self.assertIn("openvoice_v2", result.engine_name)

    def test_05_mundari_modeya_controlled_numeral(self):
        """Mundari 'मोड़ेया' (5) converts toward teacher timbre and preserves prototype status."""
        result, err = self.service.synthesize("मोड़ेया", "mundari", use_teacher_voice=True)
        self.assertIsNone(err)
        self.assertIsNotNone(result)
        self.assertTrue(result.teacher_voice_applied)
        self.assertEqual(result.language, "mundari")
        self.assertEqual(result.verification_status, "PROTOTYPE_ONLY_PENDING_HUMAN_VALIDATION")

    def test_06_arbitrary_mundari_sentence_blocked_from_voice_conversion(self):
        """
        STRICT GOVERNANCE RULE:
        Arbitrary unverified Mundari sentences MUST NOT undergo voice conversion.
        They must remain raw synthetic TTS with SYNTHETIC_GENERATED_TTS status.
        """
        arbitrary_mundari = "चिलका होबाः ओ अम।"
        # First ensure this arbitrary sentence is NOT in registry
        if self.service.registry_provider:
            self.assertFalse(self.service.registry_provider.has_entry(arbitrary_mundari, "mundari"))

        result, err = self.service.synthesize(arbitrary_mundari, "mundari", use_teacher_voice=True)
        self.assertIsNone(err)
        self.assertIsNotNone(result)
        # MUST BE BLOCKED: teacher_voice_applied MUST be False!
        self.assertFalse(result.teacher_voice_applied)
        self.assertEqual(result.verification_status, "SYNTHETIC_GENERATED_TTS")

    def test_07_deterministic_caching_hit(self):
        """Calling synthesis a second time returns cached audio."""
        text = "पाँच"
        # First call ensures it's cached
        res1, _ = self.service.synthesize(text, "hindi", use_teacher_voice=True)
        self.assertIsNotNone(res1)

        # Second call must hit cache
        res2, _ = self.service.synthesize(text, "hindi", use_teacher_voice=True)
        self.assertIsNotNone(res2)
        self.assertTrue(res2.is_cached)
        self.assertTrue(res2.teacher_voice_applied)
        self.assertEqual(res1.audio_bytes, res2.audio_bytes)


class TestTeacherVoiceAPIEndpoints(unittest.TestCase):
    """Verifies HTTP server endpoints for Teacher Voice."""

    @classmethod
    def setUpClass(cls):
        # Start a test HTTPServer on an ephemeral port
        cls.server = HTTPServer(("127.0.0.1", 0), PrototypeBridgeHandler)
        cls.port = cls.server.server_address[1]
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _post_json(self, path, payload):
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        return urllib.request.urlopen(req)

    def test_01_get_status_endpoint(self):
        """GET /api/teacher-voice/status returns 200 with structured status."""
        url = f"{self.base_url}/api/teacher-voice/status"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("status", data)
            self.assertIn("ui_state_label", data)
            self.assertIn("enrolled", data)

    def test_02_post_pronunciation_with_teacher_voice_header(self):
        """POST /api/pronunciation sets X-Pronunciation-Teacher-Voice: ACTIVE for Hindi."""
        payload = {"text": "नमस्ते", "language": "hindi", "teacher_voice": True}
        resp = self._post_json("/api/pronunciation", payload)
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.headers.get("Content-Type"), "audio/wav")
        self.assertEqual(resp.headers.get("X-Pronunciation-Teacher-Voice"), "ACTIVE")
        self.assertEqual(resp.headers.get("X-Pronunciation-Validation-Status"), "TEACHER_ADAPTED_SYNTHETIC")

    def test_03_post_pronunciation_arbitrary_mundari_blocked_header(self):
        """POST /api/pronunciation sets X-Pronunciation-Teacher-Voice: BLOCKED_UNCONTROLLED_MUNDARI."""
        payload = {"text": "चिलका होबाः ओ अम।", "language": "mundari", "teacher_voice": True}
        resp = self._post_json("/api/pronunciation", payload)
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.headers.get("X-Pronunciation-Teacher-Voice"), "BLOCKED_UNCONTROLLED_MUNDARI")
        self.assertEqual(resp.headers.get("X-Pronunciation-Validation-Status"), "SYNTHETIC_GENERATED_TTS")

    def test_04_toggle_endpoint(self):
        """POST /api/teacher-voice/toggle enables and disables voice profile."""
        # Disable
        resp = self._post_json("/api/teacher-voice/toggle", {"enabled": False})
        data = json.loads(resp.read().decode("utf-8"))
        self.assertFalse(data["enabled"])

        # Re-enable
        resp = self._post_json("/api/teacher-voice/toggle", {"enabled": True})
        data = json.loads(resp.read().decode("utf-8"))
        self.assertTrue(data["enabled"])

    def test_05_delete_and_re_enroll_profile(self):
        """DELETE /api/teacher-voice/profile clears profile, and re-enrollment restores it."""
        # 1. DELETE
        req = urllib.request.Request(f"{self.base_url}/api/teacher-voice/profile", method="DELETE")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "SUCCESS")

        # 2. Check status is now UNAVAILABLE
        with urllib.request.urlopen(f"{self.base_url}/api/teacher-voice/status") as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertFalse(data["enrolled"])
            self.assertEqual(data["ui_state_label"], "Teacher voice unavailable")

        # 3. Restore profile from verified reference so workspace remains functional
        ref_path = os.path.join(PROJECT_ROOT, "scratch", "voice_conversion_test", "reference_human.wav")
        if os.path.exists(ref_path):
            from server import pronunciation_service
            if pronunciation_service.teacher_voice_manager:
                pronunciation_service.teacher_voice_manager.enroll_from_file(ref_path)

    def test_06_frontend_ui_status_mapping_contract(self):
        """Verifies strict UI status mapping invariants in frontend/index.html."""
        frontend_html = os.path.join(PROJECT_ROOT, "frontend", "index.html")
        with open(frontend_html, "r", encoding="utf-8") as f:
            html = f.read()

        # Invariant 1: PROTOTYPE_ONLY_PENDING_HUMAN_VALIDATION maps to 'Prototype audio — pending language validation'
        self.assertIn('"Prototype audio — pending language validation"', html)
        self.assertIn('valStatusHeader === "PROTOTYPE_ONLY_PENDING_HUMAN_VALIDATION"', html)

        # Invariant 2: Teacher-adapted audio for converted speech
        self.assertIn('"Teacher-adapted audio"', html)

        # Invariant 3: Synthetic warning for arbitrary Mundari
        self.assertIn('"Synthetic pronunciation — review before classroom use"', html)

        # Invariant 4: Verified classroom audio strictly restricted to HUMAN_VALIDATED or CANONICAL_APPROVED
        self.assertIn('valStatusHeader === "HUMAN_VALIDATED" || valStatusHeader === "CANONICAL_APPROVED"', html)

        # Invariant 5: PROTOTYPE_ONLY_PENDING_HUMAN_VALIDATION is NOT mapped to 'Verified classroom audio'
        self.assertNotIn(
            'valStatusHeader === "PROTOTYPE_ONLY_PENDING_HUMAN_VALIDATION" {\n          label.textContent = "Verified classroom audio"',
            html
        )


if __name__ == "__main__":
    unittest.main()
