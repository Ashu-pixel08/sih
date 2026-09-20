"""
tests/test_continuous_voice_orb.py
Comprehensive verification test suite for the Continuous Voice Orb & Barge-In Experience:
1. Start voice session
2. Recognition begins (hi-IN, continuous = true)
3. Hindi transcript captured
4. Translation request sent
5. Mundari result displayed
6. Audio playback triggered
7. Listening automatically resumes
8. Second utterance works without pressing Start again
9. Speaking audio can be interrupted (Barge-in)
10. OOV result is safely rejected
11. Classroom broadcast still works
12. Stop button completely stops the session
13. Recognition error recovers
14. Unsupported browser fallback works
"""

import os
import re
import json
import subprocess
import pytest

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_HTML = os.path.join(WORKSPACE_ROOT, "frontend", "index.html")


@pytest.fixture(scope="module")
def html_content():
    with open(FRONTEND_HTML, "r", encoding="utf-8") as f:
        return f.read()


class TestVoiceOrbMarkupAndCSS:
    """Static and structural contract tests on frontend/index.html."""

    def test_voice_orb_elements_present(self, html_content):
        assert 'class="voice-hero-panel' in html_content
        assert 'class="voice-orb ready"' in html_content or 'id="micBtn"' in html_content
        assert 'id="micStatus"' in html_content
        assert 'id="micSubStatus"' in html_content
        assert 'id="voiceSessionBtn"' in html_content
        assert 'id="bargeInCancelBtn"' in html_content
        assert 'id="voiceHistoryFeed"' in html_content

    def test_all_seven_voice_orb_states_styled(self, html_content):
        """Verify CSS contains distinct styles and animations for all 7 states."""
        assert ".voice-orb.ready" in html_content
        assert ".voice-orb.listening" in html_content
        assert ".voice-orb.processing" in html_content
        assert ".voice-orb.translating" in html_content
        assert ".voice-orb.speaking" in html_content
        assert ".voice-orb.interrupted" in html_content
        assert ".voice-orb.error" in html_content

        assert "@keyframes orb-pulse-ready" in html_content
        assert "@keyframes orb-pulse-listening" in html_content
        assert "@keyframes orb-pulse-processing" in html_content
        assert "@keyframes orb-pulse-translating" in html_content
        assert "@keyframes orb-pulse-speaking" in html_content
        assert "@keyframes orb-pulse-interrupted" in html_content

    def test_state_machine_and_controller_contract(self, html_content):
        """Verify core state machine functions exist in script."""
        assert "const VoiceStateEnum = {" in html_content
        assert "function setVoiceState(" in html_content
        assert "function startVoiceSession()" in html_content
        assert "function stopVoiceSession()" in html_content
        assert "function toggleVoiceSession()" in html_content
        assert "function cancelSpeechAudio()" in html_content
        assert "function processVoiceUtterance(" in html_content
        assert "function playMundariVoiceAudio(" in html_content
        assert "window.voiceController =" in html_content


class TestContinuousVoiceOrbEngineRuntime:
    """
    Executes an in-depth Node.js runtime simulation of the continuous voice engine,
    mocking browser SpeechRecognition, Audio, and fetch to verify all 14 scenarios.
    """

    @pytest.fixture(autouse=True)
    def run_node_simulation(self):
        js_test_script = r"""
const fs = require('fs');

const html = fs.readFileSync('frontend/index.html', 'utf8');
const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/);
if (!scriptMatch) {
  console.error("No script found");
  process.exit(1);
}

// Minimal browser mock environment
const results = {};
let fetchLog = [];
let busLog = [];
let audioInstances = [];
let lastSpokenUtterance = null;

global.localStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {}
};
global.navigator = { userAgent: "Node" };

global.window = {
  location: { search: '', hash: '' },
  localStorage: global.localStorage,
  navigator: global.navigator,
  speechSynthesis: {
    speaking: false,
    pending: false,
    speak: function(u) {
      this.speaking = true;
      lastSpokenUtterance = u;
    },
    cancel: function() {
      this.speaking = false;
    }
  },
  fetch: async function(url) {
    fetchLog.push(url);
    if (url.includes('text=%E0%A4%A8%E0%A4%AE%E0%A4%B8%E0%A5%8D%E0%A4%A4%E0%A5%87') || url.includes('नमस्ते')) {
      return {
        ok: true,
        json: async () => ({
          status: 'VERIFIED_EDUCATIONAL_LOOKUP',
          confidence: 1.0,
          source_text: 'नमस्ते',
          translated_text: 'जोहार',
          translation_source: 'EDUCATIONAL_REGISTRY',
          metadata: { audio_asset: 'data/custom/images/audio_namaste.wav' }
        })
      };
    } else if (url.includes('%E0%A4%AA%E0%A4%BE%E0%A4%81%E0%A4%9A') || url.includes('पाँच')) {
      return {
        ok: true,
        json: async () => ({
          status: 'VERIFIED_EDUCATIONAL_LOOKUP',
          confidence: 1.0,
          source_text: 'पाँच',
          translated_text: 'मोड़ेया',
          translation_source: 'EDUCATIONAL_REGISTRY',
          metadata: { audio_asset: 'data/audio/canonical_modeya.wav' }
        })
      };
    } else if (url.includes('UNKNOWN_OOV')) {
      return {
        ok: true,
        json: async () => ({
          status: 'OUT_OF_VOCABULARY_UNVERIFIED',
          confidence: 0.0,
          source_text: 'UNKNOWN_OOV',
          translated_text: 'This sentence could not be translated yet.',
          translation_source: 'REJECTED'
        })
      };
    }
    return {
      ok: true,
      json: async () => ({
        status: 'AI TRANSLATION — REVIEW',
        confidence: 0.75,
        source_text: 'कुछ बात',
        translated_text: 'कजि',
        translation_source: 'NEURAL_MODEL'
      })
    };
  }
};

global.fetch = global.window.fetch;

global.document = {
  body: {
    appendChild: () => {},
    removeChild: () => {}
  },
  querySelector: function(sel) {
    return {
      classList: {
        add: () => {},
        remove: () => {},
        contains: () => false
      },
      style: {},
      value: '',
      innerHTML: '',
      textContent: '',
      prepend: () => {},
      appendChild: () => {},
      querySelector: () => null
    };
  },
  querySelectorAll: function() { return []; },
  createElement: function(tag) {
    return {
      className: '',
      style: {},
      innerHTML: '',
      prepend: () => {},
      appendChild: () => {},
      remove: () => {}
    };
  }
};

global.Audio = class {
  constructor(src) {
    this.src = src;
    this.paused = false;
    this.currentTime = 0;
    this.onended = null;
    this.onerror = null;
    audioInstances.push(this);
  }
  async play() {
    this.paused = false;
    return Promise.resolve();
  }
  pause() {
    this.paused = true;
  }
};

class MockSpeechRecognition {
  constructor() {
    this.lang = '';
    this.continuous = false;
    this.interimResults = false;
    this.maxAlternatives = 1;
    this.onstart = null;
    this.onspeechstart = null;
    this.onsoundstart = null;
    this.onresult = null;
    this.onerror = null;
    this.onend = null;
    this.started = false;
    MockSpeechRecognition.lastInstance = this;
  }
  start() {
    this.started = true;
    if (this.onstart) this.onstart();
  }
  stop() {
    this.started = false;
    if (this.onend) this.onend();
  }
  abort() {
    this.started = false;
  }
}
global.window.SpeechRecognition = MockSpeechRecognition;
global.window.webkitSpeechRecognition = MockSpeechRecognition;

// Evaluate the frontend script
new Function(scriptMatch[1])();

async function runScenarioTests() {
  const vc = global.window.voiceController;
  if (!vc) throw new Error("voiceController not exported");

  // 1. Start voice session
  vc.startSession();
  results.scenario_01_session_started = vc.isSessionActive() === true;
  results.scenario_01_state_listening = vc.getState() === "listening";

  // 2. Recognition begins
  const recog = MockSpeechRecognition.lastInstance;
  results.scenario_02_recognition_started = recog && recog.started === true;
  results.scenario_02_recognition_lang = recog && recog.lang === "hi-IN";
  results.scenario_02_recognition_continuous = recog && recog.continuous === true;

  // 3 & 4 & 5. Hindi transcript captured, translated, displayed
  await vc.simulateSpeechInput("नमस्ते");
  results.scenario_03_transcript_captured = global.window.state.currentTranslation && global.window.state.currentTranslation.source === "नमस्ते";
  results.scenario_04_translation_api_sent = fetchLog.some(u => u.includes("translate"));
  results.scenario_05_mundari_result = global.window.state.currentTranslation && global.window.state.currentTranslation.mundari === "जोहार";
  results.scenario_05_verified_badge = global.window.state.currentTranslation && global.window.state.currentTranslation.badge === "VERIFIED EDUCATIONAL";

  // 6. Audio playback triggered
  results.scenario_06_audio_triggered = audioInstances.length > 0 && audioInstances[audioInstances.length - 1].src.includes("audio_namaste.wav");
  results.scenario_06_state_speaking = vc.isSpeaking() === true || vc.getState() === "speaking";

  // 7. Listening automatically resumes when audio finishes
  const lastAudio = audioInstances[audioInstances.length - 1];
  if (lastAudio && lastAudio.onended) {
    lastAudio.onended();
  }
  results.scenario_07_resumed_listening = vc.getState() === "listening";

  // 8. Second utterance works without pressing Start again
  await vc.simulateSpeechInput("पाँच");
  results.scenario_08_second_utterance_handled = global.window.state.currentTranslation && global.window.state.currentTranslation.source === "पाँच";
  results.scenario_08_second_utterance_result = global.window.state.currentTranslation && global.window.state.currentTranslation.mundari === "मोड़ेया";

  // 9. Speaking audio can be interrupted (BARGE-IN)
  results.scenario_09_is_speaking = vc.isSpeaking() === true;
  const audioBeforeBarge = audioInstances[audioInstances.length - 1];
  
  // Teacher interrupts while audio is playing!
  await vc.simulateSpeechInput("नमस्ते");
  results.scenario_09_previous_audio_paused = audioBeforeBarge ? audioBeforeBarge.paused === true : true;
  results.scenario_09_barge_in_new_result = global.window.state.currentTranslation && global.window.state.currentTranslation.mundari === "जोहार";

  // 10. OOV result is safely rejected
  if (audioInstances.length > 0 && audioInstances[audioInstances.length - 1].onended) {
    audioInstances[audioInstances.length - 1].onended();
  }
  await vc.simulateSpeechInput("UNKNOWN_OOV");
  results.scenario_10_oov_rejected = global.window.state.currentTranslation && global.window.state.currentTranslation.status === "OUT_OF_VOCABULARY";
  results.scenario_10_oov_badge = global.window.state.currentTranslation && global.window.state.currentTranslation.badge === "TRANSLATION UNAVAILABLE";

  // 11. Classroom broadcast still works
  global.window.state.room = "MUN-TEST";
  let broadcastSent = false;
  global.window.state.channel = {
    postMessage: (d) => {
      broadcastSent = true;
      busLog.push(d);
    }
  };
  await vc.simulateSpeechInput("नमस्ते");
  results.scenario_11_broadcast_sent = broadcastSent === true;

  // 12. Stop button completely stops the session
  vc.stopSession();
  results.scenario_12_session_stopped = vc.isSessionActive() === false;
  results.scenario_12_state_ready = vc.getState() === "ready";

  // 13. Recognition error recovery
  vc.startSession();
  const activeRecog = MockSpeechRecognition.lastInstance;
  if (activeRecog && activeRecog.onerror) {
    activeRecog.onerror({ error: 'no-speech' });
  }
  results.scenario_13_no_speech_recovered = vc.isSessionActive() === true;
  vc.stopSession();

  // 14. Unsupported browser fallback
  delete global.window.SpeechRecognition;
  delete global.window.webkitSpeechRecognition;
  const startResult = vc.startSession();
  results.scenario_14_unsupported_handled = startResult === false;
  results.scenario_14_error_state = vc.getState() === "error";

  console.log(JSON.stringify(results));
}

runScenarioTests().catch(err => {
  console.error("Runtime test failed:", err);
  process.exit(1);
});
""";
        proc = subprocess.run(
            ["node", "-e", js_test_script],
            capture_output=True,
            text=True,
            cwd=WORKSPACE_ROOT
        )
        assert proc.returncode == 0, "Node.js simulation failed: " + str(proc.stderr) + " -- " + str(proc.stdout)
        self.node_results = json.loads(proc.stdout.strip().splitlines()[-1])

    def test_01_start_voice_session(self):
        assert self.node_results["scenario_01_session_started"] is True
        assert self.node_results["scenario_01_state_listening"] is True

    def test_02_recognition_begins_with_hi_in(self):
        assert self.node_results["scenario_02_recognition_started"] is True
        assert self.node_results["scenario_02_recognition_lang"] is True
        assert self.node_results["scenario_02_recognition_continuous"] is True

    def test_03_hindi_transcript_captured(self):
        assert self.node_results["scenario_03_transcript_captured"] is True

    def test_04_translation_request_sent(self):
        assert self.node_results["scenario_04_translation_api_sent"] is True

    def test_05_mundari_result_displayed_with_verified_badge(self):
        assert self.node_results["scenario_05_mundari_result"] is True
        assert self.node_results["scenario_05_verified_badge"] is True

    def test_06_audio_playback_triggered(self):
        assert self.node_results["scenario_06_audio_triggered"] is True
        assert self.node_results["scenario_06_state_speaking"] is True

    def test_07_listening_automatically_resumes(self):
        assert self.node_results["scenario_07_resumed_listening"] is True

    def test_08_second_utterance_without_pressing_start_again(self):
        assert self.node_results["scenario_08_second_utterance_handled"] is True
        assert self.node_results["scenario_08_second_utterance_result"] is True

    def test_09_speaking_audio_barge_in_interrupted(self):
        assert self.node_results["scenario_09_is_speaking"] is True
        assert self.node_results["scenario_09_previous_audio_paused"] is True
        assert self.node_results["scenario_09_barge_in_new_result"] is True

    def test_10_oov_result_safely_rejected(self):
        assert self.node_results["scenario_10_oov_rejected"] is True
        assert self.node_results["scenario_10_oov_badge"] is True

    def test_11_classroom_broadcast_integration(self):
        assert self.node_results["scenario_11_broadcast_sent"] is True

    def test_12_stop_button_completely_stops_session(self):
        assert self.node_results["scenario_12_session_stopped"] is True
        assert self.node_results["scenario_12_state_ready"] is True

    def test_13_recognition_error_recovers_without_infinite_loop(self):
        assert self.node_results["scenario_13_no_speech_recovered"] is True

    def test_14_unsupported_browser_fallback_works(self):
        assert self.node_results["scenario_14_unsupported_handled"] is True
        assert self.node_results["scenario_14_error_state"] is True
