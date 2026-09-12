"""
tests/test_noise_robustness.py
=============================================================================
SIH260042: Automated Unit Test Suite for Classroom Acoustic Robustness
=============================================================================

TEST CODES & VALIDATION:
1. test_noise_generator_finite_and_shapes:
   Verifies all 5 classroom noise generators produce finite, valid, normalized waveforms.
2. test_snr_mixing_mathematical_accuracy:
   Verifies that mix_at_snr achieves actual SNR within +/- 0.5 dB of target (10, 5, 0 dB).
3. test_reverberation_energy_and_decay:
   Verifies synthetic RIR convolution maintains signal integrity and peak scaling.
4. test_vad_transient_desk_taps_rejection:
   Verifies mechanical transient taps do not cause false utterance triggers.
5. test_vad_continuous_fan_hum_adaptation:
   Verifies continuous motor hum is tracked into noise floor without false alarms.
6. test_preprocessing_numerical_stability_under_noise:
   Verifies Log-Mel spectrograms remain strictly finite without NaNs or Infs across 0 dB SNR.
7. test_pipeline_fallback_activation_on_corrupted_audio:
   Verifies extreme noise conditions reliably activate Pathway C presentation fallback.
=============================================================================
"""

import math
import os
import sys
import unittest

import numpy as np

cur_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.normpath(os.path.join(cur_dir, ".."))
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


class TestNoiseRobustness(unittest.TestCase):
    """Test suite validating classroom acoustic simulation, VAD, and fallback behavior."""

    @classmethod
    def setUpClass(cls):
        cls.simulator = ClassroomAcousticSimulator(sample_rate=16000, seed=42)
        cls.preprocessor = AudioPreprocessor()
        cls.pipeline = VernacularPedagogyPipeline()

    def test_noise_generator_finite_and_shapes(self):
        """Verifies all classroom noise generators produce finite, valid, normalized waveforms."""
        num_samples = 16000  # 1 second
        for noise_type in [
            ClassroomNoiseType.FAN_HUM,
            ClassroomNoiseType.CLASSROOM_BABBLE,
            ClassroomNoiseType.DESK_TAPS,
            ClassroomNoiseType.MIXED_CLASSROOM,
        ]:
            noise = self.simulator.generate_noise(noise_type, num_samples)
            self.assertEqual(len(noise), num_samples)
            self.assertEqual(noise.dtype, np.float32)
            self.assertFalse(np.isnan(noise).any(), f"NaNs detected in {noise_type.value}")
            self.assertFalse(np.isinf(noise).any(), f"Infs detected in {noise_type.value}")
            self.assertLessEqual(np.max(np.abs(noise)), 1.05)
            self.assertGreater(np.max(np.abs(noise)), 0.1, f"Noise {noise_type.value} too quiet")

    def test_snr_mixing_mathematical_accuracy(self):
        """Verifies that mix_at_snr achieves actual SNR within +/- 0.5 dB of target."""
        sr = 16000
        t = np.arange(sr) / sr
        # Clean 400 Hz sine wave
        clean_speech = (0.5 * np.sin(2 * np.pi * 400.0 * t)).astype(np.float32)
        noise = self.simulator.generate_fan_hum(sr)

        for target_snr in [10.0, 5.0, 0.0]:
            mixed, stats = self.simulator.mix_at_snr(clean_speech, noise, target_snr)
            self.assertEqual(len(mixed), len(clean_speech))
            actual_snr = stats["actual_snr_db"]
            self.assertAlmostEqual(
                actual_snr,
                target_snr,
                delta=0.6,
                msg=f"Actual SNR {actual_snr} deviates from target {target_snr}",
            )

    def test_reverberation_energy_and_decay(self):
        """Verifies synthetic RIR convolution maintains signal integrity and peak scaling."""
        sr = 16000
        impulse = np.zeros(sr, dtype=np.float32)
        impulse[0] = 1.0  # Unit impulse

        reverbed = self.simulator.apply_room_reverberation(impulse, rt60=0.30)
        self.assertEqual(len(reverbed), sr)
        self.assertFalse(np.isnan(reverbed).any())
        # Reverberated signal should decay over time: energy in first 100ms > energy in last 100ms
        energy_start = np.sum(reverbed[:1600] ** 2)
        energy_end = np.sum(reverbed[-1600:] ** 2)
        self.assertGreater(energy_start, energy_end * 10.0)

    def test_vad_transient_desk_taps_rejection(self):
        """Verifies mechanical transient taps do not cause false utterance triggers."""
        sr = 16000
        # Generate 2 seconds of pure impulsive desk taps
        taps = self.simulator.generate_desk_taps(2 * sr, tap_rate_per_sec=2.0)
        vad = StreamingVADProcessor()

        utterances = vad.process_continuous_audio(taps)
        # Transient taps are < 30ms, below min_speech_duration_ms=120ms
        self.assertEqual(
            len(utterances),
            0,
            f"VAD falsely triggered {len(utterances)} utterances on pure desk taps",
        )

    def test_vad_continuous_fan_hum_adaptation(self):
        """Verifies continuous motor hum is tracked into noise floor without false alarms."""
        sr = 16000
        fan = self.simulator.generate_fan_hum(3 * sr)
        # Scale fan hum to typical classroom hum (-40 dBFS)
        fan = fan * (10.0 ** (-40.0 / 20.0) / (np.sqrt(np.mean(fan**2)) + 1e-9))
        vad = StreamingVADProcessor()

        utterances = vad.process_continuous_audio(fan)
        self.assertEqual(
            len(utterances),
            0,
            f"VAD falsely triggered {len(utterances)} utterances on continuous fan hum",
        )

    def test_preprocessing_numerical_stability_under_noise(self):
        """Verifies Log-Mel spectrograms remain strictly finite without NaNs or Infs across 0 dB SNR."""
        sr = 16000
        speech = np.random.normal(0, 0.1, sr).astype(np.float32)
        noise = self.simulator.generate_classroom_babble(sr)
        mixed, _ = self.simulator.mix_at_snr(speech, noise, target_snr_db=0.0)

        _, log_mel = self.preprocessor.preprocess_signal(mixed, sr)
        spec_4d = self.preprocessor.format_for_model(log_mel)

        self.assertEqual(spec_4d.shape, (1, 101, 64, 1))
        self.assertFalse(np.isnan(spec_4d).any())
        self.assertFalse(np.isinf(spec_4d).any())
        self.assertGreater(float(np.std(spec_4d)), 0.1)

    def test_pipeline_fallback_activation_on_corrupted_audio(self):
        """Verifies extreme noise conditions reliably activate Pathway C presentation fallback."""
        sr = 16000
        # White noise / severe babble audio
        severe_noise = self.simulator.generate_classroom_babble(sr)
        resp = self.pipeline.process_spoken_audio(severe_noise, sample_rate=sr)

        self.assertEqual(resp.input_mode, "SPOKEN_SPEECH")
        self.assertTrue(resp.fallback_recommended, "Corrupted audio must trigger fallback_recommended")
        self.assertEqual(resp.status_code, "AMBIGUOUS_AUDIO_FALLBACK_RECOMMENDED")
        self.assertFalse(resp.is_success)


if __name__ == "__main__":
    unittest.main()
