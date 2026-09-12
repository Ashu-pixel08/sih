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

from ai.translation.translation_engine import TranslationEngine

# Initialize the translation engine once on startup with Tier 2 Neural Model enabled
print("Initializing TranslationEngine for browser-prototype bridge (with Tier 2 Neural Model)...")
engine = TranslationEngine(enable_neural=True)
print(f"TranslationEngine initialized with {len(engine.hindi_corpus)} corpus pairs, {len(engine.educational_lookup)} lookup terms, and Neural Engine active: {engine.neural_engine is not None}.")


class PrototypeBridgeHandler(SimpleHTTPRequestHandler):
    """
    HTTP handler that serves frontend static files while exposing a local
    /api/translate endpoint for browser-prototype queries.
    """

    def __init__(self, *args, **kwargs):
        frontend_dir = os.path.join(PROJECT_ROOT, "frontend")
        super().__init__(*args, directory=frontend_dir, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Health endpoint
        if path == "/api/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            payload = {
                "status": "HEALTHY",
                "architecture": "LOCAL_DEVELOPMENT_BRIDGE_ONLY",
                "android_offline_mandate": "Android runs 100% offline without this server",
                "corpus_pairs": len(engine.hindi_corpus),
                "lookup_entries": len(engine.educational_lookup),
                "neural_model_active": engine.neural_engine is not None
            }
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            return

        # Translation endpoint
        if path == "/api/translate":
            params = urllib.parse.parse_qs(parsed.query)
            query_text = params.get("text", [""])[0]
            direction = params.get("dir", ["hi-unr"])[0]

            result = engine.translate(query_text, direction=direction)

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
                "metadata": result.metadata
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode("utf-8"))
            return

        # Serve static content from content/audio directory if requested
        if path.startswith("/content/"):
            rel_path = path.lstrip("/")
            file_path = os.path.join(PROJECT_ROOT, rel_path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                self.send_response(200)
                if file_path.endswith(".wav"):
                    self.send_header("Content-Type", "audio/wav")
                elif file_path.endswith(".json"):
                    self.send_header("Content-Type", "application/json")
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

            result = engine.translate(query_text, direction=direction)

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
                "metadata": result.metadata
            }


            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
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
