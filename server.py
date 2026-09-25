"""
server.py
=============================================================================
SIH260042: Development & Browser-Prototype Translation Bridge Server
=============================================================================
ARCHITECTURAL MANDATE:
This server is STRICTLY a local development/browser-prototype bridge.
It allows the browser prototype (frontend/index.html) to query the Python
translation engine and 17,809-pair parallel corpus vector space.

IT IS NOT:
- A runtime dependency for Android (Android operates 100% offline without INTERNET).
- A cloud service or external API.
=============================================================================
"""

import os
import sys
import json
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import base64
import io
import wave
import numpy as np

from ai.translation.translation_engine import TranslationEngine
from ai.educational_content import EducationalContentManager
from ai.speech.pronunciation_service import PronunciationService
from ai.speech.speech_recognition_engine import SpeechRecognitionManager

# Initialize the translation engine once on startup with Tier 2 Neural Model enabled
print("Initializing TranslationEngine for browser-prototype bridge (with Tier 2 Neural Model)...")
engine = TranslationEngine(enable_neural=True)
print(f"TranslationEngine initialized with {len(engine.hindi_corpus)} corpus pairs, {len(engine.educational_lookup)} lookup terms, and Neural Engine active: {engine.neural_engine is not None} (artifact: {getattr(engine, 'neural_checkpoint_path', 'None')}).")

# Initialize Educational Content Manager
edu_manager = EducationalContentManager(PROJECT_ROOT)
print(f"EducationalContentManager initialized with {edu_manager.total_count} vocabulary items across {len(edu_manager.get_categories())} categories.")

# Initialize Offline Pronunciation & Speech Service
pronunciation_service = PronunciationService(project_root=PROJECT_ROOT)
p_health = pronunciation_service.get_health_status()
print(f"PronunciationService initialized (Mundari: {p_health['mundari']}, Hindi: {p_health['hindi']}, Cache: {p_health['cache']}).")

# Initialize Offline Speech Recognition (21-class Edge Classifier for FLN 1-20 Numerals)
speech_manager = SpeechRecognitionManager()
print(f"SpeechRecognitionManager initialized (Backend: {speech_manager.vocabulary_recognizer.backend_type}, Scope: FLN Grade 1 Numbers 1-20).")


class PrototypeBridgeHandler(SimpleHTTPRequestHandler):
    """
    HTTP handler that serves frontend static files while exposing a local
    /api/translate endpoint for browser-prototype queries.
    """

    def __init__(self, *args, **kwargs):
        frontend_dir = os.path.join(PROJECT_ROOT, "frontend")
        super().__init__(*args, directory=frontend_dir, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Health endpoint
        if path == "/api/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            p_stat = pronunciation_service.get_health_status()
            payload = {
                "status": "HEALTHY",
                "architecture": "LOCAL_DEVELOPMENT_BRIDGE_ONLY",
                "android_offline_mandate": "Android runs 100% offline without this server",
                "corpus_pairs": len(engine.hindi_corpus),
                "lookup_entries": len(engine.educational_lookup),
                "neural_model_active": engine.neural_engine is not None,
                "neural_model_path": getattr(engine, "neural_checkpoint_path", None),
                "pronunciation": {
                    "hindi": p_stat["hindi"],
                    "mundari": p_stat["mundari"],
                    "prototype_audio": "available" if p_stat["mundari"] == "available" else "unavailable",
                    "cache": p_stat["cache"],
                    "cache_entries": p_stat["cache_entries"],
                    "providers": p_stat["providers"],
                    "disclaimer": p_stat["disclaimer"]
                }
            }
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            return

        # Speech recognition status endpoint
        if path == "/api/asr/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            vocab = speech_manager.vocabulary_recognizer.get_supported_vocabulary()
            payload = {
                "status": "READY",
                "architecture": "EDGE_VOCABULARY_CNN_21_CLASS",
                "backend": speech_manager.vocabulary_recognizer.backend_type,
                "supported_languages": ["mundari (unr)", "hindi (hi)"],
                "controlled_vocabulary_scope": "FLN Grade 1 Numbers 1-20 (21 classes including background)",
                "supported_classes_count": len(vocab),
                "confidence_threshold": speech_manager.vocabulary_recognizer.confidence_threshold,
                "margin_threshold": speech_manager.vocabulary_recognizer.margin_threshold,
                "android_parity": "Exact contract match with TFLiteSpeechRecognizer.kt and AndroidAudioRecordService.kt",
                "disclaimer": "Local edge-optimized FLN vocabulary classifier. Continuous general Mundari ASR requires expanded acoustic corpus."
            }
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            return

        # Translation endpoint
        if path == "/api/translate":
            params = urllib.parse.parse_qs(parsed.query)
            query_text = params.get("text", [""])[0]
            direction = params.get("dir", ["hi-unr"])[0]
            src_lang = params.get("src_lang", [None])[0] or params.get("mode", [None])[0]

            result = engine.translate(query_text, direction=direction, src_lang=src_lang)

            response_data = {
                "status": result.status,
                "confidence": result.confidence,
                "source_text": result.source_text,
                "normalized_source": result.normalized_source,
                "translated_text": result.translated_text,
                "match_type": result.match_type,
                "provenance": result.provenance,
                "translation_source": result.translation_source,
                "requires_validation": result.requires_validation,
                "provenance_label": result.provenance_label,
                "ui_status": getattr(result, "ui_status", "AI TRANSLATION — REVIEW"),
                "normalized_hindi": (result.metadata and result.metadata.get("normalized_hindi")) or result.normalized_source,
                "metadata": result.metadata
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode("utf-8"))
            return

        # Educational Vocabulary endpoint
        if path == "/api/educational/vocabulary":
            params = urllib.parse.parse_qs(parsed.query)
            category = params.get("category", [""])[0] or None
            verified_only = params.get("verified_only", ["false"])[0].lower() in ("true", "1", "yes")
            search_query = params.get("search", [""])[0] or params.get("q", [""])[0] or None

            items = edu_manager.get_items(category=category, verified_only=verified_only, search=search_query)
            categories = edu_manager.get_categories()

            payload = {
                "status": "SUCCESS",
                "total": len(items),
                "dataset_source": "data/custom/cleaned_team_pairs.jsonl",
                "manifest_source": "data/custom/image_manifest.json",
                "categories": categories,
                "items": items
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            return

        # Educational Categories endpoint
        if path == "/api/educational/categories":
            categories = edu_manager.get_categories()
            payload = {
                "status": "SUCCESS",
                "total_categories": len(categories),
                "total_vocabulary": sum(c.get("total", c.get("count", 0)) for c in categories),
                "categories": categories
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            return

        # Teacher Voice Status endpoint
        if path == "/api/teacher-voice/status":
            if pronunciation_service.teacher_voice_manager:
                status = pronunciation_service.teacher_voice_manager.get_status()
            else:
                status = {
                    "status": "UNAVAILABLE",
                    "enrolled": False,
                    "enabled": False,
                    "profile_id": None,
                    "model_available": False,
                    "ui_state_label": "Teacher voice unavailable"
                }
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(status, ensure_ascii=False).encode("utf-8"))
            return

        # Serve static content from content/ or data/ directory if requested
        if path.startswith("/content/") or path.startswith("/data/"):
            rel_path = path.lstrip("/")
            file_path = os.path.join(PROJECT_ROOT, rel_path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                self.send_response(200)
                if file_path.endswith(".wav"):
                    self.send_header("Content-Type", "audio/wav")
                elif file_path.endswith(".json"):
                    self.send_header("Content-Type", "application/json")
                elif file_path.lower().endswith((".jpg", ".jpeg")):
                    self.send_header("Content-Type", "image/jpeg")
                elif file_path.lower().endswith(".png"):
                    self.send_header("Content-Type", "image/png")
                else:
                    self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
                return

        # Default static handler from frontend directory
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/translate":
            content_len = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_len).decode("utf-8")
            try:
                data = json.loads(post_body)
            except Exception:
                data = urllib.parse.parse_qs(post_body)
                data = {k: v[0] for k, v in data.items()}

            query_text = data.get("text", "")
            direction = data.get("dir") or data.get("direction") or "hi-unr"
            src_lang = data.get("src_lang") or data.get("mode")

            result = engine.translate(query_text, direction=direction, src_lang=src_lang)

            response_data = {
                "status": result.status,
                "confidence": result.confidence,
                "source_text": result.source_text,
                "normalized_source": result.normalized_source,
                "translated_text": result.translated_text,
                "match_type": result.match_type,
                "provenance": result.provenance,
                "translation_source": result.translation_source,
                "requires_validation": result.requires_validation,
                "provenance_label": result.provenance_label,
                "ui_status": getattr(result, "ui_status", "AI TRANSLATION — REVIEW"),
                "normalized_hindi": (result.metadata and result.metadata.get("normalized_hindi")) or result.normalized_source,
                "metadata": result.metadata
            }


            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode("utf-8"))
            return

        if path == "/api/teacher-voice/toggle":
            content_len = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else ""
            try:
                data = json.loads(post_body) if post_body else {}
            except Exception:
                data = urllib.parse.parse_qs(post_body)
                data = {k: v[0] for k, v in data.items()}

            enabled = bool(data.get("enabled", True))
            if pronunciation_service.teacher_voice_manager:
                pronunciation_service.teacher_voice_manager.set_enabled(enabled)
                status = pronunciation_service.teacher_voice_manager.get_status()
            else:
                status = {
                    "status": "UNAVAILABLE",
                    "enrolled": False,
                    "enabled": False,
                    "profile_id": None,
                    "model_available": False,
                    "ui_state_label": "Teacher voice unavailable"
                }

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(json.dumps(status, ensure_ascii=False).encode("utf-8"))
            return

        if path in ("/api/teacher-voice/delete", "/api/teacher-voice/profile"):
            if pronunciation_service.teacher_voice_manager:
                pronunciation_service.teacher_voice_manager.delete_profile()
            resp = {"status": "SUCCESS", "message": "Teacher voice profile deleted and cache cleared."}
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode("utf-8"))
            return

        if path == "/api/pronunciation":
            content_len = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else ""
            try:
                data = json.loads(post_body) if post_body else {}
            except Exception:
                data = urllib.parse.parse_qs(post_body)
                data = {k: v[0] for k, v in data.items()}

            text = data.get("text")
            language = data.get("language")
            teacher_voice_req = bool(data.get("teacher_voice", False))

            result, error = pronunciation_service.synthesize(text, language, use_teacher_voice=teacher_voice_req)

            if error:
                code = error.get("http_code", 400)
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()
                resp_payload = {
                    "status": error.get("status", "ERROR"),
                    "message": error.get("message", "Pronunciation generation failed."),
                    "language": error.get("language"),
                    "details": error.get("details")
                }
                self.wfile.write(json.dumps(resp_payload, ensure_ascii=False).encode("utf-8"))
                return

            # Determine teacher voice response header
            if result.teacher_voice_applied:
                tv_header = "ACTIVE"
            elif teacher_voice_req:
                if result.language == "mundari" and not (
                    pronunciation_service.registry_provider and pronunciation_service.registry_provider.has_entry(text, "mundari")
                ):
                    tv_header = "BLOCKED_UNCONTROLLED_MUNDARI"
                else:
                    tv_header = "INACTIVE"
            else:
                tv_header = "INACTIVE"

            # Success: Return binary WAV audio with proper headers
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Expose-Headers", "X-Pronunciation-Language, X-Pronunciation-Engine, X-Pronunciation-Source, X-Pronunciation-Cache, X-Pronunciation-Validation-Status, X-Pronunciation-Teacher-Voice")
            self.send_header("Content-Length", str(len(result.audio_bytes)))
            self.send_header("X-Pronunciation-Language", result.language)
            self.send_header("X-Pronunciation-Engine", result.engine_name)
            self.send_header("X-Pronunciation-Source", result.source_type)
            self.send_header("X-Pronunciation-Cache", "HIT" if result.is_cached else "MISS")
            self.send_header("X-Pronunciation-Validation-Status", result.verification_status)
            self.send_header("X-Pronunciation-Teacher-Voice", tv_header)
            self.end_headers()
            self.wfile.write(result.audio_bytes)
            return

        if path in ("/api/asr", "/api/speech-recognize"):
            content_len = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_len) if content_len > 0 else b""
            content_type = self.headers.get("Content-Type", "")

            pcm_data = None
            sample_rate = 16000
            req_lang = "mundari"

            # 1. Parse JSON payload if sent as JSON
            if "application/json" in content_type or (post_body.strip().startswith(b"{") and post_body.strip().endswith(b"}")):
                try:
                    data = json.loads(post_body.decode("utf-8"))
                    b64_str = data.get("audio") or data.get("audio_base64") or data.get("pcm_base64") or data.get("data")
                    sample_rate = int(data.get("sample_rate", 16000))
                    req_lang = (data.get("language") or data.get("lang") or "mundari").lower()
                    if b64_str:
                        raw_audio = base64.b64decode(b64_str)
                    else:
                        raw_audio = b""
                except Exception:
                    raw_audio = b""
            else:
                raw_audio = post_body

            # 2. Extract PCM from WAV or raw int16 bytes
            if raw_audio.startswith(b"RIFF") and len(raw_audio) >= 44:
                try:
                    with wave.open(io.BytesIO(raw_audio), "rb") as wf:
                        sample_rate = wf.getframerate()
                        n_channels = wf.getnchannels()
                        sampwidth = wf.getsampwidth()
                        n_frames = wf.getnframes()
                        frames = wf.readframes(n_frames)
                        if sampwidth == 2:
                            pcm_int16 = np.frombuffer(frames, dtype=np.int16)
                        else:
                            pcm_int16 = (np.frombuffer(frames, dtype=np.uint8).astype(np.int16) - 128) * 256
                        if n_channels > 1:
                            pcm_int16 = pcm_int16[::n_channels]
                        pcm_data = pcm_int16.astype(np.float32) / 32768.0
                except Exception:
                    pcm_data = None
            elif len(raw_audio) > 0:
                try:
                    pcm_int16 = np.frombuffer(raw_audio, dtype=np.int16)
                    pcm_data = pcm_int16.astype(np.float32) / 32768.0
                except Exception:
                    pcm_data = None

            if pcm_data is None or len(pcm_data) == 0:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()
                err_payload = {
                    "status": "ERROR",
                    "message": "No valid audio data received. Provide 16 kHz WAV or int16 PCM data.",
                    "recognized_text": None,
                    "is_confident": False
                }
                self.wfile.write(json.dumps(err_payload, ensure_ascii=False).encode("utf-8"))
                return

            # 3. Classify with speech_manager (Edge-optimized FLN vocabulary classifier)
            res = speech_manager.process_raw_audio(pcm_data, sample_rate=sample_rate)

            response_payload = {
                "status": res.status,
                "recognized_text": res.recognized_text,
                "hindi_equivalent": res.hindi_equivalent,
                "class_index": res.class_index,
                "label_id": res.label_id,
                "confidence": res.confidence,
                "margin": res.margin,
                "is_confident": res.is_confident,
                "engine_name": res.engine_name,
                "engine_type": res.engine_type,
                "decision": res.decision,
                "rejection_reason": res.rejection_reason,
                "rms_energy": res.rms_energy,
                "audio_duration_sec": res.audio_duration_sec,
                "metadata": res.metadata
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(json.dumps(response_payload, ensure_ascii=False).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == "/api/teacher-voice/profile":
            if pronunciation_service.teacher_voice_manager:
                pronunciation_service.teacher_voice_manager.delete_profile()
            resp = {"status": "SUCCESS", "message": "Teacher voice profile deleted and cache cleared."}
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def run_server(port=8080):
    server_address = ("", port)
    httpd = HTTPServer(server_address, PrototypeBridgeHandler)
    print(f"Browser-Prototype Bridge Server running on http://localhost:{port}/")
    print("Serving frontend/ and /api/translate. Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()


if __name__ == "__main__":
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port)
