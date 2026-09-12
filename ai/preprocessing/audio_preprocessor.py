"""
Audio Preprocessor Module for FLN Pedagogy & Speech Pipeline.

Implements the formal preprocessing contract shared between Python and Android (Kotlin):
- 16 kHz high-quality polyphase resampling
- Single-channel (mono) conversion
- 16-bit linear PCM normalization to Float32 [-1.0, 1.0]
- Fixed 1.0-second window duration (16,000 samples)
- STFT with Hann window (size 400, hop 160, FFT 512)
- 64-bin Mel filterbank generation spanning 20 Hz to 8000 Hz
- Log compression: log(mel_energy + 1e-6)
- Verified Output Tensor Shape: [1, 101, 64, 1] (Float32)
"""

import os
import math
import wave
from dataclasses import dataclass
from typing import Optional, Tuple, Literal
import numpy as np
import scipy.signal as signal


@dataclass
class AudioPreprocessingConfig:
    """Explicit parameters governing audio preprocessing contract."""
    target_sample_rate: int = 16000
    target_channels: int = 1
    duration_seconds: float = 1.0
    target_samples: int = 16000  # sample_rate * duration
    win_length: int = 400        # 25 ms window at 16 kHz
    hop_length: int = 160        # 10 ms hop at 16 kHz
    n_fft: int = 512             # FFT size
    n_mels: int = 64             # Number of Mel filterbank bins
    f_min: float = 20.0          # Minimum frequency in Hz
    f_max: float = 8000.0        # Maximum frequency in Hz (Nyquist at 16 kHz)
    center_padding: bool = True  # Symmetric padding for centered STFT
    log_offset: float = 1e-6     # Numerical stabilizer for log compression
    dtype: str = "float32"       # Final tensor dtype


class AudioPreprocessor:
    """Preprocesses raw audio into standardized tensors for edge speech recognition."""

    def __init__(self, config: Optional[AudioPreprocessingConfig] = None):
        self.config = config or AudioPreprocessingConfig()
        self._mel_filterbank = self._build_mel_filterbank()
        self._hann_window = self._build_hann_window()

    @property
    def output_tensor_shape(self) -> Tuple[int, int, int, int]:
        """
        Computes the exact tensor dimensions based on configuration:
        [Batch, TimeFrames, MelBins, Channels].
        """
        if self.config.center_padding:
            pad = self.config.win_length // 2
            total_samples = self.config.target_samples + 2 * pad
        else:
            total_samples = self.config.target_samples

        num_frames = (total_samples - self.config.win_length) // self.config.hop_length + 1
        return (1, num_frames, self.config.n_mels, 1)

    def _build_hann_window(self) -> np.ndarray:
        """Constructs periodic/symmetric Hann window matching standard DSP."""
        N = self.config.win_length
        n = np.arange(N)
        # 0.5 * (1 - cos(2 * pi * n / (N - 1)))
        return (0.5 * (1.0 - np.cos(2.0 * np.pi * n / (N - 1)))).astype(np.float32)

    def _hz_to_mel(self, hz: float) -> float:
        """Converts frequency in Hz to Mel scale using standard formula."""
        return 2595.0 * math.log10(1.0 + hz / 700.0)

    def _mel_to_hz(self, mel: float) -> float:
        """Converts Mel scale to frequency in Hz."""
        return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)

    def _build_mel_filterbank(self) -> np.ndarray:
        """
        Builds triangular Mel filterbank matrix of shape [n_mels, n_fft // 2 + 1].
        Matches exact formulation to be mirrored in Android Kotlin implementation.
        """
        num_fft_bins = self.config.n_fft // 2 + 1
        mel_min = self._hz_to_mel(self.config.f_min)
        mel_max = self._hz_to_mel(self.config.f_max)

        # Linearly spaced points in Mel scale
        mel_points = np.linspace(mel_min, mel_max, self.config.n_mels + 2)
        hz_points = np.array([self._mel_to_hz(m) for m in mel_points])

        # Convert Hz to FFT bin indices
        bin_points = np.floor((self.config.n_fft + 1) * hz_points / self.config.target_sample_rate).astype(int)

        weights = np.zeros((self.config.n_mels, num_fft_bins), dtype=np.float32)

        for m in range(1, self.config.n_mels + 1):
            left = bin_points[m - 1]
            center = bin_points[m]
            right = bin_points[m + 1]

            # Up-slope
            if center > left:
                for k in range(left, center):
                    if k < num_fft_bins:
                        weights[m - 1, k] = (k - left) / float(center - left)

            # Down-slope
            if right > center:
                for k in range(center, right):
                    if k < num_fft_bins:
                        weights[m - 1, k] = (right - k) / float(right - center)

        # Slaney area normalization: 2.0 / (hz[m+1] - hz[m-1])
        for m in range(self.config.n_mels):
            enorm = 2.0 / (hz_points[m + 2] - hz_points[m])
            weights[m] *= enorm

        return weights

    def load_wav(self, file_path: str) -> Tuple[np.ndarray, int]:
        """Loads WAV audio file into float32 array [-1.0, 1.0] and returns (audio, sample_rate)."""
        with wave.open(file_path, "rb") as wf:
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            sr = wf.getframerate()
            n_frames = wf.getnframes()
            raw_bytes = wf.readframes(n_frames)

        if sampwidth == 1:
            audio = (np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
        elif sampwidth == 2:
            audio = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        elif sampwidth == 3:
            total_samples = len(raw_bytes) // 3
            audio = np.zeros(total_samples, dtype=np.float32)
            for i in range(total_samples):
                sample_bytes = raw_bytes[i * 3 : (i + 1) * 3]
                int_val = int.from_bytes(sample_bytes, byteorder="little", signed=True)
                audio[i] = int_val / 8388608.0
        elif sampwidth == 4:
            raw_int32 = np.frombuffer(raw_bytes, dtype=np.int32)
            if np.max(np.abs(raw_int32)) > 1.0:
                audio = raw_int32.astype(np.float32) / 2147483648.0
            else:
                audio = np.frombuffer(raw_bytes, dtype=np.float32)
        else:
            raise ValueError(f"Unsupported sample width: {sampwidth} bytes")

        if channels > 1:
            audio = audio.reshape(-1, channels)
            audio = np.mean(audio, axis=1)

        return audio.astype(np.float32), sr

    def to_mono(self, audio: np.ndarray) -> np.ndarray:
        """Converts multi-channel audio to single-channel mono."""
        if audio.ndim > 1:
            return np.mean(audio, axis=1).astype(np.float32)
        return audio.astype(np.float32)

    def resample(self, audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """
        Resamples audio signal using reproducible polyphase FIR filtering.
        """
        if orig_sr == target_sr:
            return audio.astype(np.float32)

        gcd = math.gcd(orig_sr, target_sr)
        up = target_sr // gcd
        down = orig_sr // gcd

        resampled = signal.resample_poly(audio, up, down)
        return resampled.astype(np.float32)

    def fix_duration(
        self,
        audio: np.ndarray,
        target_samples: Optional[int] = None,
        mode: Literal["center", "right", "energy_center"] = "center",
    ) -> np.ndarray:
        """
        Ensures the audio is exactly target_samples in length by padding or cropping.
        """
        target_len = target_samples or self.config.target_samples
        current_len = len(audio)

        if current_len == target_len:
            return audio.copy()

        if current_len < target_len:
            pad_total = target_len - current_len
            if mode == "center":
                pad_left = pad_total // 2
                pad_right = pad_total - pad_left
                return np.pad(audio, (pad_left, pad_right), mode="constant")
            else:  # right padding
                return np.pad(audio, (0, pad_total), mode="constant")

        # Crop if longer
        if mode == "energy_center":
            # Find window with maximum RMS energy
            window_size = target_len
            step = max(1, self.config.hop_length)
            best_idx = 0
            max_energy = -1.0
            for start in range(0, current_len - window_size + 1, step):
                chunk = audio[start : start + window_size]
                energy = np.sum(chunk**2)
                if energy > max_energy:
                    max_energy = energy
                    best_idx = start
            return audio[best_idx : best_idx + window_size].copy()

        elif mode == "center":
            crop_start = (current_len - target_len) // 2
            return audio[crop_start : crop_start + target_len].copy()
        else:  # leading
            return audio[:target_len].copy()

    def compute_stft(self, audio: np.ndarray) -> np.ndarray:
        """
        Computes Short-Time Fourier Transform (STFT) power spectrum.
        Returns power spectrogram of shape [num_frames, n_fft // 2 + 1].
        """
        win_len = self.config.win_length
        hop_len = self.config.hop_length
        n_fft = self.config.n_fft

        if self.config.center_padding:
            pad = win_len // 2
            padded_audio = np.pad(audio, (pad, pad), mode="reflect")
        else:
            padded_audio = audio

        num_frames = (len(padded_audio) - win_len) // hop_len + 1
        power_spectrum = np.zeros((num_frames, n_fft // 2 + 1), dtype=np.float32)

        for i in range(num_frames):
            start = i * hop_len
            frame = padded_audio[start : start + win_len] * self._hann_window
            # rfft computes one-sided FFT (n_fft // 2 + 1 complex bins)
            fft_complex = np.fft.rfft(frame, n=n_fft)
            # Power spectrum: |X|^2
            power_spectrum[i] = np.abs(fft_complex) ** 2

        return power_spectrum

    def compute_log_mel_spectrogram(self, audio_16k: np.ndarray) -> np.ndarray:
        """
        Computes Log-Mel spectrogram from 16kHz audio array.
        Output shape: [num_frames, n_mels] (e.g. [101, 64]).
        """
        # Step 1: Compute STFT power spectrogram [num_frames, 257]
        power_spec = self.compute_stft(audio_16k)

        # Step 2: Project onto Mel filterbank [num_frames, 64]
        mel_spec = np.dot(power_spec, self._mel_filterbank.T)

        # Step 3: Log compression with stabilizer
        log_mel = np.log(mel_spec + self.config.log_offset)

        return log_mel.astype(np.float32)

    def preprocess_signal(
        self, audio: np.ndarray, sample_rate: int, crop_mode: str = "center"
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        End-to-end signal processing:
        1. Mono conversion
        2. Resample to 16 kHz
        3. Fixed-duration windowing (1.0s = 16,000 samples)
        4. Log-Mel spectrogram computation
        Returns: (fixed_audio_16k, log_mel_spectrogram)
        """
        mono = self.to_mono(audio)
        resampled = self.resample(mono, sample_rate, self.config.target_sample_rate)
        fixed_audio = self.fix_duration(resampled, self.config.target_samples, mode=crop_mode)
        log_mel = self.compute_log_mel_spectrogram(fixed_audio)

        return fixed_audio, log_mel

    def preprocess_file(self, file_path: str, crop_mode: str = "center") -> Tuple[np.ndarray, np.ndarray]:
        """Loads WAV from disk and computes standardized 16kHz audio and Log-Mel spectrogram."""
        audio, sr = self.load_wav(file_path)
        return self.preprocess_signal(audio, sr, crop_mode=crop_mode)

    def format_for_model(self, log_mel: np.ndarray) -> np.ndarray:
        """
        Reshapes 2D spectrogram [101, 64] to 4D CNN batch tensor [1, 101, 64, 1].
        """
        return np.expand_dims(np.expand_dims(log_mel, axis=0), axis=-1).astype(np.float32)

    def save_wav_16k(self, audio_16k: np.ndarray, output_path: str) -> None:
        """Saves 1D float32 audio as 16-bit PCM 16kHz mono WAV."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        int16_audio = np.clip(audio_16k * 32767.0, -32768.0, 32767.0).astype(np.int16)
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.config.target_sample_rate)
            wf.writeframes(int16_audio.tobytes())

    def save_spectrogram_image(self, log_mel: np.ndarray, output_png_path: str) -> None:
        """
        Generates and writes a normalized grayscale visual image of the spectrogram.
        Uses pure Python/NumPy to generate a uncompressed BMP/PPM or standard image.
        """
        os.makedirs(os.path.dirname(output_png_path), exist_ok=True)
        # Normalize to 0-255
        spec_min = np.min(log_mel)
        spec_max = np.max(log_mel)
        if spec_max > spec_min:
            norm = ((log_mel - spec_min) / (spec_max - spec_min) * 255.0).astype(np.uint8)
        else:
            norm = np.zeros_like(log_mel, dtype=np.uint8)

        # Transpose so time is on X-axis (width) and frequency is on Y-axis (height, inverted)
        # log_mel is [TimeFrames, MelBins] -> [101, 64]
        # Image matrix: height=64, width=101
        img_matrix = np.flipud(norm.T)  # low frequency at bottom
        height, width = img_matrix.shape

        # Write as Netpbm PGM (portable graymap) or PPM, readable by all standard viewers
        ppm_path = os.path.splitext(output_png_path)[0] + ".pgm"
        with open(ppm_path, "wb") as f:
            header = f"P5\n{width} {height}\n255\n".encode("ascii")
            f.write(header)
            f.write(img_matrix.tobytes())


if __name__ == "__main__":
    preprocessor = AudioPreprocessor()
    print("Audio Preprocessor initialized.")
    print("Verified Output Tensor Shape:", preprocessor.output_tensor_shape)
