"""
ai/speech/classroom_acoustic_simulator.py
=============================================================================
SIH260042: AI-Powered Vernacular Pedagogy & Real-Time Translation
Classroom Acoustic Simulator & Noise Robustness Evaluation Suite
=============================================================================

PURPOSE & METHODOLOGY:
- Simulates realistic acoustic conditions of rural primary schools in Jharkhand:
  1. Fan/Motor Hum: 50 Hz fundamental + harmonics + low-frequency brown noise.
  2. Classroom Babble: Overlapping multi-child vocal murmur (formants + syllabic rhythm).
  3. Desk Taps / Impulsive: Sharp acoustic transients (< 30ms) from desks/slates.
  4. Room Reverberation: Exponentially decaying room impulse response (RT60 ~ 0.3s).
  5. Mixed Classroom: Composite realistic background environment.
- Injects simulated noise over AUTHENTIC Mundari speech recordings at precise
  Signal-to-Noise Ratios (Clean, 10 dB, 5 dB, 0 dB).
- STRICT POLICY: Synthetic noise is used exclusively for signal-processing, VAD,
  and fallback stress-testing; it is NEVER used to claim real linguistic accuracy.
=============================================================================
"""

import math
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import scipy.signal as signal


class ClassroomNoiseType(Enum):
    CLEAN = "CLEAN"
    FAN_HUM = "FAN_HUM"
    CLASSROOM_BABBLE = "CLASSROOM_BABBLE"
    DESK_TAPS = "DESK_TAPS"
    ROOM_REVERBERATION = "ROOM_REVERBERATION"
    MIXED_CLASSROOM = "MIXED_CLASSROOM"


class ClassroomAcousticSimulator:
    """
    Generates synthetic classroom noise and convolutive room acoustic distortions
    to stress-test VAD, audio preprocessing, and pipeline fallback mechanisms.
    """

    def __init__(self, sample_rate: int = 16000, seed: int = 42):
        self.sample_rate = sample_rate
        self.rng = np.random.RandomState(seed)

    def generate_fan_hum(self, num_samples: int) -> np.ndarray:
        """
        Generates 50 Hz electrical/fan motor hum with harmonics (100, 150, 200 Hz)
        combined with low-pass motor rumble.
        """
        t = np.arange(num_samples) / float(self.sample_rate)
        # Fundamental and harmonics
        hum = (
            0.60 * np.sin(2 * np.pi * 50.0 * t)
            + 0.25 * np.sin(2 * np.pi * 100.0 * t + 0.5)
            + 0.15 * np.sin(2 * np.pi * 150.0 * t + 1.2)
            + 0.08 * np.sin(2 * np.pi * 200.0 * t + 2.1)
        )
        # Low-frequency motor rumble (Brown noise filtered < 300 Hz)
        white = self.rng.normal(0, 1.0, num_samples)
        b, a = signal.butter(2, 300.0 / (self.sample_rate / 2.0), btype="low")
        rumble = signal.lfilter(b, a, white)
        rumble = rumble / (np.std(rumble) + 1e-8)

        fan = hum + 0.40 * rumble
        fan = fan / (np.max(np.abs(fan)) + 1e-8)
        return fan.astype(np.float32)

    def generate_classroom_babble(self, num_samples: int) -> np.ndarray:
        """
        Simulates multi-child classroom background babble:
        Resonant vocal formants (F1~500Hz, F2~1500Hz, F3~2500Hz) modulated by
        a 3–5 Hz syllabic rhythm envelope.
        """
        # Excite three formant resonators with pink-ish noise
        white = self.rng.normal(0, 1.0, num_samples)
        babble_signal = np.zeros(num_samples, dtype=np.float64)

        formants = [
            (450.0, 80.0, 0.50),   # F1
            (1450.0, 120.0, 0.35), # F2
            (2400.0, 200.0, 0.20), # F3
        ]

        for freq, bw, gain in formants:
            w0 = freq / (self.sample_rate / 2.0)
            q = freq / bw
            b, a = signal.iirpeak(w0, q)
            filtered = signal.lfilter(b, a, white)
            babble_signal += gain * filtered

        # Apply syllabic amplitude modulation (3 to 5 Hz speech rate)
        t = np.arange(num_samples) / float(self.sample_rate)
        mod1 = 0.5 + 0.5 * np.sin(2 * np.pi * 3.5 * t + 0.3)
        mod2 = 0.5 + 0.5 * np.sin(2 * np.pi * 4.8 * t + 1.7)
        envelope = 0.6 * mod1 + 0.4 * mod2

        babble = babble_signal * envelope
        babble = babble / (np.std(babble) + 1e-8)
        return (babble / (np.max(np.abs(babble)) + 1e-8)).astype(np.float32)

    def generate_desk_taps(
        self, num_samples: int, tap_rate_per_sec: float = 2.0, min_spacing_ms: float = 200.0
    ) -> np.ndarray:
        """
        Generates sparse impulsive mechanical transients (< 30ms) mimicking
        desk drumming, pencil taps, slate clicks, and footsteps.
        Enforces realistic inter-tap physical spacing (>= 200ms).
        """
        taps = np.zeros(num_samples, dtype=np.float32)
        total_seconds = num_samples / float(self.sample_rate)
        num_taps = max(1, int(total_seconds * tap_rate_per_sec))

        # Exponential decaying burst template (~20 ms)
        decay_samples = int(0.025 * self.sample_rate)
        decay_env = np.exp(-np.linspace(0, 6, decay_samples)).astype(np.float32)
        burst_carrier = np.sin(2 * np.pi * 1200.0 * np.arange(decay_samples) / self.sample_rate).astype(np.float32)
        tap_template = decay_env * burst_carrier

        min_spacing_samples = int((min_spacing_ms / 1000.0) * self.sample_rate)
        placed_positions: List[int] = []

        attempts = 0
        while len(placed_positions) < num_taps and attempts < num_taps * 20:
            attempts += 1
            pos = self.rng.randint(0, max(1, num_samples - decay_samples))
            if all(abs(pos - p) >= min_spacing_samples for p in placed_positions):
                placed_positions.append(pos)
                amplitude = self.rng.uniform(0.5, 1.0)
                taps[pos : pos + decay_samples] += amplitude * tap_template

        taps = taps / (np.max(np.abs(taps)) + 1e-8)
        return taps.astype(np.float32)

    def apply_room_reverberation(self, audio: np.ndarray, rt60: float = 0.30) -> np.ndarray:
        """
        Simulates acoustic reflection in an untreated rural classroom
        (concrete floor, brick walls) with RT60 around 0.25 to 0.35 seconds.
        """
        # Generate synthetic Room Impulse Response (RIR)
        rir_length = int(rt60 * self.sample_rate)
        t = np.arange(rir_length) / float(self.sample_rate)
        # Decay factor such that amplitude drops to -60 dB (0.001) at rt60
        decay = np.exp(-6.908 * t / rt60)
        noise = self.rng.normal(0, 1.0, rir_length)
        rir = noise * decay
        # Add early direct path spike
        rir[0] = 1.0
        rir = rir / np.sqrt(np.sum(rir**2) + 1e-8)

        # Fast FFT convolution
        reverbed = signal.fftconvolve(audio, rir, mode="full")[: len(audio)]
        # Preserve original peak scaling
        orig_peak = np.max(np.abs(audio)) + 1e-8
        rev_peak = np.max(np.abs(reverbed)) + 1e-8
        return (reverbed * (orig_peak / rev_peak)).astype(np.float32)

    def generate_noise(self, noise_type: ClassroomNoiseType, num_samples: int) -> np.ndarray:
        """Generates noise signal of specified type."""
        if noise_type == ClassroomNoiseType.CLEAN:
            return np.zeros(num_samples, dtype=np.float32)
        elif noise_type == ClassroomNoiseType.FAN_HUM:
            return self.generate_fan_hum(num_samples)
        elif noise_type == ClassroomNoiseType.CLASSROOM_BABBLE:
            return self.generate_classroom_babble(num_samples)
        elif noise_type == ClassroomNoiseType.DESK_TAPS:
            return self.generate_desk_taps(num_samples)
        elif noise_type == ClassroomNoiseType.MIXED_CLASSROOM:
            fan = self.generate_fan_hum(num_samples)
            babble = self.generate_classroom_babble(num_samples)
            taps = self.generate_desk_taps(num_samples, tap_rate_per_sec=1.5)
            mixed = 0.35 * fan + 0.45 * babble + 0.20 * taps
            return (mixed / (np.max(np.abs(mixed)) + 1e-8)).astype(np.float32)
        else:
            return np.zeros(num_samples, dtype=np.float32)

    def mix_at_snr(
        self, clean_speech: np.ndarray, noise: np.ndarray, target_snr_db: float
    ) -> Tuple[np.ndarray, Dict[str, float]]:
        """
        Mixes clean speech with noise at a calibrated Signal-to-Noise Ratio:
        SNR_dB = 10 * log10( RMS_speech^2 / RMS_noise^2 )
        """
        # Ensure length parity
        if len(noise) < len(clean_speech):
            repeats = int(math.ceil(len(clean_speech) / len(noise)))
            noise = np.tile(noise, repeats)[: len(clean_speech)]
        else:
            noise = noise[: len(clean_speech)]

        speech_rms = float(np.sqrt(np.mean(clean_speech**2)))
        noise_rms = float(np.sqrt(np.mean(noise**2)))

        if speech_rms < 1e-9:
            # Silent speech
            return noise.copy().astype(np.float32), {"actual_snr_db": -100.0, "speech_rms": speech_rms, "noise_rms": noise_rms}

        if noise_rms < 1e-9 or math.isinf(target_snr_db) or target_snr_db >= 80.0:
            # Clean signal
            return clean_speech.copy().astype(np.float32), {"actual_snr_db": 99.0, "speech_rms": speech_rms, "noise_rms": 0.0}

        # Calculate required noise scaling:
        # target_snr_db = 20 * log10(speech_rms / (scale * noise_rms))
        # scale = (speech_rms / noise_rms) / (10^(target_snr_db / 20))
        scale = (speech_rms / noise_rms) / (10.0 ** (target_snr_db / 20.0))
        scaled_noise = noise * scale

        mixed = clean_speech + scaled_noise

        # Peak normalization if clipping
        peak = np.max(np.abs(mixed))
        if peak > 0.99:
            mixed = mixed / (peak / 0.95)

        actual_speech_pwr = np.mean(clean_speech**2)
        actual_noise_pwr = np.mean(scaled_noise**2)
        actual_snr = 10.0 * math.log10(actual_speech_pwr / (actual_noise_pwr + 1e-12))

        return mixed.astype(np.float32), {
            "actual_snr_db": round(actual_snr, 2),
            "target_snr_db": target_snr_db,
            "scale_factor": round(float(scale), 6),
        }

    def simulate_classroom_utterance(
        self,
        clean_speech: np.ndarray,
        noise_type: ClassroomNoiseType = ClassroomNoiseType.MIXED_CLASSROOM,
        target_snr_db: float = 10.0,
        apply_reverb: bool = True,
        rt60_seconds: float = 0.28,
        lead_in_seconds: float = 0.5,
        lead_out_seconds: float = 0.6,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Creates a complete realistic classroom recording simulation:
        [Lead-in Background Silence/Noise] -> [Speech + Reverberation + Noise] -> [Lead-out Background Silence/Noise]
        """
        # Step 1: Optional reverberation on speech
        processed_speech = clean_speech.copy()
        if apply_reverb:
            processed_speech = self.apply_room_reverberation(processed_speech, rt60=rt60_seconds)

        lead_in_samples = int(lead_in_seconds * self.sample_rate)
        lead_out_samples = int(lead_out_seconds * self.sample_rate)
        speech_samples = len(processed_speech)
        total_samples = lead_in_samples + speech_samples + lead_out_samples

        # Step 2: Continuous noise stream across the whole recording
        full_noise = self.generate_noise(noise_type, total_samples)

        # Pad speech with silence
        padded_speech = np.zeros(total_samples, dtype=np.float32)
        padded_speech[lead_in_samples : lead_in_samples + speech_samples] = processed_speech

        # Step 3: Mix speech with continuous noise at target SNR during speech active window
        speech_rms = float(np.sqrt(np.mean(processed_speech**2)))
        noise_active_window = full_noise[lead_in_samples : lead_in_samples + speech_samples]
        noise_rms = float(np.sqrt(np.mean(noise_active_window**2)))

        if target_snr_db is not None and not math.isinf(target_snr_db):
            scale = (speech_rms / (noise_rms + 1e-9)) / (10.0 ** (target_snr_db / 20.0))
        else:
            scale = 0.0

        scaled_noise = full_noise * scale
        mixed_audio = padded_speech + scaled_noise

        # Ensure no clipping
        peak = np.max(np.abs(mixed_audio))
        if peak > 0.99:
            mixed_audio = mixed_audio / (peak / 0.95)

        return mixed_audio.astype(np.float32), {
            "noise_type": noise_type.value,
            "target_snr_db": target_snr_db,
            "reverb_applied": apply_reverb,
            "rt60_seconds": rt60_seconds if apply_reverb else 0.0,
            "lead_in_samples": lead_in_samples,
            "speech_samples": speech_samples,
            "lead_out_samples": lead_out_samples,
            "total_samples": total_samples,
            "total_duration_seconds": round(total_samples / self.sample_rate, 2),
        }
