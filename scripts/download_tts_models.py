"""
scripts/download_tts_models.py
=============================================================================
SIH260042: Bhasha Setu Controlled Offline TTS Model Installer
=============================================================================

PURPOSE:
Enables educators and system administrators to explicitly pre-download and
install the Meta MMS-TTS VITS models for local, offline classroom deployment.

GOVERNANCE & SAFETY POLICIES:
1. NEVER invoked during HTTP requests or runtime inference.
2. Models are downloaded into local directory: models/tts/<model_id>
3. Weights are strictly excluded from git tracking.
4. Model Licensing & Provenance:
   - Architecture: VITS (Variational Inference with adversarial learning for end-to-end Text-to-Speech)
   - Hindi Model: facebook/mms-tts-hin (36.3M parameters, ~145 MB)
   - Mundari Model: facebook/mms-tts-unr (36.3M parameters, ~145 MB)
   - License: Creative Commons Attribution-NonCommercial 4.0 (CC-BY-NC 4.0)
   - Source: Meta AI Multilingual Model Series (MMS)
=============================================================================
"""

import argparse
import os
import sys

# Ensure project root in sys.path
PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

MODELS = {
    "hindi": {
        "repo_id": "facebook/mms-tts-hin",
        "target_dir": os.path.join(PROJECT_ROOT, "models", "tts", "mms-tts-hin"),
        "description": "Meta MMS-TTS Hindi VITS Speech Model",
        "params": "36.3 Million",
        "size_mb": 145,
        "license": "CC-BY-NC 4.0"
    },
    "mundari": {
        "repo_id": "facebook/mms-tts-unr",
        "target_dir": os.path.join(PROJECT_ROOT, "models", "tts", "mms-tts-unr"),
        "description": "Meta MMS-TTS Mundari VITS Speech Model",
        "params": "36.3 Million",
        "size_mb": 145,
        "license": "CC-BY-NC 4.0"
    }
}


def download_model(lang: str, dry_run: bool = False) -> bool:
    info = MODELS.get(lang)
    if not info:
        print(f"[-] Unknown language: {lang}. Choose 'hindi' or 'mundari'.", file=sys.stderr)
        return False

    target_dir = info["target_dir"]
    repo_id = info["repo_id"]

    print(f"\n=======================================================")
    print(f"Target: {info['description']}")
    print(f"Hugging Face ID: {repo_id}")
    print(f"Destination: {target_dir}")
    print(f"Scale: {info['params']} (~{info['size_mb']} MB)")
    print(f"License: {info['license']}")
    print(f"=======================================================")

    if dry_run:
        print("[DRY-RUN] No downloads performed.")
        return True

    try:
        from transformers import AutoTokenizer, VitsModel
    except ImportError:
        print("[-] Error: 'transformers' or 'torch' not installed. Install requirements first.", file=sys.stderr)
        return False

    os.makedirs(target_dir, exist_ok=True)
    print(f"[+] Downloading tokenizer for {repo_id}...")
    tokenizer = AutoTokenizer.from_pretrained(repo_id)
    tokenizer.save_pretrained(target_dir)

    print(f"[+] Downloading VITS model weights for {repo_id}...")
    model = VitsModel.from_pretrained(repo_id)
    model.save_pretrained(target_dir)

    print(f"[SUCCESS] Model {repo_id} installed successfully to {target_dir}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Download and install offline TTS models for Bhasha Setu.")
    parser.add_argument(
        "--lang",
        choices=["hindi", "mundari", "all"],
        default="all",
        help="Language model to download (default: all)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Display target model details without downloading."
    )

    args = parser.parse_args()

    targets = ["hindi", "mundari"] if args.lang == "all" else [args.lang]
    for target in targets:
        download_model(target, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
