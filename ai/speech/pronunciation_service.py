"""
ai/speech/pronunciation_service.py
=============================================================================
SIH260042: AI-Powered Vernacular Pedagogy & Real-Time Translation
Offline Pronunciation & Speech Synthesis (TTS) Service
=============================================================================

ARCHITECTURAL & GOVERNANCE MANDATE:
1. Purely local / offline execution. No cloud TTS API or external API keys.
2. Zero silent model downloads during API requests.
3. Strict separation of asset types:
   - Prototype synthetic audio assets (content/audio/prototype_tts) for FLN
     curriculum words (Numerals 1–20, Core Classroom Commands).
     * NEVER claimed as native-speaker verified or certified ground truth.
     * Suitable only for controlled prototype playback.
   - Neural TTS generated audio (via local Meta MMS-TTS VITS models when
     installed by the user/educator).
   - Unavailable status when required local assets/models are not installed.
4. Deterministic, safe caching (cache/speech/<hash>.wav) with zero path-traversal risk.
=============================================================================
"""

import hashlib
import io
import json
import os
import re
import sys
import wave
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class PronunciationResult:
    """Output metadata and audio payload from the pronunciation service."""
    audio_bytes: bytes
    language: str
    source_type: str  # "prototype_asset", "neural_tts", "cached", "teacher_voice", "teacher_voice_controlled"
    engine_name: str  # "prototype_audio_registry", "vits_mms_tts", etc.
    verification_status: str  # "PROTOTYPE_ONLY_PENDING_HUMAN_VALIDATION" or "SYNTHETIC_GENERATED_TTS"
    sample_rate: int = 16000
    is_cached: bool = False
    duration_sec: float = 0.0
    teacher_voice_applied: bool = False


class BasePronunciationProvider(ABC):
    """Abstract base class for language-specific pronunciation providers."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier for this provider."""
        pass

    @abstractmethod
    def is_available(self, language: str) -> bool:
        """Checks if this provider is actively usable for the target language."""
        pass

    @abstractmethod
    def generate(self, text: str, language: str) -> Optional[PronunciationResult]:
        """
        Generates or retrieves WAV audio bytes for the given text and language.
        Returns None if this provider cannot fulfill the request.
        """
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Returns structured diagnostic status for health reporting."""
        pass


class PrototypeAudioRegistryProvider(BasePronunciationProvider):
    """
    Serves pre-rendered prototype audio assets from the project manifest
    (content/audio/audio_manifest.json).

    CRITICAL GOVERNANCE LABEL:
    These assets are strictly PROTOTYPE / SYNTHETIC assets for FLN Grade 1
    classroom demonstration. They are NEVER claimed as native-speaker verified.
    """

    def __init__(self, project_root: str, manifest_path: Optional[str] = None):
        self.project_root = project_root
        self.manifest_path = manifest_path or os.path.join(
            project_root, "content", "audio", "audio_manifest.json"
        )
        self._lookup: Dict[str, Dict[str, Any]] = {}
        self.asset_count = 0
        self._load_manifest()

    @property
    def provider_id(self) -> str:
        return "prototype_audio_registry"

    def _normalize_key(self, text: str) -> str:
        """Normalize Devanagari text for key lookup (nukhta, whitespace, punctuation)."""
        t = text.strip()
        # Normalize common nukhta variations (e.g. ड़ vs ड़)
        t = t.replace("\u0921\u093c", "\u095c")  # ड़ -> ड़
        t = t.replace("\u0922\u093c", "\u095d")  # ढ़ -> ढ़
        # Remove trailing punctuation
        t = re.sub(r"[।?!.,:;]+$", "", t).strip()
        return t

    def _load_manifest(self) -> None:
        if not os.path.exists(self.manifest_path):
            return

        try:
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assets = data.get("assets", [])
            for item in assets:
                file_rel = item.get("audio_file", "")
                # Normalize Windows vs POSIX path separators
                file_path = os.path.join(self.project_root, file_rel.replace("\\", os.sep).replace("/", os.sep))
                if not os.path.exists(file_path):
                    continue

                m_text = item.get("mundari_text", "")
                h_text = item.get("hindi_text", "")

                entry = {
                    "content_id": item.get("content_id", ""),
                    "category": item.get("category", ""),
                    "mundari_text": m_text,
                    "hindi_text": h_text,
                    "file_path": file_path,
                    "duration_sec": item.get("duration_sec", 0.0),
                    "verification_status": "PROTOTYPE_ONLY_PENDING_HUMAN_VALIDATION"
                }

                if m_text:
                    # Index by Mundari text (both direct and normalized nukhta)
                    self._lookup[("mundari", m_text)] = entry
                    self._lookup[("mundari", self._normalize_key(m_text))] = entry
                    # Also index variants with/without nukhta
                    self._lookup[("mundari", m_text.replace("मोड़ेया", "मोड़ेया"))] = entry
                    self._lookup[("mundari", m_text.replace("मोड़ेया", "मोड़ेया"))] = entry

            self.asset_count = len(assets)
        except Exception as e:
            print(f"[PrototypeAudioRegistryProvider] Warning loading manifest: {e}", file=sys.stderr)

    def is_available(self, language: str) -> bool:
        norm_lang = language.lower().strip()
        if norm_lang in ("mundari", "unr"):
            return len(self._lookup) > 0
        return False

    def has_entry(self, text: str, language: str) -> bool:
        """Checks whether the given phrase exists in the controlled audio registry."""
        norm_lang = language.lower().strip()
        if norm_lang in ("unr", "mundari"):
            norm_lang = "mundari"
        elif norm_lang in ("hi", "hindi"):
            norm_lang = "hindi"
        else:
            return False

        clean_text = self._normalize_key(text)
        return (norm_lang, clean_text) in self._lookup or (norm_lang, text.strip()) in self._lookup

    def generate(self, text: str, language: str) -> Optional[PronunciationResult]:
        norm_lang = language.lower().strip()
        if norm_lang in ("unr", "mundari"):
            norm_lang = "mundari"
        elif norm_lang in ("hi", "hindi"):
            norm_lang = "hindi"
        else:
            return None

        clean_text = self._normalize_key(text)
        key = (norm_lang, clean_text)
        entry = self._lookup.get(key)
        if not entry:
            # Fallback check raw text
            entry = self._lookup.get((norm_lang, text.strip()))

        if not entry:
            return None

        file_path = entry["file_path"]
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, "rb") as f:
                wav_bytes = f.read()

            return PronunciationResult(
                audio_bytes=wav_bytes,
                language=norm_lang,
                source_type="prototype_asset",
                engine_name=self.provider_id,
                verification_status="PROTOTYPE_ONLY_PENDING_HUMAN_VALIDATION",
                sample_rate=16000,
                is_cached=False,
                duration_sec=entry.get("duration_sec", 0.0)
            )
        except Exception as e:
            print(f"[PrototypeAudioRegistryProvider] Error reading {file_path}: {e}", file=sys.stderr)
            return None

    def get_status(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "available": len(self._lookup) > 0,
            "registered_assets": self.asset_count,
            "disclaimer": "CRITICAL: Prototype audio assets are strictly for prototype demonstration and educational playback. They are NEVER claimed as native-speaker verified."
        }


class VitsTTSProvider(BasePronunciationProvider):
    """
    Offline neural VITS speech synthesis using Meta MMS-TTS architectures:
    - Hindi: facebook/mms-tts-hin
    - Mundari: facebook/mms-tts-unr

    CRITICAL RULES:
    1. ZERO network downloads during runtime. local_files_only=True is enforced.
    2. Models must be installed locally in models/tts/<model_dir> or configured
       via environment variables.
    3. If the model is not physically present, is_available() returns False.
    """

    MODEL_CONFIGS = {
        "hindi": {
            "default_subpath": os.path.join("models", "tts", "mms-tts-hin"),
            "env_var": "BHASHA_SETU_HINDI_TTS_MODEL_PATH",
            "model_identifier": "facebook/mms-tts-hin",
            "scale": "36.3M parameters (~145 MB)",
            "license": "CC-BY-NC 4.0"
        },
        "mundari": {
            "default_subpath": os.path.join("models", "tts", "mms-tts-unr"),
            "env_var": "BHASHA_SETU_MUNDARI_TTS_MODEL_PATH",
            "model_identifier": "facebook/mms-tts-unr",
            "scale": "36.3M parameters (~145 MB)",
            "license": "CC-BY-NC 4.0"
        }
    }

    def __init__(self, project_root: str):
        self.project_root = project_root
        self._loaded_models: Dict[str, Any] = {}
        self._loaded_tokenizers: Dict[str, Any] = {}

    @property
    def provider_id(self) -> str:
        return "vits_neural_tts"

    def get_model_path(self, language: str) -> Optional[str]:
        cfg = self.MODEL_CONFIGS.get(language)
        if not cfg:
            return None

        # 1. Environment variable override
        env_path = os.environ.get(cfg["env_var"])
        if env_path and os.path.exists(env_path):
            return env_path

        # 2. Local project models directory
        local_path = os.path.join(self.project_root, cfg["default_subpath"])
        if os.path.exists(local_path):
            return local_path

        return None

    def is_available(self, language: str) -> bool:
        norm_lang = "hindi" if language.lower() in ("hi", "hindi") else ("mundari" if language.lower() in ("unr", "mundari") else "")
        if not norm_lang:
            return False

        path = self.get_model_path(norm_lang)
        if not path or not os.path.isdir(path):
            return False

        # Verify essential VITS model files exist locally
        has_config = os.path.exists(os.path.join(path, "config.json"))
        has_weights = (
            os.path.exists(os.path.join(path, "pytorch_model.bin")) or
            os.path.exists(os.path.join(path, "model.safetensors"))
        )
        return has_config and has_weights

    def _ensure_loaded(self, language: str) -> Tuple[Any, Any]:
        """Lazy load VITS model and tokenizer strictly from local files."""
        if language in self._loaded_models:
            return self._loaded_models[language], self._loaded_tokenizers[language]

        path = self.get_model_path(language)
        if not path:
            raise FileNotFoundError(f"Local model path for {language} not found.")

        # Ensure transformers and torch are available
        try:
            import torch
            from transformers import AutoTokenizer, VitsModel
        except ImportError as e:
            raise ImportError(f"Transformers or PyTorch missing for VITS synthesis: {e}")

        # Strictly local loading: local_files_only=True
        tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
        model = VitsModel.from_pretrained(path, local_files_only=True)
        model.eval()

        self._loaded_models[language] = model
        self._loaded_tokenizers[language] = tokenizer
        return model, tokenizer

    @staticmethod
    def _devanagari_to_odia(text: str) -> str:
        """
        Transliterates Devanagari Mundari into Odia script.
        Meta MMS-TTS for Mundari ('facebook/mms-tts-unr') was trained on the
        Mundari corpus in Odia script. Its vocabulary (vocab.json) exclusively
        contains Odia Unicode codepoints (U+0B00–U+0B7F).
        """
        clean = text.replace("।", " ").replace("?", " ").replace("!", " ")
        clean = clean.replace(":", "ः").replace(";", " ")
        clean = clean.replace("\u095c", "\u0921\u093c").replace("\u095d", "\u0922\u093c")
        out = []
        for ch in clean:
            code = ord(ch)
            if 0x0900 <= code <= 0x097F:
                out.append(chr(code + 0x0200))
            else:
                out.append(ch)
        return "".join(out)

    def generate(self, text: str, language: str) -> Optional[PronunciationResult]:
        norm_lang = "hindi" if language.lower() in ("hi", "hindi") else ("mundari" if language.lower() in ("unr", "mundari") else "")
        if not norm_lang or not self.is_available(norm_lang):
            return None

        try:
            import numpy as np
            import torch

            model, tokenizer = self._ensure_loaded(norm_lang)

            model_input_text = text
            if norm_lang == "mundari":
                model_input_text = self._devanagari_to_odia(text)

            inputs = tokenizer(model_input_text, return_tensors="pt")

            with torch.no_grad():
                output = model(**inputs).waveform

            waveform = output.squeeze().cpu().numpy()
            sample_rate = getattr(model.config, "sampling_rate", 16000)

            # Convert to 16-bit PCM WAV in memory
            # Normalize volume
            max_val = np.max(np.abs(waveform)) + 1e-8
            waveform = (waveform / max_val) * 0.90
            pcm16 = (waveform * 32767.0).astype(np.int16)

            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(pcm16.tobytes())

            wav_bytes = buf.getvalue()
            duration_sec = round(len(waveform) / float(sample_rate), 3)

            return PronunciationResult(
                audio_bytes=wav_bytes,
                language=norm_lang,
                source_type="neural_tts",
                engine_name=self.MODEL_CONFIGS[norm_lang]["model_identifier"],
                verification_status="SYNTHETIC_GENERATED_TTS",
                sample_rate=sample_rate,
                is_cached=False,
                duration_sec=duration_sec
            )
        except Exception as e:
            print(f"[VitsTTSProvider] Synthesis error for {norm_lang}: {e}", file=sys.stderr)
            return None

    def get_status(self) -> Dict[str, Any]:
        status: Dict[str, Any] = {"provider_id": self.provider_id, "models": {}}
        for lang, cfg in self.MODEL_CONFIGS.items():
            avail = self.is_available(lang)
            path = self.get_model_path(lang)
            status["models"][lang] = {
                "available": avail,
                "model_identifier": cfg["model_identifier"],
                "scale": cfg["scale"],
                "license": cfg["license"],
                "resolved_path": path,
                "installed": avail
            }
        return status


class PronunciationService:
    """
    Canonical coordination service for Bhasha Setu pronunciation and speech audio.
    Provides validation, deterministic safe caching, audio normalization, and
    multi-provider delegation.
    """

    MAX_TEXT_LENGTH = 250

    def __init__(
        self,
        project_root: Optional[str] = None,
        cache_dir: Optional[str] = None,
        enable_cache: bool = True,
        providers: Optional[List[BasePronunciationProvider]] = None,
        teacher_voice_manager: Optional[Any] = None,
    ):
        if project_root is None:
            # Default to repo root (two levels up from ai/speech)
            cur = os.path.dirname(os.path.abspath(__file__))
            self.project_root = os.path.normpath(os.path.join(cur, "..", ".."))
        else:
            self.project_root = project_root

        self.enable_cache = enable_cache
        self.cache_dir = cache_dir or os.environ.get(
            "BHASHA_SETU_SPEECH_CACHE_DIR",
            os.path.join(self.project_root, "cache", "speech")
        )

        if self.enable_cache:
            os.makedirs(self.cache_dir, exist_ok=True)

        if providers is not None:
            self.providers = providers
        else:
            self.providers = [
                PrototypeAudioRegistryProvider(self.project_root),
                VitsTTSProvider(self.project_root),
            ]

        # Locate registry provider for controlled audio checks
        self.registry_provider: Optional[PrototypeAudioRegistryProvider] = None
        for p in self.providers:
            if isinstance(p, PrototypeAudioRegistryProvider):
                self.registry_provider = p
                break

        # Teacher Voice Profile Manager
        if teacher_voice_manager is not None:
            self.teacher_voice_manager = teacher_voice_manager
        else:
            try:
                from ai.speech.teacher_voice_service import TeacherVoiceProfileManager
                self.teacher_voice_manager = TeacherVoiceProfileManager(self.project_root)
            except Exception as e:
                print(f"[PronunciationService] Warning initializing TeacherVoiceProfileManager: {e}", file=sys.stderr)
                self.teacher_voice_manager = None

    def normalize_language(self, language: Optional[str]) -> Optional[str]:
        if not language or not isinstance(language, str):
            return None
        norm = language.strip().lower()
        if norm in ("hindi", "hi"):
            return "hindi"
        if norm in ("mundari", "unr"):
            return "mundari"
        return None

    def validate_request(self, text: Any, language: Any) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        Validates text and language parameters.
        Returns: (is_valid, normalized_text, normalized_lang, error_message)
        """
        if not isinstance(text, str) or not text.strip():
            return False, None, None, "Text must be a non-empty string."

        clean_text = text.strip()
        if len(clean_text) > self.MAX_TEXT_LENGTH:
            return False, None, None, f"Text exceeds maximum allowable length of {self.MAX_TEXT_LENGTH} characters."

        norm_lang = self.normalize_language(language)
        if not norm_lang:
            return False, None, None, f"Unsupported language '{language}'. Supported languages: 'hindi', 'mundari'."

        return True, clean_text, norm_lang, None

    def _compute_cache_key(self, text: str, language: str, engine_id: str) -> str:
        """
        Computes a deterministic, collision-resistant hash key.
        Strictly alphanumeric (hex) to eliminate any directory traversal risk.
        """
        raw = f"{language}:{text.strip()}:{engine_id}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _get_cache_file_path(self, cache_key: str, prefix: str = "") -> str:
        # Strictly alphanumeric safe prefix and 64-char hex string
        safe_prefix = re.sub(r"[^0-9a-zA-Z_]", "", prefix)
        safe_key = re.sub(r"[^0-9a-fA-F]", "", cache_key)
        return os.path.join(self.cache_dir, f"{safe_prefix}{safe_key}.wav")

    def _normalize_wav_audio(self, audio_bytes: bytes, target_sr: int = 16000) -> bytes:
        """
        Validates and standardizes the WAV audio bytes to 1-channel mono 16-bit PCM.
        """
        try:
            with io.BytesIO(audio_bytes) as in_buf:
                with wave.open(in_buf, "rb") as wf:
                    nchannels = wf.getnchannels()
                    sampwidth = wf.getsampwidth()
                    framerate = wf.getframerate()
                    nframes = wf.getnframes()
                    frames = wf.readframes(nframes)

            # If already 1-channel, 16-bit PCM (sampwidth=2), and target_sr, return directly
            if nchannels == 1 and sampwidth == 2 and framerate == target_sr:
                return audio_bytes

            # If stereo (2 channels), downmix to mono
            if nchannels == 2 and sampwidth == 2:
                import numpy as np
                audio_data = np.frombuffer(frames, dtype=np.int16).reshape(-1, 2)
                mono = audio_data.mean(axis=1).astype(np.int16)
                out_buf = io.BytesIO()
                with wave.open(out_buf, "wb") as out_wf:
                    out_wf.setnchannels(1)
                    out_wf.setsampwidth(2)
                    out_wf.setframerate(framerate)
                    out_wf.writeframes(mono.tobytes())
                return out_buf.getvalue()

            return audio_bytes
        except Exception:
            # Fallback to returning raw bytes if parser cannot decode
            return audio_bytes

    def synthesize(
        self, text: Any, language: Any, use_teacher_voice: bool = False
    ) -> Tuple[Optional[PronunciationResult], Optional[Dict[str, Any]]]:
        """
        Core synthesis dispatcher supporting standard synthesis and Teacher Voice Profile.

        ROUTING RULES:
        1. Hindi + Teacher Voice:
           Base MMS-TTS -> OpenVoice v2 conversion -> Teacher Hindi audio.
           Validation status: TEACHER_ADAPTED_SYNTHETIC.
        2. Mundari Controlled + Teacher Voice:
           Registry audio -> OpenVoice v2 conversion -> Teacher Mundari audio.
           Validation status: PROTOTYPE_ONLY_PENDING_HUMAN_VALIDATION (NEVER upgraded).
        3. Mundari Arbitrary + Teacher Voice:
           Voice conversion is BLOCKED. Synthesized via raw MMS-TTS ONLY.
           Validation status: SYNTHETIC_GENERATED_TTS.
        4. Standard Base Audio (use_teacher_voice=False or profile inactive):
           Dispatched directly to providers (Registry or MMS-TTS).

        Returns:
            (PronunciationResult, None) on success
            (None, error_dict) on validation failure or unavailable provider
        """
        is_valid, clean_text, norm_lang, err_msg = self.validate_request(text, language)
        if not is_valid:
            return None, {
                "status": "INVALID_INPUT",
                "message": err_msg,
                "http_code": 400
            }

        # Check if Teacher Voice conversion can be applied
        apply_teacher_voice = False
        if use_teacher_voice and self.teacher_voice_manager and self.teacher_voice_manager.is_active():
            if norm_lang == "hindi":
                apply_teacher_voice = True
            elif norm_lang == "mundari":
                # STRICT GOVERNANCE: Only controlled phrases from the registry can undergo voice conversion
                if self.registry_provider and self.registry_provider.has_entry(clean_text, "mundari"):
                    apply_teacher_voice = True
                else:
                    # Arbitrary Mundari text is blocked from voice conversion to avoid masking phonology
                    apply_teacher_voice = False

        # PATH A: Teacher Voice Profile Conversion
        if apply_teacher_voice:
            profile_id = self.teacher_voice_manager.get_profile_id() or "teacher_v1"
            teacher_engine_id = f"teacher_{profile_id}"
            teacher_cache_key = self._compute_cache_key(clean_text, norm_lang, teacher_engine_id)
            teacher_cache_path = self._get_cache_file_path(teacher_cache_key, prefix="teacher_")
            teacher_meta_path = teacher_cache_path.replace(".wav", ".json")

            # Check teacher voice cache
            if self.enable_cache and os.path.exists(teacher_cache_path):
                try:
                    with open(teacher_cache_path, "rb") as f:
                        cached_bytes = f.read()

                    engine_name = f"cached_{teacher_engine_id}"
                    source_type = "teacher_voice"
                    verification_status = (
                        "PROTOTYPE_ONLY_PENDING_HUMAN_VALIDATION"
                        if norm_lang == "mundari"
                        else "TEACHER_ADAPTED_SYNTHETIC"
                    )
                    duration_sec = 0.0
                    sample_rate = 22050

                    if os.path.exists(teacher_meta_path):
                        try:
                            with open(teacher_meta_path, "r", encoding="utf-8") as mf:
                                meta = json.load(mf)
                                engine_name = meta.get("engine_name", engine_name)
                                source_type = meta.get("source_type", source_type)
                                verification_status = meta.get("verification_status", verification_status)
                                duration_sec = meta.get("duration_sec", 0.0)
                                sample_rate = meta.get("sample_rate", 22050)
                        except Exception:
                            pass

                    return PronunciationResult(
                        audio_bytes=cached_bytes,
                        language=norm_lang,
                        source_type=source_type,
                        engine_name=engine_name,
                        verification_status=verification_status,
                        sample_rate=sample_rate,
                        is_cached=True,
                        duration_sec=duration_sec,
                        teacher_voice_applied=True
                    ), None
                except Exception as e:
                    print(f"[PronunciationService] Error reading teacher cache: {e}", file=sys.stderr)

            # Generate base audio for voice conversion
            base_result: Optional[PronunciationResult] = None
            if norm_lang == "mundari":
                if self.registry_provider:
                    base_result = self.registry_provider.generate(clean_text, "mundari")
            else:
                for provider in self.providers:
                    if provider.is_available("hindi"):
                        base_result = provider.generate(clean_text, "hindi")
                        if base_result and base_result.audio_bytes:
                            break

            if base_result and base_result.audio_bytes:
                try:
                    target_se = self.teacher_voice_manager.get_embedding()
                    conv_res = self.teacher_voice_manager.converter.convert_audio(
                        base_result.audio_bytes,
                        target_se=target_se
                    )
                    if isinstance(conv_res, tuple):
                        converted_wav, dur = conv_res
                    else:
                        converted_wav = conv_res
                        dur = base_result.duration_sec

                    # Extract duration and sample rate from converted WAV
                    sr = 22050
                    try:
                        with io.BytesIO(converted_wav) as buf:
                            with wave.open(buf, "rb") as wf:
                                sr = wf.getframerate()
                                dur = round(wf.getnframes() / float(sr), 3)
                    except Exception:
                        pass

                    # Status governance
                    if norm_lang == "mundari":
                        val_status = "PROTOTYPE_ONLY_PENDING_HUMAN_VALIDATION"
                        src_type = "teacher_voice_controlled"
                        eng_name = f"{base_result.engine_name}+openvoice_v2"
                    else:
                        val_status = "TEACHER_ADAPTED_SYNTHETIC"
                        src_type = "teacher_voice_synthetic"
                        eng_name = f"{base_result.engine_name}+openvoice_v2"

                    result = PronunciationResult(
                        audio_bytes=converted_wav,
                        language=norm_lang,
                        source_type=src_type,
                        engine_name=eng_name,
                        verification_status=val_status,
                        sample_rate=sr,
                        is_cached=False,
                        duration_sec=dur,
                        teacher_voice_applied=True
                    )

                    # Write to teacher cache
                    if self.enable_cache:
                        try:
                            with open(teacher_cache_path, "wb") as cf:
                                cf.write(converted_wav)
                            meta_data = {
                                "engine_name": result.engine_name,
                                "source_type": result.source_type,
                                "verification_status": result.verification_status,
                                "sample_rate": result.sample_rate,
                                "duration_sec": result.duration_sec,
                                "teacher_voice_applied": True
                            }
                            with open(teacher_meta_path, "w", encoding="utf-8") as mf:
                                json.dump(meta_data, mf)
                        except Exception as e:
                            print(f"[PronunciationService] Error writing teacher cache: {e}", file=sys.stderr)

                    return result, None

                except Exception as e:
                    print(f"[PronunciationService] Teacher voice conversion failed: {e}. Falling back to base audio.", file=sys.stderr)

        # PATH B: Standard Synthesis Dispatcher (Base Audio)
        # 1. Check disk cache first (using service-wide hash)
        global_cache_key = self._compute_cache_key(clean_text, norm_lang, "default_v1")
        cache_path = self._get_cache_file_path(global_cache_key)
        meta_path = cache_path.replace(".wav", ".json")

        if self.enable_cache and os.path.exists(cache_path):
            try:
                with open(cache_path, "rb") as f:
                    cached_bytes = f.read()

                engine_name = "disk_cache"
                source_type = "cached"
                verification_status = "PROTOTYPE_ONLY_PENDING_HUMAN_VALIDATION"
                duration_sec = 0.0

                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, "r", encoding="utf-8") as mf:
                            meta = json.load(mf)
                            engine_name = meta.get("engine_name", engine_name)
                            source_type = meta.get("source_type", source_type)
                            verification_status = meta.get("verification_status", verification_status)
                            duration_sec = meta.get("duration_sec", 0.0)
                    except Exception:
                        pass

                return PronunciationResult(
                    audio_bytes=cached_bytes,
                    language=norm_lang,
                    source_type=source_type,
                    engine_name=engine_name,
                    verification_status=verification_status,
                    sample_rate=16000,
                    is_cached=True,
                    duration_sec=duration_sec,
                    teacher_voice_applied=False
                ), None
            except Exception as e:
                print(f"[PronunciationService] Error reading cache file {cache_path}: {e}", file=sys.stderr)

        # 2. Iterate through providers in order of preference
        for provider in self.providers:
            if not provider.is_available(norm_lang):
                continue

            result = provider.generate(clean_text, norm_lang)
            if result and result.audio_bytes:
                # Normalize audio
                normalized_wav = self._normalize_wav_audio(result.audio_bytes, target_sr=16000)
                result.audio_bytes = normalized_wav
                result.teacher_voice_applied = False

                # Write to disk cache
                if self.enable_cache:
                    try:
                        with open(cache_path, "wb") as cf:
                            cf.write(normalized_wav)
                        meta_data = {
                            "engine_name": result.engine_name,
                            "source_type": result.source_type,
                            "verification_status": result.verification_status,
                            "sample_rate": result.sample_rate,
                            "duration_sec": result.duration_sec,
                            "teacher_voice_applied": False
                        }
                        with open(meta_path, "w", encoding="utf-8") as mf:
                            json.dump(meta_data, mf)
                    except Exception as e:
                        print(f"[PronunciationService] Error writing cache file {cache_path}: {e}", file=sys.stderr)

                return result, None

        # 3. Provider unavailable: formulate a truthful, transparent response
        if norm_lang == "hindi":
            details = "Hindi neural TTS model is not installed. To install 'facebook/mms-tts-hin' (VITS 36.3M, ~145 MB), run 'python scripts/download_tts_models.py --lang hindi' or set BHASHA_SETU_HINDI_TTS_MODEL_PATH."
        else:
            details = "Mundari pronunciation is available for registered Grade 1 FLN numerals and classroom phrases. For un-registered phrases, install 'facebook/mms-tts-unr' (~145 MB) via 'python scripts/download_tts_models.py --lang mundari' or set BHASHA_SETU_MUNDARI_TTS_MODEL_PATH."

        return None, {
            "status": "UNAVAILABLE",
            "message": f"Pronunciation audio is currently unavailable for {norm_lang} text: '{clean_text}'.",
            "language": norm_lang,
            "details": details,
            "http_code": 503
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Returns truthful runtime status across all providers and languages."""
        hi_avail = any(p.is_available("hindi") for p in self.providers)
        unr_avail = any(p.is_available("mundari") for p in self.providers)

        cache_count = 0
        if self.enable_cache and os.path.exists(self.cache_dir):
            try:
                cache_count = len([f for f in os.listdir(self.cache_dir) if f.endswith(".wav")])
            except Exception:
                pass

        provider_statuses = [p.get_status() for p in self.providers]

        health: Dict[str, Any] = {
            "status": "HEALTHY",
            "hindi": "available" if hi_avail else "unavailable",
            "mundari": "available" if unr_avail else "unavailable",
            "cache": "enabled" if self.enable_cache else "disabled",
            "cache_entries": cache_count,
            "providers": provider_statuses,
            "disclaimer": "CRITICAL: Prototype audio assets are strictly for prototype demonstration and educational playback. They are NEVER claimed as native-speaker verified."
        }

        if self.teacher_voice_manager:
            health["teacher_voice"] = self.teacher_voice_manager.get_status()
        else:
            health["teacher_voice"] = {
                "status": "UNAVAILABLE",
                "enrolled": False,
                "enabled": False,
                "profile_id": None,
                "model_available": False,
                "ui_state_label": "Teacher voice unavailable"
            }

        return health
