# `data/validated/` — Technically Verified Staging Area

## Purpose
Holds records that have successfully passed **all automated technical and licensing gates**:
- Schema conformance
- UTF-8 NFC normalization and zero control characters
- Duplicate detection
- License verification (explicit non-commercial / educational use permitted)
- Audio format verification (16 kHz, 16-bit mono PCM WAV)
- Speaker disjointness for speech datasets

## Important Limitation
**Technical validation != Educational approval.**
Records in `data/validated/` are syntactically and legally sound, but **MUST NOT** be merged into canonical application files until they receive formal **Linguistic Review** and **Educational Alignment Review** by native experts.
