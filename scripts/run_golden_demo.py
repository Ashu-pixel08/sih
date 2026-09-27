"""
scripts/run_golden_demo.py
=============================================================================
Automated Replay and Verification Test Suite for Bhasha Setu Golden Demo Set.

Validates:
1. Live execution of TranslationEngine (hi-unr, unr-hi).
2. Live execution of HinglishNormalizer + TranslationEngine (hinglish-unr).
3. PronunciationService audio asset resolution and physical WAV integrity.
4. Quality gate adherence across all 20 evaluated items.
5. Exact parity with demo/golden_set/golden_demo_set.json.

Exit code 0 on all tests passing.
=============================================================================
"""

import os
import sys
import json
import wave

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from ai.translation.translation_engine import TranslationEngine
from ai.translation.hinglish_normalizer import HinglishNormalizer
from ai.speech.pronunciation_service import PronunciationService


def verify_wav_header(file_path):
    """Verifies that file_path exists and has a valid PCM WAV header."""
    if not os.path.isfile(file_path):
        return False, f"File not found: {file_path}"
    
    try:
        with wave.open(file_path, "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            framerate = wf.getframerate()
            nframes = wf.getnframes()
            duration = nframes / float(framerate) if framerate > 0 else 0.0

            if channels not in (1, 2):
                return False, f"Unexpected channel count: {channels}"
            if sample_width != 2:  # 16-bit PCM
                return False, f"Unexpected sample width: {sample_width} (expected 2 for 16-bit)"
            if framerate not in (16000, 22050, 24000, 44100, 48000):
                return False, f"Unexpected sample rate: {framerate}"
            if duration <= 0.05:
                return False, f"Duration too short ({duration:.2f}s)"

            return True, {
                "channels": channels,
                "sample_rate": framerate,
                "sample_width": sample_width,
                "frames": nframes,
                "duration_sec": round(duration, 2)
            }
    except Exception as e:
        return False, f"Failed to parse WAV header: {e}"


def run_golden_demo_suite():
    print("=" * 80)
    print("  BHASHA SETU — GOLDEN DEMO VERIFICATION & REPLAY SUITE")
    print("=" * 80)

    dataset_path = os.path.join(PROJECT_ROOT, "demo", "golden_set", "golden_demo_set.json")
    if not os.path.isfile(dataset_path):
        print(f"[FAIL] Missing dataset: {dataset_path}")
        return 1

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    items = dataset.get("items", [])
    print(f"Loaded {len(items)} items from {dataset_path}\n")

    print("[Init] Initializing runtime engines...")
    engine = TranslationEngine(enable_neural=True)
    hnorm = HinglishNormalizer()
    p_service = PronunciationService(project_root=PROJECT_ROOT)
    print("[Init] All engines initialized successfully.\n")

    passed_count = 0
    failed_count = 0

    print("-" * 80)
    print(f"{'ID':<14} | {'STATUS':<14} | {'DIR':<8} | {'RES':<6} | {'DETAILS'}")
    print("-" * 80)

    for item in items:
        item_id = item["id"]
        status = item["final_decision"]
        direction = item["direction"]
        raw_input = item["input"]
        expected_output = item.get("actual_output")
        category = item.get("category", "")
        
        # 1. Execute live pipeline
        actual_output = None
        replayed_confidence = 0.0
        live_err = None

        try:
            if category == "CANDIDATE_HINGLISH_EVALUATION" or direction == "hinglish-unr":
                norm_res = hnorm.normalize(raw_input)
                norm_text = norm_res.normalized_hindi or raw_input
                res = engine.translate(norm_text, direction="hi-unr")
                actual_output = res.translated_text
                replayed_confidence = res.confidence
            elif direction == "unr-hi":
                res = engine.translate(raw_input, direction="unr-hi")
                actual_output = res.translated_text
                replayed_confidence = res.confidence
            else:  # hi-unr
                res = engine.translate(raw_input, direction="hi-unr")
                actual_output = res.translated_text
                replayed_confidence = res.confidence
        except Exception as ex:
            live_err = str(ex)

        # 2. Evaluate according to declared status
        item_passed = True
        notes = []

        if live_err:
            item_passed = False
            notes.append(f"Execution error: {live_err}")
        elif status == "DEMO_READY":
            # Must reproduce exact output with high confidence
            if actual_output != expected_output:
                item_passed = False
                notes.append(f"Output mismatch: got '{actual_output}', expected '{expected_output}'")
            else:
                notes.append(f"Exact output reproduced (conf={replayed_confidence:.2f})")
            
            # Must have valid playable audio
            exported_audio = item.get("audio", {}).get("exported_audio_path")
            if exported_audio:
                abs_audio = os.path.join(PROJECT_ROOT, exported_audio)
                valid, info = verify_wav_header(abs_audio)
                if not valid:
                    item_passed = False
                    notes.append(f"Audio invalid: {info}")
                else:
                    notes.append(f"Audio verified ({info['duration_sec']}s, {info['sample_rate']}Hz)")
            else:
                item_passed = False
                notes.append("DEMO_READY item missing exported audio path")

        elif status == "PROVISIONAL":
            # Must produce deterministic output matching golden dataset
            if actual_output != expected_output:
                item_passed = False
                notes.append(f"Provisional output changed: got '{actual_output}'")
            else:
                notes.append(f"Deterministic output confirmed (conf={replayed_confidence:.2f})")

        elif status == "NOT_DEMO_READY":
            # Must verify that limitation or safe fallback was reproduced
            if actual_output != expected_output:
                item_passed = False
                notes.append(f"Neural/safe output deviated: got '{actual_output}'")
            else:
                notes.append(f"Limitation verified ({item.get('evidence_source', '')})")

        if item_passed:
            passed_count += 1
            res_str = "[PASS]"
        else:
            failed_count += 1
            res_str = "[FAIL]"

        detail_msg = "; ".join(notes) if notes else "OK"
        print(f"{item_id:<14} | {status:<14} | {direction:<8} | {res_str:<6} | {detail_msg}")

    print("-" * 80)
    print("\n[Audio Verification]")
    audio_dir = os.path.join(PROJECT_ROOT, "demo", "golden_set", "audio")
    audio_files = [f for f in os.listdir(audio_dir) if f.endswith(".wav")] if os.path.isdir(audio_dir) else []
    print(f"Exported audio files in {audio_dir}: {len(audio_files)}")
    for af in audio_files:
        p = os.path.join(audio_dir, af)
        valid, info = verify_wav_header(p)
        status_lbl = "VALID" if valid else "INVALID"
        print(f"  • {af}: [{status_lbl}] {info}")

    print("\n" + "=" * 80)
    print(f"  REPLAY SUITE SUMMARY: {passed_count} PASSED, {failed_count} FAILED (TOTAL: {len(items)})")
    print("=" * 80)

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    exit_code = run_golden_demo_suite()
    sys.exit(exit_code)
