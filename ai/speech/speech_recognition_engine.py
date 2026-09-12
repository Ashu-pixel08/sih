"""
ai/speech/speech_recognition_engine.py
=============================================================================
SIH260042: AI-Powered Vernacular Pedagogy & Real-Time Translation
Modular Speech Recognition Subsystem & Extensible Engine Interface
=============================================================================

ARCHITECTURAL PRINCIPLE:
- The 1–20 speech classifier is an edge-optimized vocabulary recognition module
  serving as our controlled FLN presentation MVP.
- It is NOT the whole speech system.
- This module provides an extensible architecture where vocabulary recognizers
  (numbers, classroom instructions, FLN terms) and future continuous ASR models
  coexist under a unified interface:
    Audio PCM -> Preprocessor -> SpeechRecognitionManager -> Unified Result
=============================================================================
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import os
import sys
from typing import Any, Dict, List, Optional, Union

import numpy as np

cur_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.normpath(os.path.join(cur_dir, "..", ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from ai.preprocessing.audio_preprocessor import AudioPreprocessor
from ai.preprocessing.vad_stream_processor import StreamingVADProcessor, VADConfig
from ai.speech.speech_classifier import LightweightSpectrogramCNN


# =============================================================================
# EXPLICIT SYSTEM CAPABILITY SEPARATION
# =============================================================================
CAPABILITY_GENERAL_SPEECH_RECOGNITION = "GENERAL_SPEECH_RECOGNITION (Requires ~50-100h corpus; NOT implemented on edge)"
CAPABILITY_CONTROLLED_VOCABULARY = "CONTROLLED_VOCABULARY_SPEECH_RECOGNITION (21-class edge classifier for 1-20 numerals)"
CAPABILITY_TEXT_TRANSLATION = "TEXT_TRANSLATION (Deterministic retrieval engine: Tier 1 exact + Tier 2 TF-IDF + Tier 3 fallback)"


@dataclass
class SpeechRecognitionResult:
    """Standardized output from any speech recognition engine backend."""
    recognized_text: Optional[str]
    hindi_equivalent: Optional[str]
    class_index: Optional[int]
    label_id: str
    confidence: float
    margin: float
    is_confident: bool
    engine_name: str
    engine_type: str  # "EDGE_VOCABULARY_CNN", "GENERAL_ASR_EXTENSIBLE", "FALLBACK"
    status: str       # "RECOGNIZED", "LOW_CONFIDENCE_REJECTED", "BACKGROUND_NOISE", "FUTURE_ASR"
    metadata: Dict[str, Any]
    # Phase 9 Diagnostic metrics
    rms_energy: float = 0.0
    second_best_confidence: float = 0.0
    second_best_class_index: Optional[int] = None
    decision: str = "REJECTED"
    rejection_reason: Optional[str] = None
    audio_duration_sec: float = 1.0


class BaseSpeechRecognizer(ABC):
    """Abstract interface for all speech recognition components."""

    @abstractmethod
    def recognize_spectrogram(self, spectrogram: np.ndarray) -> SpeechRecognitionResult:
        """Processes normalized Log-Mel spectrogram [101, 64] or [1, 101, 64, 1]."""
        pass

    @abstractmethod
    def get_supported_vocabulary(self) -> List[str]:
        """Returns list of words/classes supported by this engine."""
        pass


class VocabularySpeechRecognizer(BaseSpeechRecognizer):
    """
    Edge-deployable vocabulary recognizer using the LightweightSpectrogramCNN
    (or its quantized TFLite edge export).
    Specializes in the controlled FLN Grade 1 Numbers 1–20 vocabulary.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        use_tflite: bool = True,
        confidence_threshold: float = 0.65,
        margin_threshold: float = 0.20,
        registry_path: Optional[str] = None,
    ):
        self.use_tflite = use_tflite
        self.confidence_threshold = confidence_threshold
        self.margin_threshold = margin_threshold

        self.registry_path = registry_path or os.path.join(
            workspace_root, "content", "content_registry.json"
        )
        self.registry_data = self._load_registry()

        # Resolve model path
        if model_path is None:
            if use_tflite:
                model_path = os.path.join(
                    workspace_root, "models", "edge", "speech_classifier_float32.tflite"
                )
            else:
                model_path = os.path.join(
                    workspace_root, "models", "checkpoints", "best_model.pt"
                )
        self.model_path = model_path

        # Initialize backend
        self._tflite_interp = None
        self._torch_model = None

        if use_tflite and os.path.exists(model_path):
            try:
                import ai_edge_litert.interpreter as tflite
                self._tflite_interp = tflite.Interpreter(model_path=model_path)
                self._tflite_interp.allocate_tensors()
                self._in_idx = self._tflite_interp.get_input_details()[0]["index"]
                self._out_idx = self._tflite_interp.get_output_details()[0]["index"]
                self.backend_type = "LITERT_TFLITE"
            except Exception as e:
                print(f"Notice: Falling back to PyTorch model (LiteRT init error: {e})")
                self._init_torch_backend()
        else:
            self._init_torch_backend()

    def _init_torch_backend(self):
        import torch
        self._torch_model = LightweightSpectrogramCNN(num_classes=21)
        if os.path.exists(self.model_path) and self.model_path.endswith(".pt"):
            ckpt = torch.load(self.model_path, weights_only=False, map_location="cpu")
            state = ckpt["model_state_dict"] if "model_state_dict" in ckpt else ckpt
            self._torch_model.load_state_dict(state)
        self._torch_model.eval()
        self.backend_type = "PYTORCH_EVAL"

    def _load_registry(self) -> Dict[str, Any]:
        if os.path.exists(self.registry_path):
            with open(self.registry_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"items": [], "background_class": {"label_id": "_background_"}}

    def get_supported_vocabulary(self) -> List[str]:
        vocab = ["_background_"]
        for item in self.registry_data.get("items", []):
            vocab.append(item.get("mundari_text", f"num_{item['class_index']}"))
        return vocab

    def recognize_spectrogram(self, spectrogram: np.ndarray) -> SpeechRecognitionResult:
        """
        Infers class and maps to verified educational numeral representation.
        """
        # Ensure 4D shape [1, 101, 64, 1]
        spec = np.asarray(spectrogram, dtype=np.float32)
        if spec.ndim == 2:  # [101, 64]
            spec = spec[np.newaxis, :, :, np.newaxis]
        elif spec.ndim == 3 and spec.shape[-1] != 1:  # [1, 101, 64]
            spec = spec.transpose(0, 1, 2)[:, :, :, np.newaxis]

        if self._tflite_interp is not None:
            self._tflite_interp.set_tensor(self._in_idx, spec)
            self._tflite_interp.invoke()
            probs = self._tflite_interp.get_tensor(self._out_idx).squeeze(0)
        else:
            res = self._torch_model.predict(
                spec,
                confidence_threshold=self.confidence_threshold,
                margin_threshold=self.margin_threshold,
            )
            probs = np.array(res["probabilities"], dtype=np.float32)

        sorted_idx = np.argsort(probs)[::-1]
        top_idx = int(sorted_idx[0])
        top_conf = float(probs[top_idx])
        second_conf = float(probs[sorted_idx[1]]) if len(sorted_idx) > 1 else 0.0
        margin = float(top_conf - second_conf)

        is_confident = (
            top_conf >= self.confidence_threshold
            and margin >= self.margin_threshold
            and top_idx != 0
        )

        # Map to canonical registry data
        second_idx = int(sorted_idx[1]) if len(sorted_idx) > 1 else None
        if top_idx == 0:
            status = "BACKGROUND_NOISE"
            rec_text = None
            hi_text = None
            label_id = "_background_"
            decision = "REJECTED_BACKGROUND"
            rejection_reason = "Ambient noise or silence classified as background"
        elif is_confident:
            status = "RECOGNIZED"
            item = next((it for it in self.registry_data.get("items", []) if it["class_index"] == top_idx), None)
            rec_text = item["mundari_text"] if item else f"num_{top_idx}"
            hi_text = item["hindi_text"] if item else None
            label_id = item["label_id"] if item else f"num_{top_idx:02d}"
            decision = "ACCEPTED"
            rejection_reason = None
        else:
            status = "LOW_CONFIDENCE_REJECTED"
            rec_text = None
            hi_text = None
            label_id = f"num_{top_idx:02d}"
            decision = "REJECTED_LOW_CONFIDENCE"
            rejection_reason = f"Confidence ({top_conf:.2f}) or margin ({margin:.2f}) below threshold"

        return SpeechRecognitionResult(
            recognized_text=rec_text,
            hindi_equivalent=hi_text,
            class_index=top_idx,
            label_id=label_id,
            confidence=round(top_conf, 4),
            margin=round(margin, 4),
            is_confident=is_confident,
            engine_name="LightweightSpectrogramCNN",
            engine_type="EDGE_VOCABULARY_CNN",
            status=status,
            metadata={
                "backend": self.backend_type,
                "confidence_threshold": self.confidence_threshold,
                "margin_threshold": self.margin_threshold,
                "status_policy": "RESEARCH / PIPELINE VALIDATION ONLY",
            },
            second_best_confidence=round(second_conf, 4),
            second_best_class_index=second_idx,
            decision=decision,
            rejection_reason=rejection_reason,
            audio_duration_sec=1.0,
        )


class GeneralASRInterface(BaseSpeechRecognizer):
    """
    Extensible interface stub for future broader Mundari ASR models
    (e.g., fine-tuned CTC acoustic model or sequence-to-sequence model).
    Currently documents real-data prerequisites before activation.
    """

    def __init__(self, asr_model_path: Optional[str] = None):
        self.asr_model_path = asr_model_path
        self.is_active = asr_model_path is not None and os.path.exists(asr_model_path)

    def get_supported_vocabulary(self) -> List[str]:
        return ["GENERAL_MUNDARI_VOCABULARY (REQUIRES_EXPANDED_CORPUS)"]

    def recognize_spectrogram(self, spectrogram: np.ndarray) -> SpeechRecognitionResult:
        """Plug-in execution stub for future general ASR model."""
        return SpeechRecognitionResult(
            recognized_text=None,
            hindi_equivalent=None,
            class_index=None,
            label_id="general_asr_unsupported",
            confidence=0.0,
            margin=0.0,
            is_confident=False,
            engine_name="GeneralMundariASR_Interface",
            engine_type="GENERAL_ASR_EXTENSIBLE",
            status="FUTURE_ASR_PENDING_TRAINING_DATA",
            metadata={
                "policy": "General Mundari ASR requires expanded acoustic corpus (~50-100 hours).",
                "prerequisite": "Full 26.8k Karya corpus authorization and transcription alignment.",
            },
        )


class SpeechRecognitionManager:
    """
    Orchestrates speech recognition across specialized edge vocabulary models
    and extensible general ASR engines. Provides automatic audio preprocessing,
    streaming Voice Activity Detection (VAD), and triggers the fail-safe
    presentation path when audio is ambiguous.
    """

    def __init__(
        self,
        vocabulary_recognizer: Optional[VocabularySpeechRecognizer] = None,
        general_asr: Optional[GeneralASRInterface] = None,
        vad_processor: Optional[StreamingVADProcessor] = None,
    ):
        self.preprocessor = AudioPreprocessor()
        self.vocabulary_recognizer = vocabulary_recognizer or VocabularySpeechRecognizer()
        self.general_asr = general_asr or GeneralASRInterface()
        self.vad_processor = vad_processor or StreamingVADProcessor()

    def reset_stream(self) -> None:
        """Resets the streaming VAD buffer and state machine."""
        self.vad_processor.reset()

    def process_streaming_chunk(
        self, chunk: np.ndarray, sample_rate: int = 16000
    ) -> Optional[SpeechRecognitionResult]:
        """
        Accepts a single streaming PCM chunk (typically 20-50 ms).
        Returns a SpeechRecognitionResult if an utterance endpoint is detected,
        or None while continuing to listen.
        """
        extracted_utterance = self.vad_processor.process_chunk(chunk)
        if extracted_utterance is not None:
            return self.process_raw_audio(extracted_utterance, sample_rate=sample_rate)
        return None

    def process_continuous_stream(
        self, audio: np.ndarray, sample_rate: int = 16000
    ) -> List[SpeechRecognitionResult]:
        """
        Processes a continuous audio stream through the VAD endpointing pipeline,
        returning speech recognition results for all captured utterances.
        """
        utterances = self.vad_processor.process_continuous_audio(audio)
        results = []
        for utt in utterances:
            res = self.process_raw_audio(utt, sample_rate=sample_rate)
            results.append(res)
        return results

    def process_raw_audio(self, pcm_data: Union[bytes, np.ndarray], sample_rate: int = 16000) -> SpeechRecognitionResult:
        """
        End-to-end speech recognition from raw audio samples or PCM bytes.
        """
        # Step 1: Preprocessing & Log-Mel Spectrogram computation
        if isinstance(pcm_data, bytes):
            audio = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0
        else:
            audio = np.asarray(pcm_data, dtype=np.float32)

        rms_val = float(np.sqrt(np.mean(audio ** 2))) if len(audio) > 0 else 0.0
        dur_sec = float(len(audio) / sample_rate) if sample_rate > 0 else 1.0

        _, log_mel = self.preprocessor.preprocess_signal(audio, sample_rate)
        spec_4d = self.preprocessor.format_for_model(log_mel)  # [1, 101, 64, 1]

        # Step 2: Route to Vocabulary Recognizer (Numbers 1-20 FLN MVP)
        result = self.vocabulary_recognizer.recognize_spectrogram(spec_4d)
        result.rms_energy = round(rms_val, 4)
        result.audio_duration_sec = round(dur_sec, 3)

        # Step 3: If not recognized or low confidence, check general ASR if active
        if not result.is_confident and self.general_asr.is_active:
            general_res = self.general_asr.recognize_spectrogram(spec_4d)
            general_res.rms_energy = round(rms_val, 4)
            general_res.audio_duration_sec = round(dur_sec, 3)
            if general_res.is_confident:
                return general_res

        return result

