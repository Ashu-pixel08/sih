"""
tests/test_pronunciation_service.py
=============================================================================
SIH260042: Unit & Integration Test Suite for Bhasha Setu Pronunciation Service
=============================================================================
"""

import io
import json
import os
import shutil
import sys
import unittest
import wave
from unittest.mock import MagicMock

# Ensure project root in sys.path
PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai.speech.pronunciation_service import (
    BasePronunciationProvider,
    PronunciationResult,
    PronunciationService,
    PrototypeAudioRegistryProvider,
    VitsTTSProvider,
)


def _create_dummy_wav(duration_sec: float = 0.5, sample_rate: int = 16000) -> bytes:
    """Helper to generate valid 16kHz PCM WAV bytes in memory."""
    import numpy as np
    num_samples = int(duration_sec * sample_rate)
    t = np.linspace(0, duration_sec, num_samples, endpoint=False)
    wave_data = (np.sin(2 * np.pi * 440.0 * t) * 16384.0).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(wave_data.tobytes())
    return buf.getvalue()


class MockPronunciationProvider(BasePronunciationProvider):
    """Mock provider for unit testing without depending on external model weights."""

    def __init__(self, available_langs=("hindi", "mundari")):
        self.available_langs = set(available_langs)
        self.invocations = []

    @property
    def provider_id(self) -> str:
        return "mock_provider"

    def is_available(self, language: str) -> bool:
        return language in self.available_langs

    def generate(self, text: str, language: str):
        if not self.is_available(language):
            return None
        self.invocations.append((text, language))
        return PronunciationResult(
            audio_bytes=_create_dummy_wav(),
            language=language,
            source_type="mock_audio",
            engine_name="mock_provider",
            verification_status="MOCK_TEST_AUDIO",
            sample_rate=16000,
            is_cached=False
        )

    def get_status(self):
        return {"provider_id": self.provider_id, "available_langs": list(self.available_langs)}


class TestPronunciationServiceValidation(unittest.TestCase):
    """Verifies input validation and security constraints."""

    def setUp(self):
        self.test_cache_dir = os.path.join(PROJECT_ROOT, "cache", "test_speech_validation")
        self.service = PronunciationService(
            project_root=PROJECT_ROOT,
            cache_dir=self.test_cache_dir,
            enable_cache=False,
            providers=[]
        )

    def tearDown(self):
        if os.path.exists(self.test_cache_dir):
            shutil.rmtree(self.test_cache_dir, ignore_errors=True)

    def test_empty_text_rejected(self):
        is_valid, _, _, msg = self.service.validate_request("", "hindi")
        self.assertFalse(is_valid)
        self.assertIn("non-empty", msg)

        is_valid, _, _, msg = self.service.validate_request("   \t\n", "hindi")
        self.assertFalse(is_valid)
        self.assertIn("non-empty", msg)

    def test_non_string_text_rejected(self):
        is_valid, _, _, msg = self.service.validate_request(None, "hindi")
        self.assertFalse(is_valid)
        self.assertIn("non-empty", msg)

    def test_long_text_rejected(self):
        long_text = "क" * 251
        is_valid, _, _, msg = self.service.validate_request(long_text, "hindi")
        self.assertFalse(is_valid)
        self.assertIn("maximum allowable length", msg)

    def test_valid_text_accepted(self):
        is_valid, clean_text, norm_lang, msg = self.service.validate_request("  नमस्ते  ", "hindi")
        self.assertTrue(is_valid)
        self.assertEqual(clean_text, "नमस्ते")
        self.assertEqual(norm_lang, "hindi")
        self.assertIsNone(msg)

    def test_language_normalization(self):
        self.assertEqual(self.service.normalize_language("hindi"), "hindi")
        self.assertEqual(self.service.normalize_language("HINDI"), "hindi")
        self.assertEqual(self.service.normalize_language("hi"), "hindi")
        self.assertEqual(self.service.normalize_language("mundari"), "mundari")
        self.assertEqual(self.service.normalize_language("Mundari"), "mundari")
        self.assertEqual(self.service.normalize_language("unr"), "mundari")
        self.assertIsNone(self.service.normalize_language("french"))
        self.assertIsNone(self.service.normalize_language(""))

    def test_unsupported_language_rejected(self):
        is_valid, _, _, msg = self.service.validate_request("Hello", "spanish")
        self.assertFalse(is_valid)
        self.assertIn("Unsupported language", msg)


class TestPronunciationServiceCachingAndSecurity(unittest.TestCase):
    """Verifies deterministic caching and path traversal safety."""

    def setUp(self):
        self.test_cache_dir = os.path.join(PROJECT_ROOT, "cache", "test_speech_cache")
        os.makedirs(self.test_cache_dir, exist_ok=True)
        self.mock_provider = MockPronunciationProvider(available_langs=("hindi", "mundari"))
        self.service = PronunciationService(
            project_root=PROJECT_ROOT,
            cache_dir=self.test_cache_dir,
            enable_cache=True,
            providers=[self.mock_provider]
        )

    def tearDown(self):
        if os.path.exists(self.test_cache_dir):
            shutil.rmtree(self.test_cache_dir, ignore_errors=True)

    def test_cache_miss_then_cache_hit(self):
        # 1. First call -> Cache MISS, invokes provider
        res1, err1 = self.service.synthesize("नमस्ते", "hindi")
        self.assertIsNone(err1)
        self.assertIsNotNone(res1)
        self.assertFalse(res1.is_cached)
        self.assertEqual(len(self.mock_provider.invocations), 1)

        # Verify cached files on disk (audio wav + metadata json)
        cache_files = os.listdir(self.test_cache_dir)
        wav_files = [f for f in cache_files if f.endswith(".wav")]
        json_files = [f for f in cache_files if f.endswith(".json")]
        self.assertEqual(len(wav_files), 1)
        self.assertEqual(len(json_files), 1)

        # 2. Second call with same text -> Cache HIT, does NOT invoke provider again
        res2, err2 = self.service.synthesize("नमस्ते", "hindi")
        self.assertIsNone(err2)
        self.assertIsNotNone(res2)
        self.assertTrue(res2.is_cached)
        self.assertEqual(len(self.mock_provider.invocations), 1)  # Count remains 1!
        self.assertEqual(res2.audio_bytes, res1.audio_bytes)

    def test_malicious_path_traversal_cannot_escape_cache(self):
        malicious_input = "../../../../windows/system32/cmd.exe"
        key = self.service._compute_cache_key(malicious_input, "hindi", "mock_id")
        file_path = self.service._get_cache_file_path(key)

        # Ensure the resolved path remains strictly inside the cache directory
        norm_file = os.path.normpath(file_path)
        norm_cache = os.path.normpath(self.test_cache_dir)
        self.assertTrue(norm_file.startswith(norm_cache))
        # Ensure filename contains only safe hex characters
        filename = os.path.basename(norm_file)
        self.assertTrue(filename.endswith(".wav"))
        stem = filename[:-4]
        self.assertTrue(all(c in "0123456789abcdef" for c in stem))
        self.assertEqual(len(stem), 64)


class TestPrototypeAudioRegistryProvider(unittest.TestCase):
    """Verifies that pre-rendered prototype audio assets can be retrieved and labeled correctly."""

    def setUp(self):
        self.provider = PrototypeAudioRegistryProvider(project_root=PROJECT_ROOT)

    def test_prototype_registry_assets_loaded(self):
        self.assertGreaterEqual(self.provider.asset_count, 36)
        self.assertTrue(self.provider.is_available("mundari"))
        self.assertFalse(self.provider.is_available("hindi"))  # Manifest contains Mundari audio

    def test_lookup_numeral_five_moredia(self):
        """Verifies 'मोड़ेया' (Grade 1 numeral 5) retrieves actual prototype WAV audio."""
        res = self.provider.generate("मोड़ेया", "mundari")
        self.assertIsNotNone(res)
        self.assertEqual(res.language, "mundari")
        self.assertEqual(res.source_type, "prototype_asset")
        self.assertEqual(res.verification_status, "PROTOTYPE_ONLY_PENDING_HUMAN_VALIDATION")
        self.assertGreater(len(res.audio_bytes), 1000)

        # Verify valid WAV format
        with io.BytesIO(res.audio_bytes) as buf:
            with wave.open(buf, "rb") as wf:
                self.assertEqual(wf.getnchannels(), 1)
                self.assertEqual(wf.getsampwidth(), 2)
                self.assertEqual(wf.getframerate(), 16000)

    def test_lookup_greeting_johar(self):
        """Verifies 'जोहार' (classroom greeting) retrieves actual prototype WAV audio."""
        res = self.provider.generate("जोहार", "mundari")
        self.assertIsNotNone(res)
        self.assertEqual(res.language, "mundari")
        self.assertEqual(res.verification_status, "PROTOTYPE_ONLY_PENDING_HUMAN_VALIDATION")
        self.assertGreater(len(res.audio_bytes), 1000)

    def test_unregistered_phrase_returns_none(self):
        res = self.provider.generate("अज्ञात मुंडारी वाक्य", "mundari")
        self.assertIsNone(res)


class TestVitsTTSProviderUninstalledHandling(unittest.TestCase):
    """Verifies graceful and honest handling when neural models are uninstalled."""

    def setUp(self):
        self.vits_provider = VitsTTSProvider(project_root=PROJECT_ROOT)

    def test_uninstalled_model_is_not_available(self):
        # Unless the user explicitly ran scripts/download_tts_models.py, these should be False
        if not os.path.exists(os.path.join(PROJECT_ROOT, "models", "tts", "mms-tts-hin")):
            self.assertFalse(self.vits_provider.is_available("hindi"))
        if not os.path.exists(os.path.join(PROJECT_ROOT, "models", "tts", "mms-tts-unr")):
            self.assertFalse(self.vits_provider.is_available("mundari"))

    def test_uninstalled_model_generate_returns_none(self):
        if not self.vits_provider.is_available("hindi"):
            res = self.vits_provider.generate("नमस्ते", "hindi")
            self.assertIsNone(res)


class TestPronunciationServiceEndToEnd(unittest.TestCase):
    """Verifies end-to-end service orchestration and health diagnostics."""

    def setUp(self):
        self.test_cache_dir = os.path.join(PROJECT_ROOT, "cache", "test_speech_e2e")
        if os.path.exists(self.test_cache_dir):
            shutil.rmtree(self.test_cache_dir, ignore_errors=True)
        os.makedirs(self.test_cache_dir, exist_ok=True)
        self.service = PronunciationService(
            project_root=PROJECT_ROOT,
            cache_dir=self.test_cache_dir,
            enable_cache=True
        )

    def tearDown(self):
        if os.path.exists(self.test_cache_dir):
            shutil.rmtree(self.test_cache_dir, ignore_errors=True)

    def test_health_status_reflects_truth(self):
        health = self.service.get_health_status()
        self.assertEqual(health["status"], "HEALTHY")
        self.assertEqual(health["cache"], "enabled")
        # Mundari is available via PrototypeAudioRegistryProvider for FLN vocabulary
        self.assertEqual(health["mundari"], "available")
        # Hindi is unavailable unless MMS-TTS or a local Hindi engine was downloaded
        if not os.path.exists(os.path.join(PROJECT_ROOT, "models", "tts", "mms-tts-hin")):
            self.assertEqual(health["hindi"], "unavailable")

    def test_end_to_end_mundari_attested_success(self):
        res, err = self.service.synthesize("मोड़ेया", "mundari")
        self.assertIsNone(err)
        self.assertIsNotNone(res)
        self.assertEqual(res.source_type, "prototype_asset")
        self.assertEqual(res.verification_status, "PROTOTYPE_ONLY_PENDING_HUMAN_VALIDATION")
        self.assertGreater(len(res.audio_bytes), 1000)

    def test_end_to_end_hindi_unavailable_without_model(self):
        if not os.path.exists(os.path.join(PROJECT_ROOT, "models", "tts", "mms-tts-hin")):
            res, err = self.service.synthesize("पाँच", "hindi")
            self.assertIsNone(res)
            self.assertIsNotNone(err)
            self.assertEqual(err["status"], "UNAVAILABLE")
            self.assertEqual(err["http_code"], 503)
            self.assertIn("facebook/mms-tts-hin", err["details"])


class TestPronunciationHttpApi(unittest.TestCase):
    """Verifies the HTTP endpoint behavior of /api/pronunciation and /api/health."""

    @classmethod
    def setUpClass(cls):
        import threading
        import urllib.request
        from http.server import HTTPServer
        from server import PrototypeBridgeHandler

        # Start an ephemeral test server
        cls.server = HTTPServer(("localhost", 0), PrototypeBridgeHandler)
        cls.port = cls.server.server_port
        cls.base_url = f"http://localhost:{cls.port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _post_json(self, endpoint, data):
        import urllib.error
        import urllib.request
        url = f"{self.base_url}{endpoint}"
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, dict(resp.headers), resp.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

    def test_http_health_contains_truthful_pronunciation(self):
        import urllib.request
        url = f"{self.base_url}/api/health"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("pronunciation", data)
            p = data["pronunciation"]
            self.assertEqual(p["cache"], "enabled")
            self.assertEqual(p["mundari"], "available")
            if not os.path.exists(os.path.join(PROJECT_ROOT, "models", "tts", "mms-tts-hin")):
                self.assertEqual(p["hindi"], "unavailable")

    def test_http_empty_text_returns_400(self):
        status, headers, body = self._post_json("/api/pronunciation", {"text": "", "language": "hindi"})
        self.assertEqual(status, 400)
        self.assertIn("application/json", headers.get("Content-Type", ""))
        err = json.loads(body.decode("utf-8"))
        self.assertEqual(err["status"], "INVALID_INPUT")

    def test_http_unsupported_language_returns_400(self):
        status, headers, body = self._post_json("/api/pronunciation", {"text": "hello", "language": "latin"})
        self.assertEqual(status, 400)
        self.assertIn("application/json", headers.get("Content-Type", ""))
        err = json.loads(body.decode("utf-8"))
        self.assertIn("Unsupported language", err["message"])

    def test_http_long_text_returns_400(self):
        status, headers, body = self._post_json("/api/pronunciation", {"text": "अ" * 251, "language": "hindi"})
        self.assertEqual(status, 400)
        err = json.loads(body.decode("utf-8"))
        self.assertIn("maximum allowable length", err["message"])

    def test_http_mundari_attested_returns_wav(self):
        status, headers, body = self._post_json("/api/pronunciation", {"text": "मोड़ेया", "language": "mundari"})
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Content-Type"), "audio/wav")
        self.assertEqual(headers.get("X-Pronunciation-Language"), "mundari")
        self.assertEqual(headers.get("X-Pronunciation-Engine"), "prototype_audio_registry")
        self.assertEqual(headers.get("X-Pronunciation-Validation-Status"), "PROTOTYPE_ONLY_PENDING_HUMAN_VALIDATION")
        self.assertGreater(len(body), 1000)

        # Check valid WAV header
        with io.BytesIO(body) as b:
            with wave.open(b, "rb") as wf:
                self.assertEqual(wf.getnchannels(), 1)
                self.assertEqual(wf.getsampwidth(), 2)
                self.assertEqual(wf.getframerate(), 16000)

    def test_http_hindi_uninstalled_returns_503(self):
        if not os.path.exists(os.path.join(PROJECT_ROOT, "models", "tts", "mms-tts-hin")):
            status, headers, body = self._post_json("/api/pronunciation", {"text": "पाँच", "language": "hindi"})
            self.assertEqual(status, 503)
            self.assertIn("application/json", headers.get("Content-Type", ""))
            err = json.loads(body.decode("utf-8"))
            self.assertEqual(err["status"], "UNAVAILABLE")
            self.assertEqual(err["language"], "hindi")


if __name__ == "__main__":
    unittest.main()

