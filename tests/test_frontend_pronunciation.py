"""
tests/test_frontend_pronunciation.py
=============================================================================
SIH260042: Frontend Pronunciation API Integration & Concurrency Tests
=============================================================================
Tests frontend/index.html runtime logic for:
1. Canonical playBackendPronunciation() dispatches POST /api/pronunciation
2. Language routing: 'hindi' for Hindi, 'mundari' for Mundari
3. Handling returned audio/wav Blob and HTMLAudioElement playback
4. Concurrency mutex: second pronunciation stops the first without overlapping
5. Object URL revocation on finish and interruption
6. Teacher-friendly error messages on HTTP 400, 503, and network failure
7. Voice Mode integration:
   - Hindi input -> Mundari output -> playTeacherPronunciation() requests Mundari
   - Mundari input -> Hindi output -> playTeacherPronunciation() requests Hindi
"""

import json
import os
import subprocess
import pytest

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_HTML = os.path.join(WORKSPACE_ROOT, "frontend", "index.html")


@pytest.fixture(scope="module")
def html_content():
    with open(FRONTEND_HTML, "r", encoding="utf-8") as f:
        return f.read()


class TestFrontendPronunciationContracts:
    """Static checks for canonical pronunciation functions in frontend/index.html."""

    def test_canonical_pronunciation_function_present(self, html_content):
        assert "async function playBackendPronunciation(" in html_content
        assert 'fetch("/api/pronunciation"' in html_content
        assert 'method: "POST"' in html_content
        assert "X-Pronunciation-Language" in html_content
        assert "X-Pronunciation-Engine" in html_content
        assert "X-Pronunciation-Source" in html_content

    def test_no_raw_technical_model_names_in_teacher_facing_strings(self, html_content):
        """Ensure normal teacher UI does not leak raw Hugging Face model IDs."""
        assert "facebook/mms-tts-hin" not in html_content
        assert "facebook/mms-tts-unr" not in html_content


class TestFrontendPronunciationRuntime:
    """Node.js runtime execution tests on the extracted script."""

    @pytest.fixture(autouse=True)
    def run_node_simulation(self):
        js_test_script = r"""
const fs = require('fs');

const html = fs.readFileSync('frontend/index.html', 'utf8');
const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/);
if (!scriptMatch) {
  console.error("No script tag found");
  process.exit(1);
}

const results = {};
const networkRequests = [];
const toastLog = [];
const audioLog = [];
const revokedUrls = [];

global.localStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {}
};
global.navigator = { userAgent: "Node" };

// Mock URL
global.URL = {
  createObjectURL: (blob) => {
    return 'blob:mock-uuid-' + Math.random().toString(36).substring(2, 9);
  },
  revokeObjectURL: (url) => {
    revokedUrls.push(url);
  }
};

// Mock Audio
global.Audio = class {
  constructor(src) {
    this.src = src;
    this.paused = false;
    this.currentTime = 0;
    this.onended = null;
    this.onerror = null;
    this.onplay = null;
    audioLog.push(this);
  }
  async play() {
    this.paused = false;
    if (this.onplay) this.onplay();
    return Promise.resolve();
  }
  pause() {
    this.paused = true;
  }
};

// Mock fetch
global.fetch = async (url, opts) => {
  const reqRecord = {
    url: url,
    method: opts && opts.method ? opts.method : 'GET',
    headers: opts && opts.headers ? opts.headers : {},
    body: opts && opts.body ? JSON.parse(opts.body) : null
  };
  networkRequests.push(reqRecord);

  if (url === '/api/pronunciation') {
    const payload = reqRecord.body;
    if (!payload || !payload.text) {
      return {
        ok: false,
        status: 400,
        json: async () => ({ error: "text must be a non-empty string" }),
        headers: new Map()
      };
    }

    if (payload.text === 'TRIGGER_503') {
      return {
        ok: false,
        status: 503,
        json: async () => ({ error: "Service unavailable" }),
        headers: new Map()
      };
    }

    if (payload.text === 'TRIGGER_NET_ERR') {
      throw new Error("Failed to fetch");
    }

    const headersMap = new Map([
      ['X-Pronunciation-Language', payload.language],
      ['X-Pronunciation-Engine', payload.language === 'hindi' ? 'facebook/mms-tts-hin' : 'facebook/mms-tts-unr'],
      ['X-Pronunciation-Source', payload.text === 'मोड़ेया' ? 'prototype_asset' : 'neural_tts'],
      ['X-Pronunciation-Validation-Status', payload.text === 'मोड़ेया' ? 'PROTOTYPE_ONLY_PENDING_HUMAN_VALIDATION' : 'SYNTHETIC_GENERATED_TTS'],
      ['X-Pronunciation-Cache', 'HIT']
    ]);

    return {
      ok: true,
      status: 200,
      headers: {
        get: (h) => headersMap.get(h)
      },
      blob: async () => ({
        size: 32000,
        type: 'audio/wav'
      })
    };
  }

  // Fallback for /api/translate
  return {
    ok: true,
    json: async () => ({
      status: 'VERIFIED_EDUCATIONAL_LOOKUP',
      translated_text: 'मोड़ेया',
      confidence: 1.0,
      source_text: 'पाँच'
    })
  };
};

global.window = {
  location: { search: '', hash: '' },
  localStorage: global.localStorage,
  navigator: global.navigator,
  fetch: global.fetch,
  Audio: global.Audio,
  URL: global.URL,
  speechSynthesis: {
    speaking: false,
    pending: false,
    speak: () => {},
    cancel: () => {}
  }
};

global.document = {
  body: {
    appendChild: (el) => {
      if (el && el.textContent) toastLog.push(el.textContent);
    },
    removeChild: () => {}
  },
  querySelector: function(sel) {
    return {
      classList: { add: () => {}, remove: () => {}, contains: () => false },
      style: {},
      value: (sel === '#mundari') ? 'मोड़ेया' : ((sel === '#hindi') ? 'पाँच' : ''),
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
      style: {},
      textContent: '',
      className: '',
      remove: () => {}
    };
  }
};

// Evaluate script
new Function(scriptMatch[1])();

async function runTests() {
  const playFn = global.window.playBackendPronunciation;
  if (typeof playFn !== 'function') {
    throw new Error("playBackendPronunciation is not a function");
  }

  // TEST 1: Hindi pronunciation request ("पाँच")
  networkRequests.length = 0;
  await playFn({ text: "पाँच", language: "hindi" });
  results.test1_request_sent = networkRequests.length === 1;
  results.test1_correct_url = networkRequests[0] && networkRequests[0].url === '/api/pronunciation';
  results.test1_correct_lang = networkRequests[0] && networkRequests[0].body && networkRequests[0].body.language === 'hindi';
  results.test1_correct_text = networkRequests[0] && networkRequests[0].body && networkRequests[0].body.text === 'पाँच';
  results.test1_audio_played = audioLog.length > 0 && audioLog[audioLog.length - 1].src.startsWith('blob:');

  // TEST 2: Mundari verified word ("मोड़ेया")
  networkRequests.length = 0;
  await playFn({ text: "मोड़ेया", language: "mundari" });
  results.test2_correct_lang = networkRequests[0] && networkRequests[0].body && networkRequests[0].body.language === 'mundari';
  results.test2_correct_text = networkRequests[0] && networkRequests[0].body && networkRequests[0].body.text === 'मोड़ेया';
  results.test2_source_captured = global.window.state.lastPronunciation && global.window.state.lastPronunciation.source === 'prototype_asset';

  // TEST 3: Mundari verified greeting ("जोहार")
  networkRequests.length = 0;
  await playFn({ text: "जोहार", language: "mundari" });
  results.test3_correct_lang = networkRequests[0] && networkRequests[0].body && networkRequests[0].body.language === 'mundari';
  results.test3_correct_text = networkRequests[0] && networkRequests[0].body && networkRequests[0].body.text === 'जोहार';

  // TEST 4: Mundari arbitrary sentence ("चिलका होबाः ओ अम।")
  networkRequests.length = 0;
  await playFn({ text: "चिलका होबाः ओ अम।", language: "mundari" });
  results.test4_correct_lang = networkRequests[0] && networkRequests[0].body && networkRequests[0].body.language === 'mundari';
  results.test4_correct_text = networkRequests[0] && networkRequests[0].body && networkRequests[0].body.text === 'चिलका होबाः ओ अम।';
  results.test4_source_captured = global.window.state.lastPronunciation && global.window.state.lastPronunciation.source === 'neural_tts';

  // TEST 5: Overlap prevention (second call halts first)
  await playFn({ text: "मोड़ेया", language: "mundari" });
  const firstAudio = audioLog[audioLog.length - 1];
  const firstUrl = firstAudio.src;
  await playFn({ text: "जोहार", language: "mundari" });
  results.test5_first_paused = firstAudio.paused === true;
  results.test5_url_revoked = revokedUrls.includes(firstUrl);

  // TEST 6: Error handling 503
  toastLog.length = 0;
  const res503 = await playFn({ text: "TRIGGER_503", language: "hindi" });
  results.test6_handled_503 = res503 === false;
  results.test6_toast_friendly = toastLog.some(t => t.includes("currently unavailable"));

  // TEST 7: Network error
  toastLog.length = 0;
  const resNet = await playFn({ text: "TRIGGER_NET_ERR", language: "hindi" });
  results.test7_handled_net_err = resNet === false;
  results.test7_toast_friendly = toastLog.some(t => t.includes("temporarily unavailable"));

  // TEST 8: Empty text validation
  toastLog.length = 0;
  const resEmpty = await playFn({ text: "", language: "hindi" });
  results.test8_rejected_empty = resEmpty === false;

  // TEST 9: playTeacherPronunciation() in hi-unr direction
  networkRequests.length = 0;
  global.window.state.translationDirection = 'hi-unr';
  global.window.playTeacherPronunciation();
  results.test9_teacher_btn_mundari = networkRequests.length > 0 && networkRequests[0].body.language === 'mundari';
  results.test9_teacher_btn_text = networkRequests.length > 0 && networkRequests[0].body.text === 'मोड़ेया';

  // TEST 10: playTeacherPronunciation() in unr-hi direction
  networkRequests.length = 0;
  global.window.state.translationDirection = 'unr-hi';
  global.window.playTeacherPronunciation();
  results.test10_teacher_btn_hindi = networkRequests.length > 0 && networkRequests[0].body.language === 'hindi';

  fs.writeFileSync('scratch/frontend_pronunciation_test_results.json', JSON.stringify(results, null, 2));
}

runTests().catch(err => {
  console.error("Test execution failed:", err);
  process.exit(1);
});
""";
        res = subprocess.run(["node", "-e", js_test_script], cwd=WORKSPACE_ROOT, capture_output=True, text=True)
        assert res.returncode == 0, f"Node simulation failed:\n{res.stderr}\n{res.stdout}"
        
        results_file = os.path.join(WORKSPACE_ROOT, "scratch", "frontend_pronunciation_test_results.json")
        with open(results_file, "r", encoding="utf-8") as f:
            self.results = json.load(f)

    def test_hindi_panch_request(self):
        assert self.results.get("test1_request_sent") is True
        assert self.results.get("test1_correct_url") is True
        assert self.results.get("test1_correct_lang") is True
        assert self.results.get("test1_correct_text") is True
        assert self.results.get("test1_audio_played") is True

    def test_mundari_modeya_request(self):
        assert self.results.get("test2_correct_lang") is True
        assert self.results.get("test2_correct_text") is True
        assert self.results.get("test2_source_captured") is True

    def test_mundari_johar_request(self):
        assert self.results.get("test3_correct_lang") is True
        assert self.results.get("test3_correct_text") is True

    def test_mundari_arbitrary_sentence_request(self):
        assert self.results.get("test4_correct_lang") is True
        assert self.results.get("test4_correct_text") is True
        assert self.results.get("test4_source_captured") is True

    def test_concurrency_and_overlap_prevention(self):
        assert self.results.get("test5_first_paused") is True
        assert self.results.get("test5_url_revoked") is True

    def test_503_error_handling(self):
        assert self.results.get("test6_handled_503") is True
        assert self.results.get("test6_toast_friendly") is True

    def test_network_error_handling(self):
        assert self.results.get("test7_handled_net_err") is True
        assert self.results.get("test7_toast_friendly") is True

    def test_empty_text_rejection(self):
        assert self.results.get("test8_rejected_empty") is True

    def test_voice_mode_teacher_button_routing(self):
        assert self.results.get("test9_teacher_btn_mundari") is True
        assert self.results.get("test9_teacher_btn_text") is True
        assert self.results.get("test10_teacher_btn_hindi") is True
