"""
scripts/mirror_to_sih.py
=============================================================================
Mirrors updated files and directories from C:\\Users\\Lenovo\\Documents\\sih to
C:\\Users\\Lenovo\\sih.
"""

import os
import shutil
import sys

SRC = r"C:\Users\Lenovo\Documents\sih"
DST = r"C:\Users\Lenovo\sih"

FILES_TO_COPY = [
    os.path.join("server.py"),
    os.path.join("frontend", "index.html"),
    os.path.join("docs", "tts-architecture.md"),
    os.path.join("demo", "golden_set", "golden_demo_set.json"),
    os.path.join("demo", "golden_set", "golden_voice_demo.json"),
    os.path.join("content", "audio", "audio_manifest.json")
]

DIRS_TO_COPY = [
    os.path.join("ai", "speech"),
    os.path.join("ai", "translation"),
    os.path.join("demo", "golden_set"),
    os.path.join("content", "audio", "prototype_tts"),
    os.path.join("models", "tts"),
    os.path.join("scratch", "tts_benchmark"),
    os.path.join("tests"),
    os.path.join("scripts")
]

def main():
    print(f"Mirroring from {SRC} to {DST}...")
    for rel_f in FILES_TO_COPY:
        src_path = os.path.join(SRC, rel_f)
        dst_path = os.path.join(DST, rel_f)
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        if os.path.exists(src_path):
            shutil.copy2(src_path, dst_path)
            print(f"  Copied file: {rel_f}")

    for rel_d in DIRS_TO_COPY:
        src_dir = os.path.join(SRC, rel_d)
        dst_dir = os.path.join(DST, rel_d)
        if os.path.exists(src_dir):
            os.makedirs(dst_dir, exist_ok=True)
            for root, dirs, files in os.walk(src_dir):
                rel_root = os.path.relpath(root, src_dir)
                target_root = os.path.join(dst_dir, rel_root) if rel_root != "." else dst_dir
                os.makedirs(target_root, exist_ok=True)
                for f in files:
                    s_f = os.path.join(root, f)
                    d_f = os.path.join(target_root, f)
                    shutil.copy2(s_f, d_f)
            print(f"  Mirrored directory: {rel_d}")

    print("Mirroring complete!")

if __name__ == "__main__":
    main()
