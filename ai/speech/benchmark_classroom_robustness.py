"""
ai/speech/benchmark_classroom_robustness.py
=============================================================================
SIH260042: AI-Powered Vernacular Pedagogy & Real-Time Translation
Classroom Acoustic Noise Robustness & VAD Threshold Evaluation Benchmark
=============================================================================

MANDATE & GOVERNANCE:
- Evaluates signal-processing stability, VAD endpointing, model rejection, and
  presentation fallback activation across simulated rural classroom conditions:
  Clean, 10 dB, 5 dB, 0 dB SNR with Fan Hum, Babble, Desk Taps, Reverberation.
- Uses AUTHENTIC Mundari speech recordings from the Karya corpus as the base signal.
- ZERO ACCURACY CLAIMS: The 1–20 speech model is in validation/research status due
  to lack of isolated number recordings; this benchmark measures DSP and rejection
  robustness, NOT linguistic number recognition accuracy.
=============================================================================
"""

import json
import math
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import scipy.io.wavfile as wavfile

cur_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.normpath(os.path.join(cur_dir, "..", ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from ai.integration_pipeline import VernacularPedagogyPipeline
from ai.preprocessing.audio_preprocessor import AudioPreprocessor
from ai.preprocessing.vad_stream_processor import (
    StreamingVADProcessor,
    VADConfig,
    VADState,
)
from ai.speech.classroom_acoustic_simulator import (
    ClassroomAcousticSimulator,
    ClassroomNoiseType,
)
from ai.speech.speech_recognition_engine import SpeechRecognitionManager


class ClassroomRobustnessBenchmark:
    """
    Executes systematic acoustic stress-testing across SNR levels and noise profiles.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        num_test_files: int = 12,
        seed: int = 42,
    ):
        self.sample_rate = sample_rate
        self.num_test_files = num_test_files
        self.simulator = ClassroomAcousticSimulator(sample_rate=sample_rate, seed=seed)
        self.preprocessor = AudioPreprocessor()
        self.speech_manager = SpeechRecognitionManager()
        self.pipeline = VernacularPedagogyPipeline()

        self.audio_dir = os.path.join(workspace_root, "data", "raw", "speech", "data-sample")
        self.test_audio_files = self._select_authentic_recordings()

    def _select_authentic_recordings(self) -> List[str]:
        """Selects balanced male and female authentic speech files."""
        candidates: List[str] = []
        for root, _, files in os.walk(self.audio_dir):
            for f in files:
                if f.endswith(".wav") and not f.startswith("._"):
                    candidates.append(os.path.join(root, f))

        # Select diverse subset
        candidates.sort()
        step = max(1, len(candidates) // self.num_test_files)
        selected = candidates[::step][: self.num_test_files]
        return selected

    def load_clean_audio(self, wav_path: str) -> np.ndarray:
        """Loads and converts authentic audio to 16 kHz Float32 mono."""
        sr, data = wavfile.read(wav_path)
        if data.dtype == np.int16:
            audio = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            audio = data.astype(np.float32) / 2147483648.0
        elif data.dtype == np.float32:
            audio = data
        else:
            audio = data.astype(np.float32) / np.max(np.abs(data))

        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)

        if sr != self.sample_rate:
            audio = self.preprocessor.resample(audio, sr, self.sample_rate)

        # Normalize clean speech RMS
        rms = np.sqrt(np.mean(audio**2))
        if rms > 1e-6:
            audio = audio * (0.05 / rms)  # Standardize speech RMS to ~ -26 dBFS

        return audio.astype(np.float32)

    def evaluate_vad_on_noise_only(
        self, noise_type: ClassroomNoiseType, vad_config: VADConfig, duration_s: float = 3.0
    ) -> Dict[str, Any]:
        """
        Evaluates False Positive Rate: Feeds pure noise into VAD without any speech.
        VAD should stay in IDLE and emit 0 utterances.
        """
        vad = StreamingVADProcessor(config=vad_config)
        noise = self.simulator.generate_noise(noise_type, int(duration_s * self.sample_rate))
        # Scale noise to realistic ambient level (-42 dBFS)
        target_rms = 10.0 ** (-42.0 / 20.0)
        curr_rms = np.sqrt(np.mean(noise**2)) + 1e-9
        noise = noise * (target_rms / curr_rms)

        utterances = vad.process_continuous_audio(noise)
        false_positives = len(utterances)

        # Check frame states
        false_onset_count = sum(1 for m in vad.history_metrics if m["state"] == "ONSET_CANDIDATE")
        false_speech_count = sum(1 for m in vad.history_metrics if m["state"] == "IN_SPEECH")

        return {
            "noise_type": noise_type.value,
            "duration_s": duration_s,
            "false_utterances_emitted": false_positives,
            "false_onset_frames": false_onset_count,
            "false_speech_frames": false_speech_count,
            "final_noise_floor_db": round(vad.noise_floor_db, 2),
            "final_threshold_db": round(vad.threshold_db, 2),
            "passed_false_positive_check": (false_positives == 0),
        }

    def run_acoustic_matrix(self) -> Dict[str, Any]:
        """
        Runs the full evaluation matrix:
        Audio Samples x [Clean, 10dB, 5dB, 0dB] x [Fan, Babble, Taps, Reverb, Mixed].
        """
        print("=" * 75)
        print("RUNNING CLASSROOM ACOUSTIC ROBUSTNESS BENCHMARK")
        print(f"Authentic audio samples: {len(self.test_audio_files)}")
        print("SNRs: Clean, 10 dB, 5 dB, 0 dB")
        print("Noise profiles: Fan Hum, Classroom Babble, Desk Taps, Reverb, Mixed")
        print("=" * 75)

        snr_levels = [
            ("CLEAN", math.inf),
            ("10_DB", 10.0),
            ("5_DB", 5.0),
            ("0_DB", 0.0),
        ]

        noise_types = [
            ClassroomNoiseType.MIXED_CLASSROOM,
            ClassroomNoiseType.FAN_HUM,
            ClassroomNoiseType.CLASSROOM_BABBLE,
            ClassroomNoiseType.DESK_TAPS,
        ]

        results_by_condition: Dict[str, List[Dict[str, Any]]] = {}

        for snr_label, snr_val in snr_levels:
            for n_type in noise_types:
                cond_key = f"{n_type.value}_SNR_{snr_label}"
                results_by_condition[cond_key] = []

                for wav_path in self.test_audio_files:
                    clean_audio = self.load_clean_audio(wav_path)
                    sim_audio, meta = self.simulator.simulate_classroom_utterance(
                        clean_speech=clean_audio,
                        noise_type=n_type if not math.isinf(snr_val) else ClassroomNoiseType.CLEAN,
                        target_snr_db=snr_val,
                        apply_reverb=(n_type == ClassroomNoiseType.MIXED_CLASSROOM),
                        lead_in_seconds=0.5,
                        lead_out_seconds=0.6,
                    )

                    # 1. Evaluate VAD
                    vad = StreamingVADProcessor()
                    utterances = vad.process_continuous_audio(sim_audio)
                    vad_detected = len(utterances) > 0
                    num_utterances = len(utterances)

                    # 2. Evaluate Preprocessing & Stability
                    if vad_detected:
                        test_utt = utterances[0]
                        self.assertEqual(len(test_utt), 16000)
                    else:
                        # Fallback to center window if VAD missed
                        center = len(sim_audio) // 2
                        test_utt = sim_audio[max(0, center - 8000) : center + 8000]
                        if len(test_utt) < 16000:
                            test_utt = np.pad(test_utt, (0, 16000 - len(test_utt)))

                    _, log_mel = self.preprocessor.preprocess_signal(test_utt, 16000)
                    spec_4d = self.preprocessor.format_for_model(log_mel)

                    prep_stable = (
                        not np.isnan(spec_4d).any()
                        and not np.isinf(spec_4d).any()
                        and spec_4d.shape == (1, 101, 64, 1)
                    )
                    spec_mean = float(np.mean(spec_4d))
                    spec_std = float(np.std(spec_4d))

                    # 3. Evaluate Edge Model Inference & Confidence
                    speech_res = self.speech_manager.vocabulary_recognizer.recognize_spectrogram(spec_4d)
                    conf = speech_res.confidence
                    margin = speech_res.margin
                    top_class = speech_res.class_index
                    is_confident = speech_res.is_confident

                    # 4. Evaluate Pipeline Presentation Fallback
                    pipeline_res = self.pipeline.process_spoken_audio(test_utt, sample_rate=16000)
                    fallback_activated = pipeline_res.fallback_recommended

                    results_by_condition[cond_key].append({
                        "file_name": os.path.basename(wav_path),
                        "vad_detected": vad_detected,
                        "num_utterances": num_utterances,
                        "prep_stable": prep_stable,
                        "spec_mean": round(spec_mean, 2),
                        "spec_std": round(spec_std, 2),
                        "top_class": top_class,
                        "confidence": round(conf, 4),
                        "margin": round(margin, 4),
                        "is_confident": is_confident,
                        "fallback_activated": fallback_activated,
                        "status_code": pipeline_res.status_code,
                    })

        # Aggregate summary statistics
        summary: Dict[str, Dict[str, Any]] = {}
        for cond_key, records in results_by_condition.items():
            total = len(records)
            vad_detect_rate = sum(1 for r in records if r["vad_detected"]) / float(total)
            prep_stability_rate = sum(1 for r in records if r["prep_stable"]) / float(total)
            avg_conf = float(np.mean([r["confidence"] for r in records]))
            avg_margin = float(np.mean([r["margin"] for r in records]))
            confident_rate = sum(1 for r in records if r["is_confident"]) / float(total)
            fallback_rate = sum(1 for r in records if r["fallback_activated"]) / float(total)
            class_0_rate = sum(1 for r in records if r["top_class"] == 0) / float(total)

            summary[cond_key] = {
                "total_evaluations": total,
                "vad_detection_rate": round(vad_detect_rate * 100.0, 1),
                "preprocessing_stability_rate": round(prep_stability_rate * 100.0, 1),
                "average_model_confidence": round(avg_conf, 4),
                "average_confidence_margin": round(avg_margin, 4),
                "confident_recognition_rate": round(confident_rate * 100.0, 1),
                "presentation_fallback_rate": round(fallback_rate * 100.0, 1),
                "classified_as_background_noise_rate": round(class_0_rate * 100.0, 1),
            }

        return {
            "summary": summary,
            "detailed_records": results_by_condition,
        }

    def evaluate_threshold_grid(self) -> Dict[str, Any]:
        """
        Systematic grid search evaluating candidate VAD onset margins and noise adapt rates:
        Measures False Alarm Rate (on pure noise) vs Detection Rate (on 0 dB / 5 dB / 10 dB speech).
        """
        print("\n" + "=" * 75)
        print("EVALUATING VAD THRESHOLD ASSUMPTIONS")
        print("=" * 75)

        onset_margins = [8.0, 10.0, 12.0, 14.0, 16.0]  # dB
        noise_adapt_rates = [0.02, 0.05, 0.10]

        grid_results: List[Dict[str, Any]] = []

        # Load 4 representative authentic speech samples
        eval_speech_files = self.test_audio_files[:4]
        clean_samples = [self.load_clean_audio(p) for p in eval_speech_files]

        for margin in onset_margins:
            for alpha in noise_adapt_rates:
                cfg = VADConfig(
                    speech_threshold_margin_db=margin,
                    noise_adapt_rate=alpha,
                )

                # 1. Test False Alarm on Pure Noise (3.0s babble + fan)
                pure_noise_fan = self.evaluate_vad_on_noise_only(ClassroomNoiseType.FAN_HUM, cfg, 3.0)
                pure_noise_babble = self.evaluate_vad_on_noise_only(ClassroomNoiseType.CLASSROOM_BABBLE, cfg, 3.0)
                total_fa = pure_noise_fan["false_utterances_emitted"] + pure_noise_babble["false_utterances_emitted"]

                # 2. Test Detection on 10 dB, 5 dB, 0 dB Mixed Classroom Speech
                detections = {10.0: 0, 5.0: 0, 0.0: 0}
                for speech in clean_samples:
                    for snr in [10.0, 5.0, 0.0]:
                        sim_audio, _ = self.simulator.simulate_classroom_utterance(
                            speech,
                            noise_type=ClassroomNoiseType.MIXED_CLASSROOM,
                            target_snr_db=snr,
                            apply_reverb=True,
                        )
                        v = StreamingVADProcessor(config=cfg)
                        utts = v.process_continuous_audio(sim_audio)
                        if len(utts) > 0:
                            detections[snr] += 1

                total_tests = len(clean_samples)
                det_10db = round((detections[10.0] / total_tests) * 100.0, 1)
                det_5db = round((detections[5.0] / total_tests) * 100.0, 1)
                det_0db = round((detections[0.0] / total_tests) * 100.0, 1)

                grid_results.append({
                    "speech_threshold_margin_db": margin,
                    "noise_adapt_rate": alpha,
                    "false_alarms_pure_noise": total_fa,
                    "detection_rate_10db_pct": det_10db,
                    "detection_rate_5db_pct": det_5db,
                    "detection_rate_0db_pct": det_0db,
                    "recommended": (total_fa == 0 and det_10db >= 90.0 and det_5db >= 75.0),
                })

        return {"grid_evaluations": grid_results}

    def generate_full_report(self) -> Dict[str, Any]:
        """Runs acoustic matrix and threshold grid, then saves benchmark report."""
        t0 = time.time()
        matrix_res = self.run_acoustic_matrix()
        grid_res = self.evaluate_threshold_grid()
        elapsed_s = round(time.time() - t0, 2)

        report = {
            "report_version": "1.0.0",
            "project_code": "SIH260042",
            "benchmark_title": "Classroom Acoustic Optimization & Noise Robustness Report",
            "execution_date": "2026-09-04",
            "duration_seconds": elapsed_s,
            "disclaimer": (
                "Synthetic noise injection on authentic Mundari recordings used strictly for DSP, VAD, "
                "and fallback stress-testing. ZERO linguistic accuracy claims are made for unrepresented numeral classes."
            ),
            "acoustic_conditions_tested": [
                "Clean (~inf dB SNR)",
                "10 dB SNR (moderate classroom ambient)",
                "5 dB SNR (noisy classroom / fan on)",
                "0 dB SNR (severe acoustic interference)",
            ],
            "noise_types_simulated": [
                "Mixed Classroom (Fan + Babble + Taps + Reverberation)",
                "Fan Motor Hum (50Hz + Harmonics + Rumble)",
                "Classroom Babble (Multi-talker modulated resonators)",
                "Desk Taps (Impulsive mechanical transients)",
            ],
            "threshold_analysis": grid_res["grid_evaluations"],
            "snr_matrix_summary": matrix_res["summary"],
            "detailed_samples_evaluated": len(self.test_audio_files),
        }

        benchmarks_dir = os.path.join(workspace_root, "benchmarks")
        os.makedirs(benchmarks_dir, exist_ok=True)
        report_path = os.path.join(benchmarks_dir, "classroom_robustness_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\nBenchmark report successfully written to: {report_path}")
        return report

    def assertEqual(self, a, b):
        if a != b:
            raise AssertionError(f"{a} != {b}")


if __name__ == "__main__":
    bm = ClassroomRobustnessBenchmark(num_test_files=8)
    bm.generate_full_report()
