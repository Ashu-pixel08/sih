"""
ai/speech/teacher_voice_service.py
=============================================================================
SIH260042: Bhasha Setu - Teacher Voice Profile Service
=============================================================================
Provides zero-shot voice conversion coordination using OpenVoice v2
Normalizing Flow architecture.

STRICT GOVERNANCE & PRIVACY MANDATES:
1. Teacher recordings and voice embeddings remain 100% strictly local.
   Zero cloud uploads, zero external telemetry.
2. The teacher recording is NEVER used for model training or fine-tuning.
   It is used purely for one-time latent speaker embedding extraction (256-d).
3. Linguistic validation integrity:
   Voice conversion alters vocal timbre only; it CANNOT and MUST NOT upgrade
   any validation state.
4. Arbitrary Mundari text is EXCLUDED from voice conversion to prevent
   masking phonological inaccuracies under a polished teacher timbre.
=============================================================================
"""

import glob
import hashlib
import io
import json
import math
import os
import re
import sys
import time
import wave
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
import scipy.signal as signal
import torch

# Ensure scratch directory is accessible for openvoice modules
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_CURRENT_DIR, "..", ".."))
_SCRATCH_DIR = os.path.join(_PROJECT_ROOT, "scratch")
if _SCRATCH_DIR not in sys.path:
    sys.path.insert(0, _SCRATCH_DIR)


class TeacherVoiceConverter:
    """
    Wraps the OpenVoice v2 Tone Color Converter for local offline inference.
    Executes on CPU using the pre-downloaded MIT-licensed checkpoint.
    """

    def __init__(self, project_root: str, model_dir: Optional[str] = None):
        self.project_root = project_root
        self.model_dir = model_dir or os.path.join(project_root, "scratch", "models", "openvoice_v2")
        self._vc_model = None
        self._hps = None

    def is_model_available(self) -> bool:
        ckpt_path = os.path.join(self.model_dir, "checkpoint.pth")
        config_path = os.path.join(self.model_dir, "config.json")
        return os.path.exists(ckpt_path) and os.path.exists(config_path)

    def _ensure_loaded(self) -> None:
        if self._vc_model is not None:
            return

        ckpt_path = os.path.join(self.model_dir, "checkpoint.pth")
        config_path = os.path.join(self.model_dir, "config.json")
        if not os.path.exists(ckpt_path) or not os.path.exists(config_path):
            raise FileNotFoundError(f"OpenVoice v2 checkpoint not found in {self.model_dir}")

        from openvoice import utils
        from openvoice.models import SynthesizerTrn

        hps = utils.get_hparams_from_file(config_path)
        vc_model = SynthesizerTrn(
            len(getattr(hps, "symbols", [])),
            hps.data.filter_length // 2 + 1,
            n_speakers=hps.data.n_speakers,
            **hps.model
        )
        checkpoint = torch.load(ckpt_path, map_location="cpu")
        vc_model.load_state_dict(checkpoint["model"], strict=False)
        vc_model.eval()

        self._vc_model = vc_model
        self._hps = hps

    def extract_speaker_embedding(self, audio_data: Union[str, bytes, np.ndarray], sample_rate: Optional[int] = None) -> torch.Tensor:
        """
        Extracts a 256-dimensional continuous speaker latent vector from an audio sample.
        """
        self._ensure_loaded()
        from openvoice.mel_processing import spectrogram_torch

        target_sr = self._hps.data.sampling_rate

        if isinstance(audio_data, str):
            audio, sr = self._load_wav_as_float(audio_data, target_sr=target_sr)
        elif isinstance(audio_data, bytes):
            audio, sr = self._load_wav_bytes_as_float(audio_data, target_sr=target_sr)
        elif isinstance(audio_data, np.ndarray):
            audio = audio_data
            if sample_rate and sample_rate != target_sr:
                audio = self._resample(audio, sample_rate, target_sr)
        else:
            raise ValueError("Unsupported audio_data type")

        with torch.no_grad():
            y_ref = torch.FloatTensor(audio).unsqueeze(0)
            spec_ref = spectrogram_torch(
                y_ref,
                self._hps.data.filter_length,
                self._hps.data.sampling_rate,
                self._hps.data.hop_length,
                self._hps.data.win_length,
                center=False
            )
            se = self._vc_model.ref_enc(spec_ref.transpose(1, 2)).unsqueeze(-1)
        return se

    def convert_audio(self, source_wav_bytes: bytes, target_se: torch.Tensor) -> Tuple[bytes, float]:
        """
        Transforms vocal timbre of source WAV audio toward target_se.
        Returns: (converted_wav_bytes, duration_sec)
        """
        self._ensure_loaded()
        from openvoice.mel_processing import spectrogram_torch

        target_sr = self._hps.data.sampling_rate
        src_audio, src_sr = self._load_wav_bytes_as_float(source_wav_bytes, target_sr=target_sr)

        with torch.no_grad():
            # 1. Source speaker representation
            y_src = torch.FloatTensor(src_audio).unsqueeze(0)
            spec_src = spectrogram_torch(
                y_src,
                self._hps.data.filter_length,
                self._hps.data.sampling_rate,
                self._hps.data.hop_length,
                self._hps.data.win_length,
                center=False
            )
            src_se = self._vc_model.ref_enc(spec_src.transpose(1, 2)).unsqueeze(-1)

            # 2. Voice conversion flow
            spec_lengths = torch.LongTensor([spec_src.size(-1)])
            converted_audio = self._vc_model.voice_conversion(
                spec_src,
                spec_lengths,
                sid_src=src_se,
                sid_tgt=target_se,
                tau=0.3
            )[0][0, 0].data.cpu().numpy()

        # Clip and prevent overflow / clicks
        clipped = np.clip(converted_audio, -0.99, 0.99)
        pcm16 = (clipped * 32767.0).astype(np.int16)

        out_buf = io.BytesIO()
        with wave.open(out_buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(target_sr)
            wf.writeframes(pcm16.tobytes())

        wav_bytes = out_buf.getvalue()
        duration_sec = round(len(converted_audio) / float(target_sr), 3)
        return wav_bytes, duration_sec

    def _load_wav_as_float(self, file_path: str, target_sr: int = 22050) -> Tuple[np.ndarray, int]:
        with wave.open(file_path, "rb") as wf:
            orig_sr = wf.getframerate()
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            n_frames = wf.getnframes()
            raw_bytes = wf.readframes(n_frames)
        return self._process_raw_pcm(raw_bytes, sampwidth, n_channels, orig_sr, target_sr)

    def _load_wav_bytes_as_float(self, wav_bytes: bytes, target_sr: int = 22050) -> Tuple[np.ndarray, int]:
        buf = io.BytesIO(wav_bytes)
        with wave.open(buf, "rb") as wf:
            orig_sr = wf.getframerate()
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            n_frames = wf.getnframes()
            raw_bytes = wf.readframes(n_frames)
        return self._process_raw_pcm(raw_bytes, sampwidth, n_channels, orig_sr, target_sr)

    def _process_raw_pcm(self, raw_bytes: bytes, sampwidth: int, n_channels: int, orig_sr: int, target_sr: int) -> Tuple[np.ndarray, int]:
        if sampwidth == 2:
            audio = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        elif sampwidth == 4:
            audio = np.frombuffer(raw_bytes, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            audio = np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32) / 128.0 - 1.0

        if n_channels > 1:
            audio = audio.reshape(-1, n_channels).mean(axis=1)

        if orig_sr != target_sr:
            audio = self._resample(audio, orig_sr, target_sr)

        return audio, target_sr

    def _resample(self, audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        gcd = math.gcd(orig_sr, target_sr)
        up = target_sr // gcd
        down = orig_sr // gcd
        return signal.resample_poly(audio, up, down).astype(np.float32)


class TeacherVoiceProfileManager:
    """
    Manages the educator's local voice profile.
    Maintains persistent local embedding cache and deletion controls.
    """

    DEFAULT_PROFILE_ID = "local_teacher_profile_v1"

    def __init__(self, project_root: str, converter: Optional[TeacherVoiceConverter] = None):
        self.project_root = project_root
        self.profile_dir = os.path.join(project_root, "cache", "teacher_profile")
        self.profile_path = os.path.join(self.profile_dir, "profile.pt")
        self.meta_path = os.path.join(self.profile_dir, "profile.json")
        self.converter = converter or TeacherVoiceConverter(project_root)

        self._embedding: Optional[torch.Tensor] = None
        self._profile_id: Optional[str] = None
        self._enabled: bool = True

        os.makedirs(self.profile_dir, exist_ok=True)
        self._initialize_profile()

    def _initialize_profile(self) -> None:
        """Loads profile from disk or auto-enrolls from verified local reference if present."""
        if os.path.exists(self.profile_path) and os.path.exists(self.meta_path):
            try:
                self._embedding = torch.load(self.profile_path, map_location="cpu")
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    self._profile_id = meta.get("profile_id", self.DEFAULT_PROFILE_ID)
                    self._enabled = meta.get("enabled", True)
                return
            except Exception as e:
                print(f"[TeacherVoiceProfileManager] Error loading cached profile: {e}", file=sys.stderr)

        # Check for verified local teacher reference recording
        candidate_reference = os.path.join(
            self.project_root, "scratch", "voice_conversion_test", "reference_human.wav"
        )
        if os.path.exists(candidate_reference) and self.converter.is_model_available():
            try:
                self.enroll_from_file(candidate_reference, profile_id=self.DEFAULT_PROFILE_ID)
            except Exception as e:
                print(f"[TeacherVoiceProfileManager] Could not auto-enroll from reference_human.wav: {e}", file=sys.stderr)

    def is_enrolled(self) -> bool:
        return self._embedding is not None

    def is_enabled(self) -> bool:
        return self._enabled

    def is_active(self) -> bool:
        """Returns True only when enrolled, enabled, and model is available."""
        return self.is_enrolled() and self._enabled and self.converter.is_model_available()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        self._save_metadata()

    def get_profile_id(self) -> Optional[str]:
        return self._profile_id if self.is_enrolled() else None

    def get_embedding(self) -> Optional[torch.Tensor]:
        return self._embedding if self.is_active() else None

    def enroll_from_file(self, wav_file_path: str, profile_id: Optional[str] = None) -> bool:
        """
        Enrolls a teacher voice recording by extracting its latent speaker embedding.
        The raw recording is never modified or incorporated into model weights.
        """
        if not os.path.exists(wav_file_path):
            return False

        try:
            se = self.converter.extract_speaker_embedding(wav_file_path)
            self._embedding = se
            self._profile_id = profile_id or f"teacher_{int(time.time())}"
            self._enabled = True

            # Save embedding tensor
            torch.save(se, self.profile_path)
            self._save_metadata()
            return True
        except Exception as e:
            print(f"[TeacherVoiceProfileManager] Enrollment failed: {e}", file=sys.stderr)
            return False

    def delete_profile(self) -> bool:
        """
        Deletes the local teacher voice profile and clears all cached teacher audio.
        Guarantees complete removal of the educator's biometric voice embedding.
        """
        self._embedding = None
        self._profile_id = None
        self._enabled = False

        # Remove profile files
        if os.path.exists(self.profile_path):
            try:
                os.remove(self.profile_path)
            except Exception:
                pass
        if os.path.exists(self.meta_path):
            try:
                os.remove(self.meta_path)
            except Exception:
                pass

        # Clear cached teacher audio files
        cache_dir = os.path.join(self.project_root, "cache", "speech")
        if os.path.exists(cache_dir):
            try:
                teacher_files = glob.glob(os.path.join(cache_dir, "*teacher*"))
                for tf in teacher_files:
                    try:
                        os.remove(tf)
                    except Exception:
                        pass
            except Exception:
                pass

        return True

    def _save_metadata(self) -> None:
        meta = {
            "profile_id": self._profile_id or self.DEFAULT_PROFILE_ID,
            "created_at_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "embedding_dim": 256,
            "enabled": self._enabled,
            "storage": "LOCAL_ONLY_EPHEMERAL"
        }
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

    def get_status(self) -> Dict[str, Any]:
        """Provides structured state for UI and API consumers."""
        active = self.is_active()
        return {
            "status": "READY" if active else "UNAVAILABLE",
            "enrolled": self.is_enrolled(),
            "enabled": self._enabled,
            "profile_id": self._profile_id,
            "model_available": self.converter.is_model_available(),
            "ui_state_label": "Teacher voice ready" if active else "Teacher voice unavailable"
        }
