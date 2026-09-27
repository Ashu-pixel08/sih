"""
tests/test_student_voice_pipeline.py
=============================================================================
Bhasha Setu: Student Mundari -> Hindi Voice Response Pipeline Tests
=============================================================================
Verifies the end-to-end Mundari -> Hindi voice response pipeline:
1. Spoken / typed Mundari input -> recognized Mundari text.
2. Mundari -> Hindi translation.
3. Target language determines pronunciation (target=Hindi -> Hindi MMS-TTS).
4. Audio synthesis via PronunciationService and /api/pronunciation endpoint.
5. Frontend contracts: playTranslatedSpeech, sendStudentReply, submitStudentTypedMundari,
   studentVoiceMode direction locking, and state machine transitions.
6. Error handling and user-facing notifications.
"""

import os
import sys
import json
import urllib.parse
import pytest

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from ai.translation.translation_engine import TranslationEngine
from ai.speech.pronunciation_service import PronunciationService
FRONTEND_HTML = os.path.join(WORKSPACE_ROOT, "frontend", "index.html")


@pytest.fixture(scope="module")
def html_content():
    with open(FRONTEND_HTML, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def translation_engine():
    return TranslationEngine(enable_neural=True)


@pytest.fixture(scope="module")
def pronunciation_service():
    return PronunciationService(project_root=WORKSPACE_ROOT)


class TestStudentVoiceFrontendContracts:
    """Verifies all required frontend functions, handlers, and telemetry in frontend/index.html."""

    def test_play_translated_speech_defined(self, html_content):
        assert "async function playTranslatedSpeech(options)" in html_content
        assert "window.playTranslatedSpeech = playTranslatedSpeech" in html_content

    def test_send_student_reply_defined(self, html_content):
        assert "async function sendStudentReply(rawText)" in html_content
        assert "window.sendStudentReply = sendStudentReply" in html_content

    def test_student_voice_mode_direction_locking(self, html_content):
        assert 'state.translationDirection = "unr-hi"' in html_content
        assert 'state.inputMode = "mundari"' in html_content

    def test_student_voice_mode_quick_phrases_routed_to_pipeline(self, html_content):
        assert "submitStudentMundariPhrase('ऐंग काजी बुझाओ केदा')" in html_content
        assert "submitStudentMundariPhrase('गुरु गोमके नेना काजी आर एमेप')" in html_content
        assert "submitStudentMundariPhrase('ऐंगा नाद कुड़ी मेनाअ')" in html_content
        assert "submitStudentMundariPhrase('सेब चिकिता दान रे जोवा')" in html_content
        assert "submitStudentMundariPhrase('ऐंग माद इहोन गेलिया धाब लेखा केदा')" in html_content

    def test_student_typed_input_supported(self, html_content):
        assert 'id="studentMundariInput"' in html_content
        assert "submitStudentTypedMundari()" in html_content
        assert "async function submitStudentTypedMundari()" in html_content

    def test_audio_state_machine_and_feedback_guard(self, html_content):
        # Verify microphone capture is paused or guarded during speaking
        assert "voiceState.isSpeaking" in html_content
        assert "setVoiceState(VoiceStateEnum.SPEAKING)" in html_content
        assert "setVoiceState(VoiceStateEnum.LISTENING)" in html_content

    def test_audio_failure_error_message(self, html_content):
        assert "Translation available, but Hindi audio could not be played." in html_content

    def test_required_telemetry_logs_present(self, html_content):
        assert '[STUDENT VOICE] Mundari recognition complete' in html_content
        assert '[STUDENT VOICE] Recognized:' in html_content
        assert '[TRANSLATION] Mundari → Hindi' in html_content
        assert '[TRANSLATION] Hindi result:' in html_content
        assert '[PRONUNCIATION] Target language:' in html_content
        assert '[PRONUNCIATION] Request started' in html_content
        assert '[PRONUNCIATION] WAV received:' in html_content
        assert '[PRONUNCIATION] Audio object created' in html_content
        assert '[PRONUNCIATION] Playback started' in html_content
        assert '[PRONUNCIATION] Playback ended' in html_content


class TestMundariToHindiTranslationAndAudioPipeline:
    """Verifies that Mundari text inputs produce valid Hindi translations and Hindi TTS audio."""

    @pytest.mark.parametrize("mundari_text, expected_hindi_keyword", [
        ("मिअद", "एक"),
        ("बारिया", "दो"),
        ("अपिया", "तीन"),
        ("उपुनिया", "चार"),
        ("मोड़ेया", "पाँच"),
        ("जोहार", "नमस्ते"),
        ("दुबपे", "बैठो"),
        ("लेकापे", "गिनो"),
        ("ओलपे", "लिखो"),
        ("आयूमपे", "सुनो"),
    ])
    def test_core_classroom_translation_and_hindi_tts(self, translation_engine, pronunciation_service, mundari_text, expected_hindi_keyword):
        # 1. Translate Mundari -> Hindi
        res = translation_engine.translate(mundari_text, direction="unr-hi", src_lang="mundari")
        assert res is not None
        assert res.translated_text is not None
        assert expected_hindi_keyword in res.translated_text

        # 2. Target language is Hindi -> generate Hindi audio
        audio_res, err = pronunciation_service.synthesize(res.translated_text, language="hi")
        assert err is None
        assert audio_res is not None
        assert len(audio_res.audio_bytes) > 1000
        assert audio_res.language == "hindi"
        assert audio_res.quality_gate_status in ("AUDIO_SYNTHETIC_UNVERIFIED", "HUMAN_VALIDATED", "CANONICAL_APPROVED")

    @pytest.mark.parametrize("mundari_phrase, expected_hindi_substr", [
        ("ऐंग काजी बुझाओ केदा", "समझ"),
        ("गुरु गोमके नेना काजी आर एमेप", "बताइए"),
        ("ऐंगा नाद कुड़ी मेनाअ", "बहन"),
        ("सेब चिकिता दान रे जोवा", "सेब"),
        ("ऐंग माद इहोन गेलिया धाब लेखा केदा", "गिनती"),
        ("हे", "हाँ"),
        ("का", "नहीं"),
        ("इतुअनाञ", "समझ"),
        ("काञ इतुअना", "समझ"),
    ])
    def test_student_interaction_phrases_hindi_tts(self, pronunciation_service, mundari_phrase, expected_hindi_substr):
        # Test the fallback & student phrase map values produce clear Hindi TTS
        phrase_map = {
            "ऐंग काजी बुझाओ केदा": "मुझे समझ में आ गया।",
            "गुरु गोमके नेना काजी आर एमेप": "गुरु जी, फिर से बताइए",
            "ऐंगा नाद कुड़ी मेनाअ": "मेरी एक बहन है",
            "सेब चिकिता दान रे जोवा": "सेब को क्या कहते हैं?",
            "ऐंग माद इहोन गेलिया धाब लेखा केदा": "मुझे गिनती आती है",
            "हे": "हाँ",
            "का": "नहीं",
            "इतुअनाञ": "मुझे समझ आ गया",
            "काञ इतुअना": "मुझे समझ नहीं आया",
        }
        hindi_text = phrase_map[mundari_phrase]
        assert expected_hindi_substr in hindi_text

        audio_res, err = pronunciation_service.synthesize(hindi_text, language="hi")
        assert err is None
        assert audio_res is not None
        assert len(audio_res.audio_bytes) > 2000
        assert audio_res.language == "hindi"
        assert audio_res.quality_gate_status != "AUDIO_FAILED"
