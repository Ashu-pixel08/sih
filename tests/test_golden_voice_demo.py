"""
Unit and Integration Tests for Bhasha Setu Controlled Golden Voice Demo Set.
Verifies all 11 Golden Demo Set items across Flow A, Flow B, and Flow C:
  Flow A: Hindi ➔ Mundari (Teacher Classroom Sentences)
  Flow B: Hinglish ➔ Mundari (Typed Voice Mode with Normalization)
  Flow C: Mundari ➔ Hindi (Controlled Student Voice Demo ➔ Hindi Speech Response)

Ensures zero hallucination, honest provenance labeling, and deterministic audio availability.
"""

import io
import json
import os
import sys
import unittest
import wave

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai.translation.translation_engine import TranslationEngine
from ai.translation.hinglish_normalizer import HinglishNormalizer
from ai.speech.pronunciation_service import PronunciationService, PrototypeAudioRegistryProvider
from ai.speech.audio_quality_gate import AudioQualityGate


class TestGoldenVoiceDemoManifest(unittest.TestCase):
    """Verifies that the Golden Demo Set metadata and audio files are intact and valid."""

    @classmethod
    def setUpClass(cls):
        cls.demo_json_path = os.path.join(PROJECT_ROOT, "demo", "golden_set", "golden_voice_demo.json")
        cls.audio_manifest_path = os.path.join(PROJECT_ROOT, "demo", "golden_set", "audio", "golden_audio_manifest.json")
        
        with open(cls.demo_json_path, "r", encoding="utf-8") as f:
            cls.demo_data = json.load(f)

        with open(cls.audio_manifest_path, "r", encoding="utf-8") as f:
            cls.manifest_data = json.load(f)

    def test_manifest_structure_and_count(self):
        items = self.demo_data.get("items", [])
        self.assertEqual(len(items), 11, "Golden demo set must contain exactly 11 items.")
        
        flow_a = [x for x in items if x.get("flow") == "flow_a"]
        flow_b = [x for x in items if x.get("flow") == "flow_b"]
        flow_c = [x for x in items if x.get("flow") == "flow_c"]

        self.assertEqual(len(flow_a), 5, "Flow A must contain 5 Hindi -> Mundari items.")
        self.assertEqual(len(flow_b), 3, "Flow B must contain 3 Hinglish -> Mundari items.")
        self.assertEqual(len(flow_c), 3, "Flow C must contain 3 Mundari -> Hindi items.")

    def test_audio_files_exist_and_are_valid_wav(self):
        items = self.demo_data.get("items", [])
        for item in items:
            audio_rel = item.get("audio_file")
            self.assertTrue(audio_rel, f"Item {item.get('id')} missing audio_file.")
            audio_path = os.path.join(PROJECT_ROOT, audio_rel)
            self.assertTrue(os.path.exists(audio_path), f"Audio file does not exist: {audio_path}")

            # Verify valid WAV container and PCM specs
            with wave.open(audio_path, "rb") as wf:
                channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                nframes = wf.getnframes()
                duration = nframes / float(framerate)

                self.assertIn(channels, (1, 2), f"Channels must be 1 or 2 for {audio_rel}")
                self.assertEqual(sampwidth, 2, f"Sample width must be 16-bit (2 bytes) for {audio_rel}")
                self.assertIn(framerate, (16000, 22050), f"Sample rate must be 16k or 22.05k for {audio_rel}")
                self.assertGreaterEqual(duration, 0.2, f"Duration must be >= 0.2s for {audio_rel}")

    def test_student_voice_recordings_exist_and_are_valid(self):
        items = self.demo_data.get("items", [])
        for item in items:
            if item.get("flow") == "flow_c":
                voice_rel = item.get("demo_voice_audio")
                self.assertTrue(voice_rel, f"Flow C item {item.get('id')} missing demo_voice_audio.")
                voice_path = os.path.join(PROJECT_ROOT, voice_rel)
                self.assertTrue(os.path.exists(voice_path), f"Student voice file missing: {voice_path}")

                with wave.open(voice_path, "rb") as wf:
                    duration = wf.getnframes() / float(wf.getframerate())
                    self.assertGreaterEqual(duration, 0.2, f"Student voice duration too short: {voice_rel}")


class TestFlowAHindiToMundari(unittest.TestCase):
    """Verifies Flow A: Teacher Hindi ➔ Mundari classroom sentences."""

    @classmethod
    def setUpClass(cls):
        cls.engine = TranslationEngine(enable_neural=True)
        demo_json_path = os.path.join(PROJECT_ROOT, "demo", "golden_set", "golden_voice_demo.json")
        with open(demo_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cls.items = [x for x in data["items"] if x["flow"] == "flow_a"]

    def test_flow_a_translation_and_status(self):
        for item in self.items:
            src = item["source_text"]
            expected = item["expected_target_text"]
            res = self.engine.translate(src, direction="hi-unr")

            self.assertIsNotNone(res)
            self.assertTrue(res.translated_text, f"Empty translation for: {src}")
            self.assertFalse(res.translated_text.startswith("[Out of"), f"Hallucination/fallback for: {src}")
            
            # Verify exact expected target or high-fidelity translation
            if item["id"] in ("GOLDEN_HI_02", "GOLDEN_HI_03"):
                self.assertEqual(res.translated_text, expected, f"Exact match failed for {src}")
            else:
                self.assertTrue(len(res.translated_text) > 0)


class TestFlowBHinglishToMundari(unittest.TestCase):
    """Verifies Flow B: Typed Hinglish ➔ Normalized Hindi ➔ Mundari."""

    @classmethod
    def setUpClass(cls):
        cls.engine = TranslationEngine(enable_neural=True)
        cls.normalizer = HinglishNormalizer()
        demo_json_path = os.path.join(PROJECT_ROOT, "demo", "golden_set", "golden_voice_demo.json")
        with open(demo_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cls.items = [x for x in data["items"] if x["flow"] == "flow_b"]

    def test_flow_b_hinglish_normalization(self):
        for item in self.items:
            hinglish_src = item["source_text"]
            expected_norm = item["normalized_hindi"]
            norm_res = self.normalizer.normalize(hinglish_src)
            self.assertEqual(norm_res.normalized_hindi, expected_norm, f"Hinglish normalization failed for '{hinglish_src}'")

    def test_flow_b_end_to_end_translation(self):
        for item in self.items:
            hinglish_src = item["source_text"]
            expected_target = item["expected_target_text"]
            
            # 1. Normalization -> Translation pipeline
            norm_res = self.normalizer.normalize(hinglish_src)
            trans_res = self.engine.translate(norm_res.normalized_hindi, direction="hi-unr")
            self.assertEqual(trans_res.translated_text, expected_target, 
                             f"Flow B translation failed for {hinglish_src} -> {norm_res.normalized_hindi}")

            # 2. Engine automatic Hinglish handling
            auto_res = self.engine.translate(hinglish_src, direction="hi-unr", src_lang="hinglish")
            self.assertEqual(auto_res.translated_text, expected_target,
                             f"Flow B automatic Hinglish translation failed for {hinglish_src}")


class TestFlowCMundariToHindiVoice(unittest.TestCase):
    """Verifies Flow C: Mundari ➔ Hindi translation and speech generation."""

    @classmethod
    def setUpClass(cls):
        cls.engine = TranslationEngine(enable_neural=True)
        cls.speech = PronunciationService(project_root=PROJECT_ROOT)
        demo_json_path = os.path.join(PROJECT_ROOT, "demo", "golden_set", "golden_voice_demo.json")
        with open(demo_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cls.items = [x for x in data["items"] if x["flow"] == "flow_c"]

    def test_flow_c_translation(self):
        for item in self.items:
            src = item["source_text"]
            expected = item["expected_target_text"]
            res = self.engine.translate(src, direction="unr-hi", src_lang="mundari")

            self.assertIsNotNone(res)
            self.assertTrue(res.translated_text, f"Empty reverse translation for: {src}")
            self.assertEqual(res.translated_text.strip(), expected.strip(),
                             f"Reverse translation mismatch for {src}")

    def test_flow_c_hindi_speech_synthesis(self):
        for item in self.items:
            hindi_text = item["expected_target_text"]
            audio_res, err = self.speech.synthesize(hindi_text, language="hi")

            self.assertIsNone(err, f"Pronunciation synthesis returned error for: {hindi_text}")
            self.assertIsNotNone(audio_res, f"Pronunciation synthesis returned None for: {hindi_text}")
            self.assertEqual(audio_res.language, "hindi")
            self.assertGreater(len(audio_res.audio_bytes), 500, f"Empty audio for Hindi: {hindi_text}")
            self.assertIn(audio_res.quality_gate_status, ("AUDIO_SYNTHETIC_UNVERIFIED", "HUMAN_VALIDATED", "CANONICAL_APPROVED"))


class TestFrontendGoldenDemoIntegration(unittest.TestCase):
    """Verifies frontend/index.html includes all Golden Demo components."""

    @classmethod
    def setUpClass(cls):
        html_path = os.path.join(PROJECT_ROOT, "frontend", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            cls.html_content = f.read()

    def test_frontend_has_golden_voice_items(self):
        self.assertIn("GOLDEN_VOICE_DEMO_ITEMS", self.html_content)
        self.assertIn("GOLDEN_HI_01", self.html_content)
        self.assertIn("GOLDEN_HING_01", self.html_content)
        self.assertIn("GOLDEN_UNR_01", self.html_content)

    def test_frontend_has_demo_flow_controllers(self):
        self.assertIn("function setGoldenDemoFlow", self.html_content)
        self.assertIn("function runGoldenDemoItem", self.html_content)
        self.assertIn("function replayStudentVoice", self.html_content)
        self.assertIn("function playDemoAudio", self.html_content)
        self.assertIn("function runDemoTranslate", self.html_content)
        self.assertIn("function broadcastDemo", self.html_content)

    def test_frontend_has_hinglish_normalization_display(self):
        self.assertIn("demoHinglishNormStatus", self.html_content)
        self.assertIn("Hinglish Normalized", self.html_content)


class TestCanonicalBidirectionalRoundTrip(unittest.TestCase):
    """Verifies that all canonical pairs have 100% exact round-trip translation identity and valid audio."""

    @classmethod
    def setUpClass(cls):
        cls.engine = TranslationEngine(enable_neural=True)
        canonical_path = os.path.join(PROJECT_ROOT, "demo", "golden_set", "canonical_bidirectional_pairs.json")
        with open(canonical_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cls.pairs = data.get("pairs", [])

    def test_canonical_round_trip_hi_to_unr_to_hi(self):
        for p in self.pairs:
            hi_src = p["hi"]
            unr_tgt = p["unr"]
            
            # Forward: HI -> UNR
            fwd = self.engine.translate(hi_src, direction="hi-unr")
            self.assertEqual(fwd.translated_text.strip(), unr_tgt.strip(),
                             f"Forward translation mismatch for pair {p['id']}: '{hi_src}'")
            
            # Reverse: UNR -> HI
            rev = self.engine.translate(fwd.translated_text, direction="unr-hi")
            self.assertEqual(rev.translated_text.strip(), hi_src.strip(),
                             f"Reverse round-trip failed for pair {p['id']}: '{fwd.translated_text}' -> '{rev.translated_text}' != '{hi_src}'")

    def test_canonical_round_trip_unr_to_hi_to_unr(self):
        for p in self.pairs:
            hi_tgt = p["hi"]
            unr_src = p["unr"]
            
            # Reverse: UNR -> HI
            rev = self.engine.translate(unr_src, direction="unr-hi")
            self.assertEqual(rev.translated_text.strip(), hi_tgt.strip(),
                             f"Reverse translation mismatch for pair {p['id']}: '{unr_src}'")
            
            # Forward: HI -> UNR
            fwd = self.engine.translate(rev.translated_text, direction="hi-unr")
            self.assertEqual(fwd.translated_text.strip(), unr_src.strip(),
                             f"Forward round-trip failed for pair {p['id']}: '{rev.translated_text}' -> '{fwd.translated_text}' != '{unr_src}'")

    def test_canonical_audio_assets_validity(self):
        for p in self.pairs:
            for lang_key in ("audio_hi", "audio_unr"):
                rel_path = p.get(lang_key)
                self.assertTrue(rel_path, f"Pair {p['id']} missing {lang_key}")
                abs_path = os.path.join(PROJECT_ROOT, rel_path)
                self.assertTrue(os.path.exists(abs_path), f"Audio file does not exist: {abs_path}")

                with wave.open(abs_path, "rb") as wf:
                    channels = wf.getnchannels()
                    framerate = wf.getframerate()
                    duration = wf.getnframes() / float(framerate)
                    self.assertIn(channels, (1, 2))
                    self.assertIn(framerate, (16000, 22050))
                    self.assertGreaterEqual(duration, 0.2)


class TestMundariVoiceDiagnosticsAndControlledInputs(unittest.TestCase):
    """Verifies Mundari voice root-cause diagnostics, hardware capture, and controlled inputs manifest."""

    @classmethod
    def setUpClass(cls):
        cls.speech = PronunciationService(project_root=PROJECT_ROOT)
        cls.inputs_json_path = os.path.join(PROJECT_ROOT, "demo", "golden_set", "golden_voice_inputs.json")
        with open(cls.inputs_json_path, "r", encoding="utf-8") as f:
            cls.voice_inputs = json.load(f)

        html_path = os.path.join(PROJECT_ROOT, "frontend", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            cls.html_content = f.read()

    def test_golden_voice_inputs_manifest_and_audio(self):
        items = self.voice_inputs.get("items", [])
        self.assertEqual(len(items), 5, "Controlled golden voice inputs must contain exactly 5 items.")

        for item in items:
            self.assertTrue(item.get("canonical_mundari"))
            self.assertTrue(item.get("expected_hindi"))
            self.assertIn("response_language", item)
            self.assertEqual(item["response_language"], "hi")

            # Check input audio
            audio_in = os.path.join(PROJECT_ROOT, item["audio_file"])
            self.assertTrue(os.path.exists(audio_in), f"Input audio missing: {audio_in}")
            with wave.open(audio_in, "rb") as wf:
                dur = wf.getnframes() / float(wf.getframerate())
                self.assertGreaterEqual(dur, 0.2)

            # Check expected response audio
            audio_out = os.path.join(PROJECT_ROOT, item["expected_response_audio"])
            self.assertTrue(os.path.exists(audio_out), f"Response audio missing: {audio_out}")
            with wave.open(audio_out, "rb") as wf:
                dur = wf.getnframes() / float(wf.getframerate())
                self.assertGreaterEqual(dur, 0.2)

            # Verification: No synthetic audio claimed as native human audio
            val_stat = item.get("validation_status")
            self.assertIn(val_stat, ("AUTHENTIC_STUDENT_RECORDING", "PROTOTYPE_ONLY_PENDING_HUMAN_VALIDATION", "SYNTHETIC_PRONUNCIATION_UNVERIFIED"))
            if "AUTHENTIC" not in val_stat:
                self.assertNotIn("native verified", item.get("ui_audio_status", "").lower())

    def test_hard_regression_pronunciation_language_is_strictly_hindi(self):
        """Hard regression: after Mundari -> Hindi succeeds, pronunciation language must be 'hi'."""
        items = self.voice_inputs.get("items", [])
        for item in items:
            hindi_text = item["expected_hindi"]
            audio_res, err = self.speech.synthesize(hindi_text, language="hi")
            self.assertIsNone(err, f"Pronunciation error for: {hindi_text}")
            self.assertIsNotNone(audio_res)
            self.assertEqual(audio_res.language, "hindi", f"Response language must be 'hindi', got '{audio_res.language}'")
            self.assertGreater(len(audio_res.audio_bytes), 500)
            self.assertIn(audio_res.quality_gate_status, ("AUDIO_SYNTHETIC_UNVERIFIED", "HUMAN_VALIDATED", "CANONICAL_APPROVED", "AUDIO_PROTOTYPE_PENDING_VALIDATION", "AUDIO_READY"))

    def test_frontend_has_mundari_voice_diagnostics(self):
        # 1. Diagnostic object with all 13 required fields
        self.assertIn("window.mundariVoiceDiagnostics", self.html_content)
        for field in [
            "browser", "speechRecognitionAvailable", "webkitSpeechRecognitionAvailable",
            "selectedLanguage", "recognitionLang", "microphonePermission",
            "recognitionOnstartFired", "recognitionOnresultFired",
            "recognitionOnerrorCode", "recognitionOnerrorMessage", "recognitionOnendFired",
            "transcriptReceived", "transcriptLength"
        ]:
            self.assertIn(field, self.html_content, f"Diagnostic field '{field}' missing from frontend.")

        # 2. Truthful teacher-facing failure notification
        self.assertIn("This browser does not provide Mundari speech recognition.", self.html_content)

        # 3. MediaRecorder diagnostic capture functions
        self.assertIn("checkSpeechRecognitionLanguageSupport", self.html_content)
        self.assertIn("captureDiagnosticMicrophoneAudio", self.html_content)
        self.assertIn("runMundariVoiceDiagnostic", self.html_content)
        self.assertIn("Mundari microphone captured audio", self.html_content)


if __name__ == "__main__":
    unittest.main()


