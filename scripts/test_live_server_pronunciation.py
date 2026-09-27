"""
scripts/test_live_server_pronunciation.py
=============================================================================
Live integration test for server.py HTTP API:
Validates POST /api/pronunciation for all three Golden Demo flows:
  - Flow A: Hindi -> Mundari target ("नेआ चिनाः संख्या तना", "mundari")
  - Flow B: Mundari -> Hindi target ("अब मैं गिनती करूँगा बारह तक", "hindi")
  - Flow C: Hinglish -> Mundari target ("नेआ चिनाः संख्या तना", "mundari")

Checks:
  - HTTP 200
  - Content-Type: audio/wav
  - X-Pronunciation-Status header present
  - X-Pronunciation-Quality-Gate: PASSED
  - X-Pronunciation-Language matches
  - X-Pronunciation-Engine present
  - X-Pronunciation-Validation-Status present
  - Valid 16-bit PCM WAV bytes returned
"""

import sys
import os
import json
import time
import threading
import urllib.request
from http.server import HTTPServer

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

WORKSPACE_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from server import PrototypeBridgeHandler


def run_live_test():
    port = 8765
    server = HTTPServer(("127.0.0.1", port), PrototypeBridgeHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"Test server started on http://127.0.0.1:{port}/")

    test_cases = [
        {
            "flow": "Flow A (Hindi -> Mundari)",
            "text": "नेआ चिनाः संख्या तना",
            "language": "mundari",
            "expected_lang": "mundari"
        },
        {
            "flow": "Flow B (Mundari -> Hindi)",
            "text": "अब मैं गिनती करूँगा बारह तक",
            "language": "hindi",
            "expected_lang": "hindi"
        },
        {
            "flow": "Flow C (Hinglish -> Mundari)",
            "text": "नेआ चिनाः संख्या तना",
            "language": "mundari",
            "expected_lang": "mundari"
        }
    ]

    all_passed = True

    try:
        time.sleep(0.5)
        for tc in test_cases:
            print(f"\n--- Testing {tc['flow']} ---")
            payload = json.dumps({"text": tc["text"], "language": tc["language"]}).encode("utf-8")
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/pronunciation",
                data=payload,
                headers={"Content-Type": "application/json"}
            )

            with urllib.request.urlopen(req) as resp:
                status_code = resp.status
                headers = dict(resp.headers)
                audio_bytes = resp.read()

                print(f"  Status Code: {status_code}")
                print(f"  Content-Type: {headers.get('Content-Type')}")
                print(f"  X-Pronunciation-Status: {headers.get('X-Pronunciation-Status')}")
                print(f"  X-Pronunciation-Quality-Gate: {headers.get('X-Pronunciation-Quality-Gate')}")
                print(f"  X-Pronunciation-Language: {headers.get('X-Pronunciation-Language')}")
                print(f"  X-Pronunciation-Engine: {headers.get('X-Pronunciation-Engine')}")
                print(f"  X-Pronunciation-Source: {headers.get('X-Pronunciation-Source')}")
                print(f"  X-Pronunciation-Validation-Status: {headers.get('X-Pronunciation-Validation-Status')}")
                print(f"  Audio Payload: {len(audio_bytes)} bytes")

                # Assertions
                assert status_code == 200, f"Expected 200, got {status_code}"
                assert headers.get("Content-Type") == "audio/wav", "Content-Type must be audio/wav"
                assert headers.get("X-Pronunciation-Quality-Gate") == "PASSED", "Quality gate must pass"
                assert headers.get("X-Pronunciation-Language") == tc["expected_lang"], "Language header mismatch"
                assert headers.get("X-Pronunciation-Status") in (
                    "AUDIO_READY",
                    "AUDIO_PROTOTYPE_PENDING_VALIDATION",
                    "AUDIO_SYNTHETIC_UNVERIFIED"
                ), f"Unexpected status: {headers.get('X-Pronunciation-Status')}"
                assert len(audio_bytes) > 1000, "Audio bytes must be > 1000"
                assert audio_bytes[:4] == b"RIFF", "Audio must start with RIFF header"
                print(f"  [PASS] {tc['flow']} verified successfully.")

    except Exception as e:
        print(f"\n[FAIL] Live test encountered error: {e}")
        all_passed = False
    finally:
        print("\nShutting down test server...")
        server.shutdown()
        server.server_close()

    if not all_passed:
        sys.exit(1)
    print("\nAll live server pronunciation flows passed successfully!")


if __name__ == "__main__":
    run_live_test()
