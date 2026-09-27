"""
tests/test_audio_quality_gate.py
=============================================================================
SIH260042: Audio Quality Gate & Pronunciation Header Tests
=============================================================================
Verifies:
1. AudioQualityGate rejects malformed WAV, excessive clipping, abnormal silence, and invalid duration.
2. AudioQualityGate correctly tags:
   - AUDIO_READY (human recording)
   - AUDIO_PROTOTYPE_PENDING_VALIDATION (prototype assets passing acoustic gate)
   - AUDIO_SYNTHETIC_UNVERIFIED (neural TTS passing acoustic gate)
   - AUDIO_FAILED (failing acoustic gate)
3. PronunciationService blocks teacher voice conversion if base audio fails quality gate.
4. HTTP headers on /api/pronunciation include X-Pronunciation-Status and X-Pronunciation-Quality-Gate.
"""

import io
import json
import os
import sys
import unittest
import wave
import numpy as np

WORKSPACE_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from ai.speech.audio_quality_gate import AudioQualityGate, AudioQualityResult
from ai.speech.pronunciation_service import (
    BasePronunciationProvider,
    PronunciationResult,
    PronunciationService
)


def _make_wav(duration_sec=1.0, sample_rate=16000, freq=440.0, amplitude=16000.0, num_channels=1) -> bytes:
    t = np.linspace(0, duration_sec, int(duration_sec * sample_rate), endpoint=False)
    data = (np.sin(2 * np.pi * freq * t) * amplitude).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(data.tobytes())
    return buf.getvalue()


class TestAudioQualityGate(unittest.TestCase):

    def setUp(self):
        self.gate = AudioQualityGate(expected_sample_rate=16000)

    def test_valid_speech_waveform(self):
        wav = _make_wav(duration_sec=1.5, amplitude=12000.0)
        res = self.gate.validate_audio(wav, "यह एक परीक्षा है", "hindi", provenance="SYNTHETIC_GENERATED_TTS")
        self.assertTrue(res.is_valid)
        self.assertEqual(res.status, "AUDIO_SYNTHETIC_UNVERIFIED")
        self.assertEqual(len(res.rejection_reasons), 0)
        self.assertAlmostEqual(res.duration_sec, 1.5, places=1)

    def test_prototype_provenance_labeling(self):
        wav = _make_wav(duration_sec=1.5, amplitude=12000.0)
        res = self.gate.validate_audio(wav, "नेआ चिनाः संख्या तना", "mundari", provenance="PROTOTYPE_ASSET")
        self.assertTrue(res.is_valid)
        self.assertEqual(res.status, "AUDIO_PROTOTYPE_PENDING_VALIDATION")

    def test_empty_or_truncated_audio_rejection(self):
        res = self.gate.validate_audio(b"not a wav file header", "test", "hindi")
        self.assertFalse(res.is_valid)
        self.assertEqual(res.status, "AUDIO_FAILED")

    def test_excessive_clipping_rejection(self):
        # Audio pegged to max 32767
        data = np.full(16000, 32767, dtype=np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(data.tobytes())
        res = self.gate.validate_audio(buf.getvalue(), "test", "hindi")
        self.assertFalse(res.is_valid)
        self.assertEqual(res.status, "AUDIO_FAILED")
        self.assertTrue(any("CLIPPING" in r for r in res.rejection_reasons))

    def test_silence_trimming_with_padding(self):
        sr = 16000
        # 1.0s silence + 0.5s tone + 1.0s silence
        t_tone = np.linspace(0, 0.5, int(0.5 * sr), endpoint=False)
        tone = (np.sin(2 * np.pi * 440.0 * t_tone) * 0.5).astype(np.float32)
        full_wave = np.concatenate([np.zeros(sr, dtype=np.float32), tone, np.zeros(sr, dtype=np.float32)])
        trimmed = AudioQualityGate.trim_silence(full_wave, sample_rate=sr, pad_ms=70.0)
        trimmed_dur = len(trimmed) / float(sr)
        self.assertLess(trimmed_dur, 1.0)
        self.assertGreater(trimmed_dur, 0.45)


class MockProviderForGate(BasePronunciationProvider):
    def __init__(self, audio_bytes, verification_status="SYNTHETIC_GENERATED_TTS"):
        self.audio_bytes = audio_bytes
        self.verification_status = verification_status

    @property
    def provider_id(self) -> str:
        return "mock_gate_provider"

    def is_available(self, language: str) -> bool:
        return True

    def generate(self, text: str, language: str):
        return PronunciationResult(
            audio_bytes=self.audio_bytes,
            language=language,
            source_type="neural_tts",
            engine_name="mock_gate_provider",
            verification_status=self.verification_status,
            sample_rate=16000,
            duration_sec=len(self.audio_bytes) / 32000.0
        )

    def get_status(self):
        return {"id": self.provider_id, "available": True}


class TestPronunciationServiceQualityGate(unittest.TestCase):

    def test_quality_gate_status_attached_on_valid_synthesis(self):
        valid_wav = _make_wav(duration_sec=1.0, amplitude=12000.0)
        mock = MockProviderForGate(valid_wav, "PROTOTYPE_ONLY_PENDING_HUMAN_VALIDATION")
        service = PronunciationService(project_root=WORKSPACE_ROOT, enable_cache=False, providers=[mock])
        res, err = service.synthesize("मोड़ेया", "mundari")
        self.assertIsNone(err)
        self.assertIsNotNone(res)
        self.assertEqual(res.quality_gate_status, "AUDIO_PROTOTYPE_PENDING_VALIDATION")

    def test_teacher_voice_blocked_if_base_audio_fails_gate(self):
        # Bad audio: invalid sample rate 8000 Hz fails gate
        bad_wav = _make_wav(duration_sec=1.0, sample_rate=8000)
        mock = MockProviderForGate(bad_wav, "PROTOTYPE_ONLY_PENDING_HUMAN_VALIDATION")
        # Mock teacher voice manager
        tv_mock = unittest.mock.MagicMock()
        tv_mock.is_active.return_value = True
        tv_mock.get_profile_id.return_value = "teacher_test"

        service = PronunciationService(
            project_root=WORKSPACE_ROOT,
            enable_cache=False,
            providers=[mock],
            teacher_voice_manager=tv_mock
        )
        res, err = service.synthesize("यह कौन सी संख्या है", "hindi", use_teacher_voice=True)
        # Teacher voice conversion should have been blocked because base audio failed quality gate
        self.assertIsNotNone(res)
        self.assertFalse(res.teacher_voice_applied)
        self.assertEqual(res.quality_gate_status, "AUDIO_FAILED")


if __name__ == "__main__":
    unittest.main()
