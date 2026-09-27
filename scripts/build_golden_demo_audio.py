"""
scripts/build_golden_demo_audio.py
=============================================================================
Pre-renders deterministic, high-quality 16 kHz 16-bit PCM WAV audio for the
three Golden Demo Set flows:
  - Flow A (Hindi -> Mundari): "नेआ चिनाः संख्या तना"
  - Flow B (Mundari -> Hindi): "अब मैं गिनती करूँगा बारह तक"
  - Flow C (Hinglish -> Mundari): "नेआ चिनाः संख्या तना"

Generates:
  - demo/golden_set/audio/hi_to_mundari_001.wav
  - demo/golden_set/audio/SEL_HI_05.wav
  - demo/golden_set/audio/mundari_to_hi_001.wav
  - demo/golden_set/audio/hinglish_to_mundari_001.wav
  - demo/golden_set/audio/SEL_HING_01.wav
  - demo/golden_set/audio/golden_audio_manifest.json

All audio passes the AudioQualityGate before inclusion.
"""

import os
import sys
import json
import hashlib
import datetime
import wave

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

WORKSPACE_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from ai.speech.pronunciation_service import VitsTTSProvider
from ai.speech.audio_quality_gate import AudioQualityGate


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def get_wav_info(wav_bytes: bytes):
    import io
    with io.BytesIO(wav_bytes) as buf:
        with wave.open(buf, "rb") as wf:
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            nframes = wf.getnframes()
            duration = round(nframes / float(framerate), 3)
    return {
        "channels": channels,
        "sample_rate": framerate,
        "bit_depth": sampwidth * 8,
        "duration_sec": duration,
        "bytes": len(wav_bytes)
    }


def main():
    print("[1/4] Initializing VitsTTSProvider and AudioQualityGate...")
    provider = VitsTTSProvider(WORKSPACE_ROOT)
    gate = AudioQualityGate(expected_sample_rate=16000)

    out_dir = os.path.join(WORKSPACE_ROOT, "demo", "golden_set", "audio")
    os.makedirs(out_dir, exist_ok=True)

    items = [
        {
            "id": "hi_to_mundari_001",
            "flow": "Flow A: Hindi -> Mundari",
            "demo_id": "SEL_HI_05",
            "source_text": "यह कौन सी संख्या है",
            "normalized_text": "यह कौन सी संख्या है",
            "target_text": "नेआ चिनाः संख्या तना",
            "language": "mundari",
            "provider": "vits_tts_provider",
            "model": "facebook/mms-tts-unr",
            "version": "1.0.0",
            "phonological_layer": "devanagari_to_odia_canonical_v2",
            "validation_status": "AUDIO_PROTOTYPE_PENDING_VALIDATION",
            "provenance": "MMS-TTS-UNR (VITS NEURAL ACOUSTIC SYNTHESIS; STRICTLY PROTOTYPE PENDING NATIVE SPEAKER VALIDATION)",
            "output_filenames": ["hi_to_mundari_001.wav", "SEL_HI_05.wav"]
        },
        {
            "id": "mundari_to_hi_001",
            "flow": "Flow B: Mundari -> Hindi",
            "demo_id": "SEL_UNR_02",
            "source_text": "नअःदो अइंग लेकायाइंग गेलबर जकेद्।",
            "normalized_text": None,
            "target_text": "अब मैं गिनती करूँगा बारह तक",
            "language": "hindi",
            "provider": "vits_tts_provider",
            "model": "facebook/mms-tts-hin",
            "version": "1.0.0",
            "phonological_layer": "devanagari_vits_canonical",
            "validation_status": "AUDIO_SYNTHETIC_UNVERIFIED",
            "provenance": "MMS-TTS-HIN (VITS NEURAL ACOUSTIC SYNTHESIS; SYNTHETIC SPEECH PENDING FORMAL HUMAN AUDIT)",
            "output_filenames": ["mundari_to_hi_001.wav"]
        },
        {
            "id": "hinglish_to_mundari_001",
            "flow": "Flow C: Hinglish -> Mundari",
            "demo_id": "SEL_HING_01",
            "source_text": "yeh kaun si sankhya hai",
            "normalized_text": "यह कौन सी संख्या है",
            "target_text": "नेआ चिनाः संख्या तना",
            "language": "mundari",
            "provider": "vits_tts_provider",
            "model": "facebook/mms-tts-unr",
            "version": "1.0.0",
            "phonological_layer": "devanagari_to_odia_canonical_v2",
            "validation_status": "AUDIO_PROTOTYPE_PENDING_VALIDATION",
            "provenance": "MMS-TTS-UNR (VITS NEURAL ACOUSTIC SYNTHESIS; STRICTLY PROTOTYPE PENDING NATIVE SPEAKER VALIDATION)",
            "output_filenames": ["hinglish_to_mundari_001.wav", "SEL_HING_01.wav"]
        }
    ]

    manifest_entries = []

    print("[2/4] Synthesizing and validating demo flow audio...")
    for item in items:
        text = item["target_text"]
        lang = item["language"]
        print(f"  -> Synthesizing '{lang}': '{text}'...")

        res = provider.generate(text, lang)
        if not res or not res.audio_bytes:
            raise RuntimeError(f"Failed to synthesize {lang} audio for '{text}'")

        # Validate with AudioQualityGate
        eval_result = gate.validate_audio(res.audio_bytes, text, lang, provenance=item["validation_status"])
        if not eval_result.is_valid:
            raise ValueError(f"Audio quality gate failed for {item['id']}: {eval_result.rejection_reasons}")

        wav_info = get_wav_info(res.audio_bytes)
        sha256_hash = compute_sha256(res.audio_bytes)

        # Write all specified output files
        for fname in item["output_filenames"]:
            out_path = os.path.join(out_dir, fname)
            with open(out_path, "wb") as f:
                f.write(res.audio_bytes)
            print(f"     Wrote: {out_path} ({wav_info['duration_sec']}s, {len(res.audio_bytes)} bytes)")

        entry = {
            "id": item["id"],
            "demo_id": item["demo_id"],
            "flow": item["flow"],
            "source_text": item["source_text"],
            "normalized_text": item["normalized_text"],
            "target_text": item["target_text"],
            "language": item["language"],
            "provider": item["provider"],
            "model": item["model"],
            "version": item["version"],
            "phonological_layer": item["phonological_layer"],
            "audio_file": item["output_filenames"][0],
            "alias_files": item["output_filenames"][1:],
            "sample_rate": wav_info["sample_rate"],
            "channels": wav_info["channels"],
            "bit_depth": wav_info["bit_depth"],
            "duration_sec": wav_info["duration_sec"],
            "file_size_bytes": wav_info["bytes"],
            "sha256": sha256_hash,
            "quality_gate": {
                "passed": eval_result.is_valid,
                "status": eval_result.status,
                "rms_dbfs": eval_result.rms_dbfs,
                "peak_dbfs": eval_result.peak_dbfs,
                "clipping_samples": eval_result.clipping_samples,
                "silence_ratio": eval_result.silence_ratio,
                "max_silence_run_ms": eval_result.max_silence_run_ms
            },
            "validation_status": item["validation_status"],
            "provenance": item["provenance"],
            "generated_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        manifest_entries.append(entry)

    print("[3/4] Writing golden_audio_manifest.json...")
    manifest = {
        "manifest_version": "1.0.0",
        "description": "Pre-rendered, deterministic offline audio assets for Bhasha Setu Golden Demo Set",
        "policy": {
            "anti_hallucination_mandate": "Zero synthetic speech is labeled as human verified.",
            "deterministic_synthesis": "Seeded torch generators guarantee byte-level reproducible waveforms.",
            "acoustic_quality_gate": "All assets verified for RMS, clipping, silence duration, and valid WAV headers."
        },
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_items": len(manifest_entries),
        "items": manifest_entries
    }

    manifest_path = os.path.join(out_dir, "golden_audio_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2, ensure_ascii=False)
    print(f"Manifest written to: {manifest_path}")

    print("[4/4] Completed audio generation successfully.")


if __name__ == "__main__":
    main()
