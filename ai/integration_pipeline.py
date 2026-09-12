"""
ai/integration_pipeline.py
=============================================================================
SIH260042: AI-Powered Vernacular Pedagogy & Real-Time Translation
Unified End-to-End System Integration Pipeline
=============================================================================

ARCHITECTURE FLOW:
  [Microphone / Spoken Audio]
              │
              ▼
   [Audio Preprocessor] (16 kHz, Log-Mel [1, 101, 64, 1])
              │
              ▼
  [Speech Recognition Engine] (Modular: Vocabulary CNN / General ASR Stub)
              │
              ├── Confidence < 0.65 ──> [Interactive Touch & Card Fallback Mode]
              ▼
  [Translation Engine] (Tier 1 Verified Retrieval + Tier 2 Corpus Similarity)
              │
              ▼
  [FLN Content Engine] (Grade 1 Lessons, Flashcards, Worksheets, Activities)
              │
              ▼
  [Verified Pedagogical Output] (Bilingual Text, SVG Visuals, Authentic WAV, HTML)
=============================================================================
"""

import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

cur_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.normpath(os.path.join(cur_dir, ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from ai.preprocessing.audio_preprocessor import AudioPreprocessor
from ai.speech.hindi_asr_engine import HindiASRRecognizer, HindiASRResult
from ai.speech.speech_recognition_engine import (
    SpeechRecognitionManager,
    SpeechRecognitionResult,
)
from ai.translation.translation_engine import TranslationEngine, TranslationResult
from content.flashcards.flashcard_generator import FlashcardGenerator
from content.fln.fln_content_engine import FLNContentEngine
from content.worksheets.worksheet_generator import WorksheetGenerator


@dataclass
class PedagogySessionResponse:
    """Unified session output delivering pedagogical content across modalities."""
    session_id: str
    input_mode: str  # "SPOKEN_SPEECH", "TEACHER_HINDI_TEXT", "DIRECT_CARD_SELECTION", "TEACHER_HINDI_VOICE"
    input_content: Any
    is_success: bool
    status_code: str
    message: str

    # Speech Recognition Stage (if applicable)
    speech_result: Optional[Dict[str, Any]]

    # Translation Stage
    translation_status: str
    hindi_text: Optional[str]
    mundari_text: Optional[str]
    mundari_phonetic: Optional[str]
    confidence: float

    # Pedagogical Content Stage
    lesson: Optional[Dict[str, Any]]
    flashcard_svg_path: Optional[str]
    audio_asset_path: Optional[str]
    audio_status: str
    worksheet_ref: Optional[Dict[str, Any]]
    recommended_activity: Optional[Dict[str, Any]]

    # Presentation Fallback Indicator
    fallback_recommended: bool

    # End-to-End IDs & Profiling
    content_id: Optional[str] = None
    audio_id: Optional[str] = None
    latency_breakdown: Optional[Dict[str, float]] = None
    hardware_profile: Optional[Dict[str, Any]] = None
    diagnostic_info: Optional[Dict[str, Any]] = None


class VernacularPedagogyPipeline:
    """
    Unified end-to-end pipeline coordinator integrating:
    Audio Preprocessor -> Constrained Hindi Speech Recognizer -> Translation Engine -> FLN Content Engine -> Audio Resolution.
    """

    def __init__(
        self,
        registry_path: Optional[str] = None,
        translation_tsv: Optional[str] = None,
        audio_manifest_path: Optional[str] = None,
    ):
        self.workspace_root = workspace_root
        self.registry_path = registry_path or os.path.join(
            self.workspace_root, "content", "content_registry.json"
        )
        self.translation_tsv = translation_tsv or os.path.join(
            self.workspace_root, "data", "raw", "translation", "translation-hi-unr.tsv"
        )
        self.audio_manifest_path = audio_manifest_path or os.path.join(
            self.workspace_root, "content", "audio", "audio_manifest.json"
        )

        # Initialize subsystem modules
        self.speech_manager = SpeechRecognitionManager()
        self.hindi_asr = HindiASRRecognizer()
        self.translation_engine = TranslationEngine(
            registry_path=self.registry_path,
            corpus_tsv_path=self.translation_tsv,
        )
        self.fln_engine = FLNContentEngine(registry_path=self.registry_path)
        self.flashcard_gen = FlashcardGenerator(registry_path=self.registry_path)
        self.worksheet_gen = WorksheetGenerator(registry_path=self.registry_path)

        with open(self.registry_path, "r", encoding="utf-8") as f:
            self.registry_data = json.load(f)

        # Index available audio assets from manifest
        self.audio_asset_index: Dict[str, Dict[str, Any]] = {}
        if os.path.exists(self.audio_manifest_path):
            with open(self.audio_manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
                for asset in manifest_data.get("assets", []):
                    cid = asset.get("content_id")
                    if cid:
                        self.audio_asset_index[cid] = asset
                    ht = asset.get("hindi_text")
                    if ht:
                        self.audio_asset_index[ht] = asset
                    idx = asset.get("class_index")
                    if idx is not None:
                        self.audio_asset_index[str(idx)] = asset

    def _resolve_audio_asset(
        self,
        content_id: Optional[str],
        hindi_text: Optional[str] = None,
        number: Optional[int] = None,
    ) -> Tuple[Optional[str], Optional[str], str]:
        """
        Resolves audio asset path, audio ID, and audio verification status.
        Follows strict verification policy:
        - If synthetic prototype WAV physically exists on disk: status is "SYNTHETIC_PROTOTYPE".
        - If missing or unverified: status is "MISSING" and path is None.
        Returns: (audio_asset_path, audio_id, audio_status)
        """
        candidate = None
        if content_id and content_id in self.audio_asset_index:
            candidate = self.audio_asset_index[content_id]
        elif number is not None and str(number) in self.audio_asset_index:
            candidate = self.audio_asset_index[str(number)]
        elif hindi_text and hindi_text in self.audio_asset_index:
            candidate = self.audio_asset_index[hindi_text]
        elif hindi_text == "पांच" and "पाँच" in self.audio_asset_index:
            candidate = self.audio_asset_index["पाँच"]
        elif hindi_text in ("छः", "छ:") and "छह" in self.audio_asset_index:
            candidate = self.audio_asset_index["छह"]

        if candidate:
            rel_path = candidate.get("audio_file", "")
            abs_path = os.path.normpath(os.path.join(self.workspace_root, rel_path))
            if os.path.isfile(abs_path) and os.path.getsize(abs_path) > 44:
                return (
                    abs_path,
                    candidate.get("content_id"),
                    "SYNTHETIC_PROTOTYPE",
                )

        return None, None, "MISSING"

    def _get_phrase_content_id(self, hindi_text: str) -> str:
        """Maps recognized Hindi phrase to canonical phrase ID."""
        if hindi_text in self.audio_asset_index:
            return self.audio_asset_index[hindi_text].get("content_id", "PHR_UNKNOWN")
        mapping = {
            "नमस्ते": "PHR_GREET_01",
            "सुप्रभात": "PHR_GREET_02",
            "बैठो": "PHR_MGMT_01",
            "बैठिए": "PHR_MGMT_01",
            "खड़े हो जाओ": "PHR_MGMT_02",
            "इधर देखो": "PHR_MGMT_03",
            "चुप रहो": "PHR_MGMT_04",
            "हाथ उठाओ": "PHR_MGMT_05",
            "किताब खोलो": "PHR_MGMT_06",
            "गिनो": "cmd_gino",
            "गिनिए": "cmd_gino",
            "लिखो": "cmd_likho",
            "पढ़ो": "cmd_padho",
            "सुनो": "cmd_suno",
            "बहुत अच्छा": "PHR_ENCR_01",
            "शाबाश": "PHR_ENCR_02",
        }
        return mapping.get(hindi_text.strip(), f"cmd_{hash(hindi_text) % 10000}")

    def _build_hardware_profile(self, desktop_breakdown: Dict[str, float]) -> Dict[str, Any]:
        """Provides measured desktop latency and estimated Android edge latency."""
        e2e = desktop_breakdown.get("total_end_to_end_ms", 0.0)
        prep = desktop_breakdown.get("audio_preprocessing_ms", 0.0)
        asr = desktop_breakdown.get("hindi_recognition_ms", 0.0)
        trans = desktop_breakdown.get("translation_ms", 0.0)
        fln = desktop_breakdown.get("fln_lookup_ms", 0.0)
        audio = desktop_breakdown.get("audio_lookup_ms", 0.0)

        return {
            "DESKTOP_MEASURED": {
                "audio_preprocessing_ms": round(prep, 2),
                "hindi_recognition_ms": round(asr, 2),
                "translation_ms": round(trans, 2),
                "fln_lookup_ms": round(fln, 2),
                "audio_lookup_ms": round(audio, 2),
                "total_end_to_end_ms": round(e2e, 2),
            },
            "ANDROID_ESTIMATED": {
                "audio_preprocessing_ms": round(prep * 2.5 + 5.0, 2),
                "hindi_recognition_ms": round(asr * 3.5 + 40.0, 2),
                "translation_ms": round(trans * 2.0 + 3.0, 2),
                "fln_lookup_ms": round(fln * 1.5 + 1.0, 2),
                "audio_lookup_ms": round(audio * 1.5 + 1.0, 2),
                "total_end_to_end_ms": round(e2e * 3.2 + 50.0, 2),
                "edge_tier": "Low-Cost Android (ARM Cortex-A53 / A55 @ 1.8GHz, 2-3 GB RAM)",
            },
            "ANDROID_MEASURED": "PENDING_PHYSICAL_DEVICE_DEPLOYMENT",
        }

    def process_direct_card_selection(self, number: int) -> PedagogySessionResponse:
        """
        PATHWAY C: Guaranteed Fail-Safe Presentation Mode.
        Deterministic instant execution when a teacher or student taps numeral 1–20.
        """
        t0 = time.perf_counter()
        if not (1 <= number <= 20):
            return PedagogySessionResponse(
                session_id=f"card_err_{number}",
                input_mode="DIRECT_CARD_SELECTION",
                input_content=number,
                is_success=False,
                status_code="INVALID_NUMBER_RANGE",
                message=f"Requested number {number} is out of 1–20 FLN scope.",
                speech_result=None,
                translation_status="OUT_OF_SCOPE",
                hindi_text=None,
                mundari_text=None,
                mundari_phonetic=None,
                confidence=0.0,
                lesson=None,
                flashcard_svg_path=None,
                audio_asset_path=None,
                audio_status="MISSING",
                worksheet_ref=None,
                recommended_activity=None,
                fallback_recommended=False,
                content_id=None,
                audio_id=None,
            )

        # Fetch canonical registry item
        item = next(it for it in self.registry_data["items"] if it["number"] == number)
        lesson = asdict(self.fln_engine.get_lesson(number))
        activity = asdict(self.fln_engine.create_activity("count_objects", number))

        svg_path = os.path.join(
            self.workspace_root, "content", "flashcards", "numbers", f"card_{number:02d}.svg"
        )
        content_id = item["label_id"]
        audio_path, audio_id, audio_status = self._resolve_audio_asset(
            content_id=content_id,
            hindi_text=item["hindi_text"],
            number=number,
        )
        total_ms = (time.perf_counter() - t0) * 1000.0

        return PedagogySessionResponse(
            session_id=f"card_sess_{number}",
            input_mode="DIRECT_CARD_SELECTION",
            input_content=number,
            is_success=True,
            status_code="DETERMINISTIC_CARD_SUCCESS",
            message=f"100% verified pedagogical content retrieved for numeral {number}.",
            speech_result=None,
            translation_status="VERIFIED_EDUCATIONAL_LOOKUP",
            hindi_text=item["hindi_text"],
            mundari_text=item["mundari_text"],
            mundari_phonetic=item["mundari_phonetic"],
            confidence=1.0,
            lesson=lesson,
            flashcard_svg_path=svg_path if os.path.exists(svg_path) else None,
            audio_asset_path=audio_path,
            audio_status=audio_status,
            worksheet_ref={"number": number, "worksheet_id": "ws_01_recognition"},
            recommended_activity=activity,
            fallback_recommended=False,
            content_id=content_id,
            audio_id=audio_id,
            latency_breakdown={"total_end_to_end_ms": round(total_ms, 3)},
        )

    def process_teacher_input(self, hindi_text: str) -> PedagogySessionResponse:
        """
        PATHWAY B: Teacher Hindi Instruction / Numeral Bridge.
        Translates teacher Hindi input to verified Mundari FLN instruction.
        """
        t0 = time.perf_counter()
        trans_res = self.translation_engine.translate(hindi_text)

        if trans_res.status == "VERIFIED_EDUCATIONAL_LOOKUP":
            pair = trans_res.metadata
            # Check if this corresponds to a number
            item = next(
                (
                    it
                    for it in self.registry_data["items"]
                    if it["hindi_text"] == trans_res.normalized_source
                    or it["hindi_text"] == hindi_text.strip()
                    or str(it["number"]) == hindi_text.strip()
                ),
                None,
            )
            if item:
                number = item["number"]
                content_id = item["label_id"]
                lesson = asdict(self.fln_engine.get_lesson(number))
                activity = asdict(self.fln_engine.create_activity("listen_and_identify", number))
                svg_path = os.path.join(
                    self.workspace_root, "content", "flashcards", "numbers", f"card_{number:02d}.svg"
                )
                worksheet_ref = {"number": number, "worksheet_id": "ws_02_counting"}
                status_code = "TRANSLATION_LOOKUP_SUCCESS"
                msg = "Deterministic verified bilingual pedagogical content delivered."
                audio_path, audio_id, audio_status = self._resolve_audio_asset(
                    content_id=content_id, hindi_text=item["hindi_text"], number=number
                )
            else:
                # Verified educational classroom phrase
                content_id = self._get_phrase_content_id(hindi_text)
                number = None
                lesson = {
                    "type": "CLASSROOM_INSTRUCTION",
                    "category": pair.get("context", "FLN_CLASSROOM_INSTRUCTION"),
                    "meaning_hi": pair.get("meaning_hi", hindi_text),
                }
                activity = {
                    "activity_id": "act_tpr_command",
                    "title": "सुनो और करो (TPR)",
                    "instruction_hi": f"शिक्षक के आदेश '{hindi_text}' पर क्रिया करें",
                    "instruction_unr": f"आयूमपे आर कामीपे ({trans_res.translated_text})",
                }
                svg_path = None
                worksheet_ref = None
                status_code = "TRANSLATION_LOOKUP_SUCCESS"
                msg = "Deterministic verified classroom phrase instruction delivered."
                audio_path, audio_id, audio_status = self._resolve_audio_asset(
                    content_id=content_id, hindi_text=hindi_text
                )

            total_ms = (time.perf_counter() - t0) * 1000.0

            return PedagogySessionResponse(
                session_id=f"teacher_sess_{content_id}_{int(t0 * 1000) % 100000}",
                input_mode="TEACHER_HINDI_TEXT",
                input_content=hindi_text,
                is_success=True,
                status_code=status_code,
                message=msg,
                speech_result=None,
                translation_status=trans_res.status,
                hindi_text=pair.get("hindi_text", hindi_text),
                mundari_text=pair.get("mundari_text", trans_res.translated_text),
                mundari_phonetic=pair.get("mundari_phonetic", pair.get("phonetic", "")),
                confidence=trans_res.confidence,
                lesson=lesson,
                flashcard_svg_path=svg_path if svg_path and os.path.exists(svg_path) else None,
                audio_asset_path=audio_path,
                audio_status=audio_status,
                worksheet_ref=worksheet_ref,
                recommended_activity=activity,
                fallback_recommended=False,
                content_id=content_id,
                audio_id=audio_id,
                latency_breakdown={"total_end_to_end_ms": round(total_ms, 3)},
            )

        elif trans_res.status == "CORPUS_RETRIEVAL_MATCH":
            total_ms = (time.perf_counter() - t0) * 1000.0
            content_id = f"corpus_{hash(hindi_text) % 10000}"
            return PedagogySessionResponse(
                session_id=f"teacher_corpus_{hash(hindi_text) % 10000}",
                input_mode="TEACHER_HINDI_TEXT",
                input_content=hindi_text,
                is_success=True,
                status_code="CORPUS_SENTENCE_MATCH",
                message="Retrieved parallel sentence from validated corpus.",
                speech_result=None,
                translation_status=trans_res.status,
                hindi_text=trans_res.metadata.get("retrieved_hindi"),
                mundari_text=trans_res.translated_text,
                mundari_phonetic=None,
                confidence=trans_res.confidence,
                lesson=None,
                flashcard_svg_path=None,
                audio_asset_path=None,
                audio_status="MISSING",
                worksheet_ref=None,
                recommended_activity=None,
                fallback_recommended=False,
                content_id=content_id,
                audio_id=None,
                latency_breakdown={"total_end_to_end_ms": round(total_ms, 3)},
            )

        else:
            # Low confidence or out-of-vocabulary fallback
            total_ms = (time.perf_counter() - t0) * 1000.0
            return PedagogySessionResponse(
                session_id=f"teacher_oov_{hash(hindi_text) % 10000}",
                input_mode="TEACHER_HINDI_TEXT",
                input_content=hindi_text,
                is_success=False,
                status_code="OUT_OF_VOCABULARY_UNVERIFIED",
                message="No verified educational translation or corpus sentence found. Refusing to hallucinate.",
                speech_result=None,
                translation_status="OUT_OF_VOCABULARY_UNVERIFIED",
                hindi_text=hindi_text,
                mundari_text=None,
                mundari_phonetic=None,
                confidence=trans_res.confidence,
                lesson=None,
                flashcard_svg_path=None,
                audio_asset_path=None,
                audio_status="MISSING",
                worksheet_ref=None,
                recommended_activity=None,
                fallback_recommended=True,
                content_id=None,
                audio_id=None,
                latency_breakdown={"total_end_to_end_ms": round(total_ms, 3)},
            )

    def process_teacher_speech(
        self,
        audio_input: Union[bytes, np.ndarray, str],
        sample_rate: int = 16000,
    ) -> PedagogySessionResponse:
        """
        PATHWAY D: End-to-End Offline Teacher Voice Interaction Pathway.
        Flow:
        Teacher Spoken Voice
        -> Constrained Hindi Educational Speech Recognizer
        -> Hindi Text
        -> Translation Engine (Verified / Corpus)
        -> Mundari Text
        -> FLN Content Engine (Numerals / Commands / Activities)
        -> Mundari Audio Asset (Synthetic Prototype / Fallback)
        -> Bilingual Pedagogical Output
        """
        t_total_start = time.perf_counter()

        # Step 1: Preprocessing & Constrained Hindi Speech Recognition
        asr_res = self.hindi_asr.recognize_audio(audio_input, sample_rate=sample_rate)

        prep_ms = asr_res.metrics.get("prep_ms", 1.2)
        asr_ms = asr_res.latency_ms

        # Gate 1: Confidence / Quality Check on Hindi Speech
        if not asr_res.is_confident or asr_res.status != "RECOGNIZED" or not asr_res.recognized_text:
            if asr_res.status == "SILENCE":
                status_code = "SILENCE_DETECTED_FALLBACK"
                msg = "Teacher speech was silent or below energy threshold (-45 dBFS). Refusing to hallucinate."
            elif asr_res.status == "LOW_CONFIDENCE" and "Signal-to-noise" in str(asr_res.metrics.get("rejection_reason", "")):
                status_code = "HIGH_NOISE_FALLBACK"
                msg = "Teacher audio rejected due to high background noise / low SNR. Refusing to hallucinate."
            else:
                status_code = "AMBIGUOUS_AUDIO_FALLBACK_RECOMMENDED"
                msg = f"Constrained Hindi speech recognition uncertain (confidence: {asr_res.confidence:.2f} < 0.65). Prompting interactive card fallback."

            total_ms = (time.perf_counter() - t_total_start) * 1000.0
            latency_breakdown = {
                "audio_preprocessing_ms": round(prep_ms, 3),
                "hindi_recognition_ms": round(asr_ms, 3),
                "translation_ms": 0.0,
                "fln_lookup_ms": 0.0,
                "audio_lookup_ms": 0.0,
                "total_end_to_end_ms": round(total_ms, 3),
            }
            hw_profile = self._build_hardware_profile(latency_breakdown)

            return PedagogySessionResponse(
                session_id=f"voice_fail_{int(t_total_start * 1000) % 100000}",
                input_mode="TEACHER_HINDI_VOICE",
                input_content=f"Audio signal ({asr_res.duration_sec}s, {sample_rate}Hz)",
                is_success=False,
                status_code=status_code,
                message=msg,
                speech_result=asdict(asr_res),
                translation_status="UNVERIFIED_AMBIGUOUS_AUDIO",
                hindi_text=None,
                mundari_text=None,
                mundari_phonetic=None,
                confidence=asr_res.confidence,
                lesson=None,
                flashcard_svg_path=None,
                audio_asset_path=None,
                audio_status="MISSING",
                worksheet_ref=None,
                recommended_activity=None,
                fallback_recommended=True,
                content_id=None,
                audio_id=None,
                latency_breakdown=latency_breakdown,
                hardware_profile=hw_profile,
                diagnostic_info={
                    "audio_duration_sec": asr_res.duration_sec,
                    "rms": asr_res.metrics.get("rms_energy", 0.0),
                    "predicted_class": asr_res.recognized_text or "_background_",
                    "confidence": asr_res.confidence,
                    "second_best_confidence": asr_res.metrics.get("second_best_confidence", 0.0),
                    "margin": asr_res.metrics.get("margin", 0.0),
                    "final_decision": asr_res.status,
                    "translation_status": "NOT_TRANSLATED",
                    "audio_provenance": "MISSING",
                },
            )

        recognized_hindi = asr_res.recognized_text

        # Step 2: Translation Engine
        t_trans_start = time.perf_counter()
        trans_res = self.translation_engine.translate(recognized_hindi)
        t_trans_done = time.perf_counter()
        trans_ms = (t_trans_done - t_trans_start) * 1000.0

        # Gate 2: Translation Quality Check
        if trans_res.status == "OUT_OF_VOCABULARY_UNVERIFIED":
            total_ms = (time.perf_counter() - t_total_start) * 1000.0
            latency_breakdown = {
                "audio_preprocessing_ms": round(prep_ms, 3),
                "hindi_recognition_ms": round(asr_ms, 3),
                "translation_ms": round(trans_ms, 3),
                "fln_lookup_ms": 0.0,
                "audio_lookup_ms": 0.0,
                "total_end_to_end_ms": round(total_ms, 3),
            }
            hw_profile = self._build_hardware_profile(latency_breakdown)

            return PedagogySessionResponse(
                session_id=f"voice_oov_{int(t_total_start * 1000) % 100000}",
                input_mode="TEACHER_HINDI_VOICE",
                input_content=recognized_hindi,
                is_success=False,
                status_code="TRANSLATION_UNVERIFIED_FALLBACK",
                message="This phrase is not available in the verified classroom vocabulary.",
                speech_result=asdict(asr_res),
                translation_status="OUT_OF_VOCABULARY_UNVERIFIED",
                hindi_text=recognized_hindi,
                mundari_text=None,
                mundari_phonetic=None,
                confidence=trans_res.confidence,
                lesson=None,
                flashcard_svg_path=None,
                audio_asset_path=None,
                audio_status="MISSING",
                worksheet_ref=None,
                recommended_activity=None,
                fallback_recommended=True,
                content_id=None,
                audio_id=None,
                latency_breakdown=latency_breakdown,
                hardware_profile=hw_profile,
                diagnostic_info={
                    "audio_duration_sec": asr_res.duration_sec,
                    "rms": asr_res.metrics.get("rms_energy", 0.0),
                    "predicted_class": recognized_hindi,
                    "confidence": asr_res.confidence,
                    "second_best_confidence": asr_res.metrics.get("second_best_confidence", 0.0),
                    "margin": asr_res.metrics.get("margin", 0.0),
                    "final_decision": "REJECTED_UNSUPPORTED_TRANSLATION",
                    "translation_status": trans_res.status,
                    "audio_provenance": "MISSING",
                },
            )

        # Step 3: FLN Content Engine & Activity Generation
        t_fln_start = time.perf_counter()
        # Determine if recognized term is a number or a classroom command
        target_num = trans_res.metadata.get("number")
        num_item = None
        if target_num is not None:
            num_item = next((it for it in self.registry_data["items"] if it["number"] == target_num), None)
        if not num_item:
            num_item = next(
                (
                    it
                    for it in self.registry_data["items"]
                    if it["hindi_text"] == recognized_hindi
                    or it["hindi_text"] == trans_res.normalized_source
                    or (it["hindi_text"] == "पाँच" and recognized_hindi in ("पाँच", "पांच"))
                    or (it["hindi_text"] == "छह" and recognized_hindi in ("छह", "छः", "छ:"))
                ),
                None,
            )

        number: Optional[int] = None
        if num_item:
            number = num_item["number"]
            content_id = num_item["label_id"]
            lesson = asdict(self.fln_engine.get_lesson(number))
            activity = asdict(self.fln_engine.create_activity("count_objects", number))
            svg_file = os.path.join(
                self.workspace_root, "content", "flashcards", "numbers", f"card_{number:02d}.svg"
            )
            flashcard_svg_path = svg_file if os.path.isfile(svg_file) else None
            worksheet_ref = {"number": number, "worksheet_id": "ws_01_recognition"}
            status_code = "TEACHER_VOICE_NUMERACY_SUCCESS"
            msg = f"Teacher spoken numeral recognized as '{num_item['hindi_text']}' -> Mundari '{num_item['mundari_text']}'."
        elif trans_res.status == "VERIFIED_EDUCATIONAL_LOOKUP":
            # Pedagogical classroom command / phrase
            content_id = self._get_phrase_content_id(recognized_hindi)
            lesson = {
                "type": "CLASSROOM_INSTRUCTION",
                "category": trans_res.metadata.get("context", "FLN_CLASSROOM_INSTRUCTION"),
                "meaning_hi": trans_res.metadata.get("meaning_hi", recognized_hindi),
            }
            activity = {
                "activity_id": "act_tpr_command",
                "title": "सुनो और करो (Total Physical Response)",
                "instruction_hi": f"शिक्षक के आदेश '{recognized_hindi}' पर क्रिया करें",
                "instruction_unr": f"आयूमपे आर कामीपे ({trans_res.translated_text})",
            }
            flashcard_svg_path = None
            worksheet_ref = None
            status_code = "TEACHER_VOICE_COMMAND_SUCCESS"
            msg = f"Teacher classroom command recognized as '{recognized_hindi}' -> Mundari '{trans_res.translated_text}'."
        else:
            # Corpus sentence match
            content_id = f"corpus_{hash(recognized_hindi) % 10000}"
            lesson = None
            activity = None
            flashcard_svg_path = None
            worksheet_ref = None
            status_code = "TEACHER_VOICE_CORPUS_SUCCESS"
            msg = "Retrieved parallel sentence from validated corpus."

        t_fln_done = time.perf_counter()
        fln_ms = (t_fln_done - t_fln_start) * 1000.0

        # Step 4: Mundari Audio Resolution (Prototype TTS or Fallback)
        t_audio_start = time.perf_counter()
        audio_asset_path, audio_id, audio_status = self._resolve_audio_asset(
            content_id=content_id,
            hindi_text=recognized_hindi,
            number=number,
        )
        t_audio_done = time.perf_counter()
        audio_ms = (t_audio_done - t_audio_start) * 1000.0

        total_ms = (t_audio_done - t_total_start) * 1000.0
        latency_breakdown = {
            "audio_preprocessing_ms": round(prep_ms, 3),
            "hindi_recognition_ms": round(asr_ms, 3),
            "translation_ms": round(trans_ms, 3),
            "fln_lookup_ms": round(fln_ms, 3),
            "audio_lookup_ms": round(audio_ms, 3),
            "total_end_to_end_ms": round(total_ms, 3),
        }
        hw_profile = self._build_hardware_profile(latency_breakdown)

        return PedagogySessionResponse(
            session_id=f"voice_sess_{content_id}_{int(t_total_start * 1000) % 100000}",
            input_mode="TEACHER_HINDI_VOICE",
            input_content=f"Audio speech input for '{recognized_hindi}'",
            is_success=True,
            status_code=status_code,
            message=msg,
            speech_result=asdict(asr_res),
            translation_status=trans_res.status,
            hindi_text=recognized_hindi,
            mundari_text=trans_res.translated_text,
            mundari_phonetic=trans_res.metadata.get("phonetic") or trans_res.metadata.get("mundari_phonetic", ""),
            confidence=round(float(asr_res.confidence * trans_res.confidence), 4),
            lesson=lesson,
            flashcard_svg_path=flashcard_svg_path,
            audio_asset_path=audio_asset_path,
            audio_status=audio_status,
            worksheet_ref=worksheet_ref,
            recommended_activity=activity,
            fallback_recommended=False,
            content_id=content_id,
            audio_id=audio_id,
            latency_breakdown=latency_breakdown,
            hardware_profile=hw_profile,
            diagnostic_info={
                "audio_duration_sec": asr_res.duration_sec,
                "rms": asr_res.metrics.get("rms_energy", 0.0),
                "predicted_class": recognized_hindi,
                "confidence": asr_res.confidence,
                "second_best_confidence": asr_res.metrics.get("second_best_confidence", 0.0),
                "margin": asr_res.metrics.get("margin", 0.0),
                "final_decision": "ACCEPTED",
                "translation_status": trans_res.status,
                "audio_provenance": audio_status,
            },
        )

    def _format_speech_response(
        self, speech_res: SpeechRecognitionResult, sample_rate: int = 16000
    ) -> PedagogySessionResponse:
        speech_meta = {
            "engine_name": speech_res.engine_name,
            "engine_type": speech_res.engine_type,
            "status": speech_res.status,
            "class_index": speech_res.class_index,
            "confidence": speech_res.confidence,
            "margin": speech_res.margin,
            "is_confident": speech_res.is_confident,
        }

        if speech_res.is_confident and speech_res.class_index and speech_res.class_index > 0:
            # Confident recognition of an FLN numeral!
            number = speech_res.class_index
            item = next(it for it in self.registry_data["items"] if it["number"] == number)
            lesson = asdict(self.fln_engine.get_lesson(number))
            activity = asdict(self.fln_engine.create_activity("count_objects", number))
            svg_path = os.path.join(
                self.workspace_root, "content", "flashcards", "numbers", f"card_{number:02d}.svg"
            )
            content_id = item["label_id"]
            audio_path, audio_id, audio_status = self._resolve_audio_asset(
                content_id=content_id,
                hindi_text=item["hindi_text"],
                number=number,
            )

            return PedagogySessionResponse(
                session_id=f"speech_sess_{number}",
                input_mode="SPOKEN_SPEECH",
                input_content=f"Audio signal ({sample_rate} Hz)",
                is_success=True,
                status_code="SPEECH_RECOGNITION_SUCCESS",
                message=f"Spoken numeral recognized as {item['mundari_text']} with confidence {speech_res.confidence:.2f}.",
                speech_result=speech_meta,
                translation_status="VERIFIED_EDUCATIONAL_LOOKUP",
                hindi_text=item["hindi_text"],
                mundari_text=item["mundari_text"],
                mundari_phonetic=item["mundari_phonetic"],
                confidence=speech_res.confidence,
                lesson=lesson,
                flashcard_svg_path=svg_path if os.path.exists(svg_path) else None,
                audio_asset_path=audio_path,
                audio_status=audio_status,
                worksheet_ref={"number": number, "worksheet_id": "ws_01_recognition"},
                recommended_activity=activity,
                fallback_recommended=False,
                content_id=content_id,
                audio_id=audio_id,
            )
        else:
            # Low confidence or background noise -> Prompt fail-safe touch card mode!
            return PedagogySessionResponse(
                session_id="speech_ambiguous",
                input_mode="SPOKEN_SPEECH",
                input_content=f"Audio signal ({sample_rate} Hz)",
                is_success=False,
                status_code="AMBIGUOUS_AUDIO_FALLBACK_RECOMMENDED",
                message=(
                    f"Spoken input ambiguous (confidence {speech_res.confidence:.2f} < 0.65). "
                    "Prompting student/teacher to select flashcard directly."
                ),
                speech_result=speech_meta,
                translation_status="UNVERIFIED_AMBIGUOUS_AUDIO",
                hindi_text=None,
                mundari_text=None,
                mundari_phonetic=None,
                confidence=speech_res.confidence,
                lesson=None,
                flashcard_svg_path=None,
                audio_asset_path=None,
                audio_status="MISSING",
                worksheet_ref=None,
                recommended_activity=None,
                fallback_recommended=True,
                content_id=None,
                audio_id=None,
            )

    def process_spoken_audio(
        self,
        pcm_or_audio: Union[bytes, np.ndarray],
        sample_rate: int = 16000,
    ) -> PedagogySessionResponse:
        """
        PATHWAY A: Spoken Audio Input.
        Processes audio via modular Speech Recognition Manager.
        If confident, delivers pedagogical content; if low-confidence, suggests Interactive Card mode.
        """
        speech_res = self.speech_manager.process_raw_audio(pcm_or_audio, sample_rate)
        return self._format_speech_response(speech_res, sample_rate=sample_rate)

    def process_streaming_chunk(
        self, chunk: np.ndarray, sample_rate: int = 16000
    ) -> Optional[PedagogySessionResponse]:
        """
        Processes a streaming chunk (20-50 ms) through the streaming VAD.
        Returns a PedagogySessionResponse upon speech endpointing, or None while listening.
        """
        res = self.speech_manager.process_streaming_chunk(chunk, sample_rate=sample_rate)
        if res is not None:
            return self._format_speech_response(res, sample_rate=sample_rate)
        return None

    def process_continuous_stream(
        self, audio: np.ndarray, sample_rate: int = 16000
    ) -> List[PedagogySessionResponse]:
        """
        Processes a continuous audio stream containing one or more utterances.
        """
        results = self.speech_manager.process_continuous_stream(audio, sample_rate=sample_rate)
        return [self._format_speech_response(r, sample_rate=sample_rate) for r in results]

