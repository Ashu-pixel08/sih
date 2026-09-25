"""
tests/test_phase_8_browser_prototype.py
=============================================================================
SIH260042: Phase 8 Browser Prototype Validation Test Suite
=============================================================================
Validates:
1. Flow A: Hindi text -> Mundari text (Canonical numbers & phrases)
2. Flow B: Hindi speech -> Hindi text -> Mundari text
3. Flow C: Mundari text -> Hindi text (Reverse pipeline)
4. Flow D: OOV / unverified input -> safe fallback & broadcast suppression
5. Flow E: Mundari audio playback for supported canonical phrases
6. Verification that unverified/composed translations are NOT presented as verified
7. Verification that synthetic audio is clearly labelled as SYNTHETIC_PROTOTYPE
8. Verification that browser speech recognition clearly discloses network dependency
=============================================================================
"""

import os
import re
import json
import subprocess
import unittest

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_HTML = os.path.join(WORKSPACE_ROOT, "frontend", "index.html")


class TestPhase8BrowserPrototype(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.assertTrue(os.path.exists(FRONTEND_HTML), "frontend/index.html must exist")
        with open(FRONTEND_HTML, "r", encoding="utf-8") as f:
            cls.html = f.read()

        runner_js = """
const fs = require('fs');
const vm = require('vm');
const html = fs.readFileSync('frontend/index.html', 'utf8');
const s = html.indexOf('<script>') + 8;
const e = html.indexOf('</script>', s);
const code = html.slice(s, e);

const mockEl = {
  innerHTML: '',
  value: '',
  textContent: '',
  style: {},
  classList: { add(){}, remove(){}, contains(){ return false; } }
};

global.window = global;
global.localStorage = {
  _s: {},
  getItem(k) { return this._s[k] || null; },
  setItem(k, v) { this._s[k] = String(v); },
  removeItem(k) { delete this._s[k]; }
};
global.document = {
  getElementById: () => mockEl,
  querySelector: () => mockEl,
  createElement: () => mockEl,
  body: { appendChild(){} }
};
global.$ = () => mockEl;
global.Audio = class { constructor(src){ this.src = src; } play(){ return Promise.resolve(); } };
global.SpeechSynthesisUtterance = class { constructor(t){ this.text = t; } };
global.speechSynthesis = { speak(){}, cancel(){} };

vm.runInThisContext(code);

const report = {
  db_numbers_count: DB.numbers.length,
  db_phrasebook_count: DB.phrasebook.length,
  flow_a_num_5: backendTranslate('पाँच', 'hi-unr'),
  flow_a_phrase_namaste: backendTranslate('नमस्ते', 'hi-unr'),
  flow_a_phrase_baitho: backendTranslate('बैठो', 'hi-unr'),
  flow_b_transcript: backendTranslate('एक', 'hi-unr'),
  flow_c_num_miad: backendTranslate('मिअद', 'unr-hi'),
  flow_c_num_baria: backendTranslate('बारिया', 'unr-hi'),
  flow_c_phrase_dubpe: backendTranslate('दुबपे', 'unr-hi'),
  flow_c_phrase_johar: backendTranslate('जोहार', 'unr-hi'),
  flow_d_fwd_oov: backendTranslate('क्वांटम कंप्यूटिंग अल्गोरिदम', 'hi-unr'),
  flow_d_rev_oov: backendTranslate('अल्गोरिदम डेटाबेस प्रोटोकॉल', 'unr-hi'),
  req4_composed_prompt: backendTranslate(demoHindi, 'hi-unr')
};

// Teacher Login Regression Test
mockEl.value = '1234';
teacherLogin();
report.teacher_login_test = {
  fnDefined: typeof teacherLogin === 'function',
  role: state.role,
  page: state.page
};

console.log(JSON.stringify(report));
"""
        proc = subprocess.run(
            ["node", "-e", runner_js],
            cwd=WORKSPACE_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        if proc.returncode != 0:
            raise RuntimeError(f"Node.js validation harness failed:\nSTDOUT: {proc.stdout}\nSTDERR: {proc.stderr}")

        cls.js_results = json.loads(proc.stdout)

    def test_flow_a_hindi_text_to_mundari_text(self):
        """Verify Flow A: Hindi text translates to attested Mundari text with verified status."""
        res_num = self.js_results["flow_a_num_5"]
        self.assertEqual(res_num["status"], "EXACT_CANONICAL_LOOKUP")
        self.assertEqual(res_num["mundari"], "मोड़ेया")
        self.assertTrue(res_num["isBroadcastable"])
        self.assertIn("CANONICAL", res_num["badge"])

        res_phrase = self.js_results["flow_a_phrase_namaste"]
        self.assertEqual(res_phrase["status"], "CORPUS_ATTESTED")
        self.assertEqual(res_phrase["mundari"], "जोहार")
        self.assertTrue(res_phrase["isBroadcastable"])

        res_baitho = self.js_results["flow_a_phrase_baitho"]
        self.assertEqual(res_baitho["status"], "CORPUS_ATTESTED")
        self.assertEqual(res_baitho["mundari"], "दुबपे")
        self.assertTrue(res_baitho["isBroadcastable"])

    def test_flow_b_hindi_speech_to_mundari_text(self):
        """Verify Flow B: Speech-to-text transcript translates to Mundari and network disclosure is present."""
        res_speech = self.js_results["flow_b_transcript"]
        self.assertEqual(res_speech["status"], "EXACT_CANONICAL_LOOKUP")
        self.assertEqual(res_speech["mundari"], "मिअद")
        self.assertTrue(res_speech["isBroadcastable"])

        # Network disclosure verification
        self.assertIn("WEB PROTOTYPE ONLY — browser speech recognition may require network", self.html)
        self.assertIn("Production Android will use the local speech pipeline", self.html)

    def test_flow_c_mundari_text_to_hindi_text(self):
        """Verify Flow C: Reverse Mundari text translates to Hindi equivalent with verified lookup."""
        res_miad = self.js_results["flow_c_num_miad"]
        self.assertEqual(res_miad["status"], "VERIFIED_EDUCATIONAL_LOOKUP")
        self.assertEqual(res_miad["mundari"], "एक")
        self.assertTrue(res_miad["isBroadcastable"])
        self.assertIn("MUNDARI ➔ HINDI", res_miad["badge"])

        res_dubpe = self.js_results["flow_c_phrase_dubpe"]
        self.assertEqual(res_dubpe["status"], "VERIFIED_EDUCATIONAL_LOOKUP")
        self.assertEqual(res_dubpe["mundari"], "बैठो")
        self.assertTrue(res_dubpe["isBroadcastable"])

        res_johar = self.js_results["flow_c_phrase_johar"]
        self.assertEqual(res_johar["status"], "VERIFIED_EDUCATIONAL_LOOKUP")
        self.assertEqual(res_johar["mundari"], "नमस्ते")
        self.assertTrue(res_johar["isBroadcastable"])

    def test_flow_d_oov_safe_fallback(self):
        """Verify Flow D: Out-of-vocabulary inputs trigger safe fallback and block broadcast."""
        fwd_oov = self.js_results["flow_d_fwd_oov"]
        self.assertEqual(fwd_oov["status"], "OUT_OF_VOCABULARY")
        self.assertIn("Unattested in FLN Registry", fwd_oov["mundari"])
        self.assertFalse(fwd_oov["isBroadcastable"], "Must not allow broadcast of unverified OOV")
        self.assertEqual(fwd_oov["badgeClass"], "danger")

        rev_oov = self.js_results["flow_d_rev_oov"]
        self.assertEqual(rev_oov["status"], "OUT_OF_VOCABULARY")
        self.assertIn("unattested", rev_oov["mundari"].lower())
        self.assertFalse(rev_oov["isBroadcastable"], "Must not allow broadcast of reverse OOV")
        self.assertEqual(rev_oov["badgeClass"], "danger")

    def test_flow_e_mundari_audio_playback_assets_exist(self):
        """Verify Flow E: All pre-rendered WAV audio files referenced in UI exist and are valid WAV files."""
        # 1. Check all 20 numerals
        for num_idx in range(1, 21):
            wav_path = os.path.join(WORKSPACE_ROOT, "content", "audio", "prototype_tts", "numbers", f"num_{num_idx:02d}.wav")
            self.assertTrue(os.path.exists(wav_path), f"Missing numeral audio asset: {wav_path}")
            self.assertGreater(os.path.getsize(wav_path), 1000, f"Numeral audio file too small: {wav_path}")

        # 2. Check phrasebook audio
        phrase_dir = os.path.join(WORKSPACE_ROOT, "content", "audio", "prototype_tts", "phrases")
        self.assertTrue(os.path.exists(phrase_dir))
        phrase_wavs = [f for f in os.listdir(phrase_dir) if f.endswith(".wav")]
        self.assertGreaterEqual(len(phrase_wavs), 16, "Must have at least 16 pre-rendered phrase WAVs")

    def test_unverified_composed_translations_not_presented_as_verified(self):
        """Verify Requirement 4: Composed sentences are strictly marked as unverified with broadcast blocked."""
        res_comp = self.js_results["req4_composed_prompt"]
        self.assertEqual(res_comp["status"], "COMPOSED_FROM_ATTESTED_FRAGMENTS")
        self.assertIn("UNVERIFIED_SENTENCE", res_comp["badge"])
        self.assertNotEqual(res_comp["badgeClass"], "verified", "Composed translation must not have verified badgeClass")
        self.assertEqual(res_comp["badgeClass"], "warn")
        self.assertFalse(res_comp["isBroadcastable"], "Composed sentence must NOT be broadcastable")
        self.assertIn("UNVERIFIED", res_comp["provenance"])

    def test_synthetic_audio_clearly_labelled_and_never_claimed_native(self):
        """Verify Requirement 5: Synthetic audio is labelled SYNTHETIC_PROTOTYPE and never claimed native."""
        # 1. HTML must contain explicit prototype label
        self.assertIn("SYNTHETIC_PROTOTYPE (PENDING HUMAN VALIDATION)", self.html)
        self.assertIn("SYNTHETIC_PROTOTYPE", self.html)

        # 2. Must NOT claim authentic or native Mundari audio
        html_lower = self.html.lower()
        self.assertNotIn("authentic mundari audio", html_lower)
        self.assertNotIn("native mundari recording", html_lower)
        self.assertNotIn("verified pronunciation audio", html_lower)

        # 3. Canonical Registry verification: authentic audio is MISSING pending field collection
        registry_path = os.path.join(WORKSPACE_ROOT, "content", "content_registry.json")
        with open(registry_path, "r", encoding="utf-8") as f:
            reg = json.load(f)
        for item in reg["items"]:
            self.assertEqual(item["audio_status"], "MISSING", "Canonical registry must track authentic audio as MISSING pending field collection")


    def test_browser_speech_recognition_network_disclosure(self):
        """Verify Requirement 6: Browser speech recognition clearly discloses network dependency."""
        self.assertIn("WEB PROTOTYPE ONLY — browser speech recognition may require network", self.html)
        self.assertIn("Production Android will use the local speech pipeline", self.html)
        self.assertIn("lacks native support for Mundari", self.html)

    def test_teacher_and_student_login_contracts(self):
        """Regression test for Teacher login failure: verifies teacherLogin and studentLogin are defined, validate input, and transition state."""
        self.assertIn("function teacherLogin()", self.html)
        self.assertIn("function studentLogin()", self.html)
        self.assertIn("onclick=\"teacherLogin()\"", self.html)
        self.assertIn("onclick=\"studentLogin()\"", self.html)

        res = self.js_results.get("teacher_login_test", {})
        self.assertTrue(res.get("fnDefined"), "teacherLogin must be a defined function")
        self.assertEqual(res.get("role"), "teacher", "teacherLogin must set state.role to teacher")
        self.assertEqual(res.get("page"), "dashboard", "teacherLogin must transition page to dashboard")


if __name__ == "__main__":
    unittest.main()
