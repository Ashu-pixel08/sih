import os
import glob
import math
import wave
import unittest
import numpy as np

from ai.preprocessing.audio_preprocessor import AudioPreprocessor, AudioPreprocessingConfig
from ai.preprocessing.audio_validator import AudioValidator, AudioValidationResult

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestAudioPreprocessing(unittest.TestCase):

    def setUp(self):
        self.config = AudioPreprocessingConfig()
        self.preprocessor = AudioPreprocessor(self.config)
        self.validator = AudioValidator()

    def test_configuration_and_tensor_shape(self):
        """Verify explicit preprocessing parameters and mathematical tensor shape."""
        self.assertEqual(self.config.target_sample_rate, 16000)
        self.assertEqual(self.config.target_channels, 1)
        self.assertEqual(self.config.target_samples, 16000)
        self.assertEqual(self.config.win_length, 400)
        self.assertEqual(self.config.hop_length, 160)
        self.assertEqual(self.config.n_fft, 512)
        self.assertEqual(self.config.n_mels, 64)
        self.assertEqual(self.config.f_min, 20.0)
        self.assertEqual(self.config.f_max, 8000.0)

        # Verified mathematically: (16000 + 400 - 400) // 160 + 1 = 101 frames
        expected_shape = (1, 101, 64, 1)
        self.assertEqual(self.preprocessor.output_tensor_shape, expected_shape)

    def test_mel_filterbank_properties(self):
        """Verify Mel filterbank matrix dimensions, non-negativity, and frequency coverage."""
        fb = self.preprocessor._mel_filterbank
        expected_shape = (64, 257)  # [n_mels, n_fft // 2 + 1]
        self.assertEqual(fb.shape, expected_shape)
        self.assertTrue(np.all(fb >= 0.0), "Mel filter weights must be non-negative")
        # Every filter must have at least one non-zero bin
        row_sums = np.sum(fb, axis=1)
        self.assertTrue(np.all(row_sums > 0.0), "Each Mel filter must cover active frequencies")

    def test_mono_conversion(self):
        """Verify 2D stereo signal converts to 1D mono via channel averaging."""
        stereo = np.array([[1.0, 0.0], [0.5, 0.5], [-0.5, 0.5]], dtype=np.float32)
        mono = self.preprocessor.to_mono(stereo)
        self.assertEqual(mono.ndim, 1)
        self.assertEqual(len(mono), 3)
        np.testing.assert_allclose(mono, [0.5, 0.5, 0.0], rtol=1e-5)

    def test_polyphase_resampling(self):
        """Verify accurate resampling from 44.1 kHz to 16 kHz."""
        orig_sr = 44100
        target_sr = 16000
        duration = 0.5  # 0.5 second sine wave
        t = np.linspace(0, duration, int(orig_sr * duration), endpoint=False)
        tone_freq = 440.0  # A4 note
        sine_44k = (0.5 * np.sin(2 * np.pi * tone_freq * t)).astype(np.float32)

        resampled = self.preprocessor.resample(sine_44k, orig_sr, target_sr)
        expected_len = int(round(len(sine_44k) * target_sr / orig_sr))
        self.assertEqual(len(resampled), expected_len)
        self.assertFalse(np.any(np.isnan(resampled)))
        self.assertFalse(np.any(np.isinf(resampled)))

    def test_fixed_duration_handling(self):
        """Verify zero-padding on short audio and cropping on long audio."""
        target_len = 16000

        # Short audio (8,000 samples)
        short_audio = np.ones(8000, dtype=np.float32)
        padded = self.preprocessor.fix_duration(short_audio, target_len, mode="center")
        self.assertEqual(len(padded), target_len)
        self.assertEqual(padded[0], 0.0)  # Left pad
        self.assertEqual(padded[-1], 0.0)  # Right pad
        self.assertEqual(padded[8000 // 2 + 100], 1.0)  # Center audio preserved

        # Long audio (32,000 samples)
        long_audio = np.linspace(0.0, 1.0, 32000, dtype=np.float32)
        cropped = self.preprocessor.fix_duration(long_audio, target_len, mode="center")
        self.assertEqual(len(cropped), target_len)

    def test_stft_and_log_mel_computation(self):
        """Verify STFT and Log-Mel computation produces valid, finite [101, 64] output."""
        audio_16k = (0.2 * np.sin(2 * np.pi * 500.0 * np.linspace(0, 1.0, 16000))).astype(np.float32)
        log_mel = self.preprocessor.compute_log_mel_spectrogram(audio_16k)

        self.assertEqual(log_mel.shape, (101, 64))
        self.assertEqual(log_mel.dtype, np.float32)
        self.assertFalse(np.any(np.isnan(log_mel)), "Spectrogram must not contain NaNs")
        self.assertFalse(np.any(np.isinf(log_mel)), "Spectrogram must not contain Infs")

        # Check model tensor formatting
        model_tensor = self.preprocessor.format_for_model(log_mel)
        self.assertEqual(model_tensor.shape, (1, 101, 64, 1))
        self.assertEqual(model_tensor.dtype, np.float32)

    def test_real_audio_preprocessing_e2e(self):
        """Test end-to-end preprocessing on an actual Mundari sample recording from corpus."""
        sample_files = glob.glob(os.path.join(BASE_DIR, "data", "raw", "speech", "data-sample", "*", "*.wav"))
        if not sample_files:
            self.skipTest("No sample WAV files found in data/raw/speech/data-sample")

        test_file = sample_files[0]
        audio_16k, log_mel = self.preprocessor.preprocess_file(test_file, crop_mode="energy_center")

        self.assertEqual(len(audio_16k), 16000, "Resampled audio must be exactly 16000 samples")
        self.assertEqual(log_mel.shape, (101, 64), "Spectrogram must be [101, 64]")
        model_tensor = self.preprocessor.format_for_model(log_mel)
        self.assertEqual(model_tensor.shape, (1, 101, 64, 1))

    def test_audio_validator_checks(self):
        """Verify audio validator detection of valid, silent, and invalid files."""
        # Test 1: Non-existent file
        res = self.validator.validate_file("non_existent_file.wav")
        self.assertFalse(res.is_valid)
        self.assertIn("File does not exist", res.issues)

        # Test 2: Synthetic valid WAV
        test_wav_path = os.path.join(BASE_DIR, "content", "audio", "processed", "temp_test_valid.wav")
        os.makedirs(os.path.dirname(test_wav_path), exist_ok=True)
        synthetic_pcm = (0.3 * np.sin(2 * np.pi * 440.0 * np.linspace(0, 1.0, 16000))).astype(np.float32)
        self.preprocessor.save_wav_16k(synthetic_pcm, test_wav_path)

        res_valid = self.validator.validate_file(test_wav_path)
        self.assertTrue(res_valid.is_valid, f"Synthetic file should be valid, got issues: {res_valid.issues}")
        self.assertEqual(res_valid.sample_rate, 16000)
        self.assertEqual(res_valid.channels, 1)
        self.assertEqual(res_valid.bit_depth, 16)
        self.assertFalse(res_valid.is_silent)
        self.assertFalse(res_valid.has_clipping)

        # Test 3: Synthetic silent WAV
        silent_wav_path = os.path.join(BASE_DIR, "content", "audio", "processed", "temp_test_silent.wav")
        silent_pcm = np.zeros(16000, dtype=np.float32)
        self.preprocessor.save_wav_16k(silent_pcm, silent_wav_path)

        res_silent = self.validator.validate_file(silent_wav_path)
        self.assertTrue(res_silent.is_silent)
        self.assertFalse(res_silent.is_valid)

        # Cleanup temp test files
        if os.path.exists(test_wav_path):
            os.remove(test_wav_path)
        if os.path.exists(silent_wav_path):
            os.remove(silent_wav_path)


if __name__ == "__main__":
    unittest.main()
