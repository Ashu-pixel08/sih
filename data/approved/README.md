# `data/approved/` — Canonically Approved Production Staging

## Purpose
This directory contains data that has completed the **entire 7-stage promotion pipeline**:
1. Technical Validation (Automated)
2. License Verification (Signed-off)
3. Linguistic Review (Native Mundari linguist signed-off)
4. Educational Review (JCERT / FLN primary specialist signed-off)
5. Acceptance Status set to `CANONICAL_APPROVED`

## Promotion to Production
Only records present in `data/approved/` are eligible for canonical ingestion into:
- `content/content_registry.json`
- `content/translations/classroom_phrasebook.json`
- Android assets (`android/app/src/main/assets/content/`)
- Edge deployment bundle (`deployment/bundle/`)

Every promotion triggers automated cross-platform parity tests to maintain byte-for-byte synchronization.
