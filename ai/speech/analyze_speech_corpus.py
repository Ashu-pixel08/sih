"""
Corpus Speech Analysis Module for Mundari Speech Dataset.

Performs exhaustive linguistic, speaker, and acoustic audit on available audio files:
- Token-level vocabulary extraction and frequency analysis
- 1-20 Number term coverage in transcripts
- Speaker partition analysis (Female: 100, Male: 100)
- Signal duration and acoustic parameter distribution
- Identification of missing educational vocabulary in audio corpus
"""

import os
import sys
import glob
import wave
import json
import re
from collections import Counter
from typing import Dict, Any, List

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW_SPEECH_DIR = os.path.join(BASE_DIR, "data", "raw", "speech", "data-sample")
MANIFEST_PATH = os.path.join(BASE_DIR, "content", "audio", "manifests", "raw_speech_manifest.json")


def analyze_corpus() -> Dict[str, Any]:
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    valid_results = [r for r in manifest["results"] if r["is_valid"]]
    excluded_results = [r for r in manifest["results"] if not r["is_valid"]]

    print(f"Total files audited: {len(manifest['results'])}")
    print(f"Valid files retained: {len(valid_results)}")
    print(f"Excluded files (silence/low energy): {len(excluded_results)}")

    # Load transcripts for valid files
    transcripts = {}
    speakers = Counter()
    durations_by_speaker = {"female": [], "male": []}
    words_by_speaker = {"female": [], "male": []}

    for r in valid_results:
        wav_path = r["file_path"]
        txt_path = os.path.splitext(wav_path)[0] + ".txt"
        speaker = "female" if "female" in wav_path else "male"
        speakers[speaker] += 1
        durations_by_speaker[speaker].append(r["duration_seconds"])

        if os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8", errors="replace") as tf:
                text = tf.read().strip()
                transcripts[r["file_name"]] = {
                    "text": text,
                    "speaker": speaker,
                    "duration": r["duration_seconds"],
                    "rms": r["rms_energy"]
                }
                words = re.findall(r"[\u0900-\u097F\w]+", text)
                words_by_speaker[speaker].extend(words)

    # Vocabulary statistics
    all_words = words_by_speaker["female"] + words_by_speaker["male"]
    vocab_counter = Counter(all_words)

    print(f"\nTotal word tokens in valid speech: {len(all_words)}")
    print(f"Unique vocabulary words: {len(vocab_counter)}")
    print(f"Speaker count: Female={speakers['female']} files, Male={speakers['male']} files")
    print(f"Female duration: mean={sum(durations_by_speaker['female'])/len(durations_by_speaker['female']):.2f}s, total={sum(durations_by_speaker['female'])/60:.2f} mins")
    print(f"Male duration: mean={sum(durations_by_speaker['male'])/len(durations_by_speaker['male']):.2f}s, total={sum(durations_by_speaker['male'])/60:.2f} mins")

    # Audit occurrence of Numbers 1 to 20
    canonical_num_roots = {
        1: ["मिअद", "मियद", "मिद", "मोयोद", "मोसा"],
        2: ["बारिया", "बरिया", "बार", "बर"],
        3: ["अपिया", "अपि"],
        4: ["उपुनिया", "उपुन"],
        5: ["मोड़ेया", "मोड़े", "मोनेया"],
        6: ["तुरिया", "तुरिआ", "तुरुइ", "तुरि"],
        7: ["एयाएया", "एयाए", "एया"],
        8: ["इरालिया", "इरालिआ", "इरल"],
        9: ["अरेया", "अरेआ", "अरे"],
        10: ["गेलेया", "गेलेआ", "गेल"],
        11: ["गेल मिअद", "गेल मिद"],
        12: ["गेल बारिया", "गेल बार"],
        13: ["गेल अपिया", "गेल अपि"],
        14: ["गेल उपुनिया", "गेल उपुन"],
        15: ["गेल मोड़ेया", "गेल मोड़े"],
        16: ["गेल तुरिया", "गेल तुरुइ"],
        17: ["गेल एयाएया", "गेल एयाए"],
        18: ["गेल इरालिया", "गेल इरल"],
        19: ["गेल अरेया", "गेल अरे"],
        20: ["हिसि", "बार गेल", "कुरी"]
    }

    num_coverage = {}
    for num in range(1, 21):
        roots = canonical_num_roots[num]
        hits = []
        for fname, data in transcripts.items():
            t = data["text"]
            for r in roots:
                if re.search(r'(?<![^\s।?!,;])' + re.escape(r) + r'(?![^\s।?!,;])', t):
                    hits.append({
                        "file": fname,
                        "speaker": data["speaker"],
                        "matched_term": r,
                        "text": t,
                        "duration": data["duration"]
                    })
                    break
        num_coverage[num] = hits

    print("\n--- NUMBER 1-20 COVERAGE IN VALID CORPUS TRANSCRIPTS ---")
    missing_numbers = []
    covered_numbers = []

    for num in range(1, 21):
        hits = num_coverage[num]
        print(f"Number {num:02d} ({canonical_num_roots[num][0]}): {len(hits)} sentence occurrences")
        if hits:
            covered_numbers.append(num)
            for h in hits[:2]:
                print(f"    [{h['speaker']}] {h['file']}: \"{h['text']}\" (matched: {h['matched_term']})")
        else:
            missing_numbers.append(num)

    print(f"\nNumbers with sentence-level occurrences in sample: {covered_numbers} (Count: {len(covered_numbers)})")
    print(f"Numbers COMPLETELY MISSING from sample transcripts: {missing_numbers} (Count: {len(missing_numbers)})")

    # Check for ISOLATED number recordings
    isolated_recordings = []
    for fname, data in transcripts.items():
        w = data["text"].strip().split()
        if len(w) == 1:
            isolated_recordings.append((fname, data["text"]))

    print(f"\nIsolated single-word recordings in entire sample: {len(isolated_recordings)}")

    report = {
        "total_audited_files": len(manifest["results"]),
        "valid_files": len(valid_results),
        "excluded_silent_files": len(excluded_results),
        "speaker_distribution": dict(speakers),
        "total_valid_duration_minutes": round(sum(r["duration_seconds"] for r in valid_results) / 60.0, 2),
        "isolated_single_word_audio_count": len(isolated_recordings),
        "sentence_covered_numbers": covered_numbers,
        "completely_missing_numbers": missing_numbers,
        "coverage_details": {num: len(hits) for num, hits in num_coverage.items()}
    }

    report_path = os.path.join(BASE_DIR, "docs", "dataset-coverage-report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nSaved coverage report to {report_path}")

    return report


if __name__ == "__main__":
    analyze_corpus()
