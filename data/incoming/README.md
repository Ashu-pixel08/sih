# `data/incoming/` — Untrusted Staging Area

## Purpose
This directory is the **strict intake landing zone** for candidate external datasets, proposed parallel texts, classroom phrase lists, raw audio recordings, or curriculum mappings.

## Security & Integrity Rules
1. **Zero Trust Status:** Data in this folder is strictly untrusted.
2. **Never Imported by Production:** The application runtime (`frontend/index.html`, `TranslationEngine`, `LocalContentRegistry.kt`, or TFLite classifiers) **NEVER** reads from `data/incoming/`.
3. **Mandatory Manifest:** Every candidate dataset placed here MUST be accompanied by a `<dataset_name>.license_manifest.json` conforming to `data/schemas/license_manifest.schema.json`.
4. **Validation Required:** Before moving to any other stage, data must be processed by `tools/data_intake/validator.py`.
5. **No Direct Promotion:** Files can only exit `incoming/` via the automated promoter tool:
   - To `data/validated/` if all technical schema, unicode, duplicate, and license checks pass.
   - To `data/quarantine/` if any validation error, license ambiguity, or suspicious content is detected.
