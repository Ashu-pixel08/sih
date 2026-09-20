# Educational Dataset & Multimodal Assets Guide

This guide details the structure, catalog, schema, governance policies, and contribution procedures for all datasets and multimodal assets in the **Vernacular FLN Assistant** (`sih`).

---

## 1. Dataset Philosophy & FLN Scope

The curriculum and vocabulary datasets are tailored specifically for **Grade 1 Foundational Literacy and Numeracy (FLN)** in indigenous tribal primary schools across Jharkhand, Odisha, and West Bengal.

The educational datasets focus on:
1. **Foundational Numerals (1–20)**: Essential counting, ten-frame representations, and Mundari numeral roots.
2. **Classroom Action Commands (16 Core Instructions)**: Common teacher instructions (e.g., "बैठ जाओ", "किताब खोलो", "ध्यान से सुनो") essential for bilingual classroom transition.
3. **Core Environmental & Cultural Vocabulary (159 Curated Items)**: Ten high-frequency child-familiar categories (Animals, Birds, Body Parts, Colors, Family, Flowers, Food, Insects, Vegetables, Vehicles).

---

## 2. Directory Layout & Data Catalog

```text
data/
├── custom/                                           # Team-curated educational dataset
│   ├── SIH_CUSTOM_DATASET_CLEANED_AND_MODEL_READY.xlsx # Master editable spreadsheet
│   ├── cleaned_team_pairs.jsonl                      # Structured JSONL educational pairs (159 items)
│   ├── image_manifest.json                           # Metadata manifest for all 130 image assets
│   └── images/                                       # 130 high-resolution photographic assets
│       ├── Animals/                                  # 10 species (Cow, Elephant, Goat, etc.)
│       ├── Birds/                                    # 10 species (Crow, Peacock, Parrot, etc.)
│       ├── Body Parts/                               # 10 anatomical terms (Eye, Ear, Hand, etc.)
│       ├── Family/                                   # Kinship terms (Mother, Father, Sister, etc.)
│       ├── Flower/                                   # 10 flora items (Rose, Lotus, Marigold, etc.)
│       ├── Food/                                     # 10 food items (Rice, Bread, Milk, etc.)
│       ├── Fruits/                                   # 10 fruit items (Apple, Mango, Banana, etc.)
│       ├── Insects/                                  # 10 insect items (Ant, Butterfly, Bee, etc.)
│       ├── Vegetables/                               # 10 vegetable items (Potato, Tomato, etc.)
│       └── Vehicles/                                 # 10 transport items (Bus, Bicycle, Train, etc.)
├── processed/                                        # Model-ready NMT corpora splits
│   ├── merged_train.jsonl                            # 16,059 parallel training pairs
│   ├── merged_val.jsonl                              # 902 validation pairs
│   ├── merged_test.jsonl                             # 902 held-out test pairs
│   └── clean_bilingual_corpus.tsv                    # Deduplicated baseline pairs
└── test_vectors/                                     # Evaluation benchmark suites
    ├── final_educational_challenge_set.json          # 50 challenging pedagogical test sentences
    └── held_out_educational_vocab_test.json          # Unseen vocabulary generalization set
```

---

## 3. Custom Dataset Schema & Artifacts

### 3.1 `cleaned_team_pairs.jsonl` Schema
Each line in `data/custom/cleaned_team_pairs.jsonl` is a self-contained JSON object:

```json
{
  "id": "VOCAB_001",
  "category": "insects",
  "english": "Ant",
  "hindi": "चींटी",
  "mundari": "चींटी",
  "phonetic_transcription": "chinti",
  "status": "VALID_READABLE_IMAGE",
  "has_image": true,
  "image_path": "data/custom/images/Insects/Ant.jpg"
}
```

### Required Fields:
| Field | Type | Description |
|---|---|---|
| `id` | string | Unique identifier (`VOCAB_XXX`) |
| `category` | string | Normalized category slug (`animals`, `birds`, `insects`, etc.) |
| `english` | string | English gloss / translation |
| `hindi` | string | Standard Devanagari Hindi text |
| `mundari` | string | Mundari term written in Devanagari script |
| `phonetic_transcription` | string | Latin phonetic reading aid for non-native teachers |
| `status` | string | Quality status (`VALID_READABLE_IMAGE`, `ABSTRACT_NO_IMAGE`) |
| `has_image` | boolean | `true` if an associated visual asset exists on disk |
| `image_path` | string | Relative file path starting from repository root |

### 3.2 `image_manifest.json` Schema
Maintains provenance, dimensions, and readability validation for every multimodal asset:

```json
{
  "VOCAB_001": {
    "hindi": "चींटी",
    "mundari": "चींटी",
    "english": "Ant",
    "category": "insects",
    "image": {
      "workbook_path": "images/insects/Ant.jpg",
      "resolved_disk_path": "data/custom/images/Insects/Ant.jpg",
      "exists_on_disk": true,
      "is_readable": true,
      "width": 3070,
      "height": 4096,
      "format": "JPEG",
      "status": "VALID_READABLE_IMAGE"
    }
  }
}
```

---

## 4. How to Add or Modify Educational Vocabulary

### Step 1: Update the Spreadsheet or JSONL
You can edit `data/custom/SIH_CUSTOM_DATASET_CLEANED_AND_MODEL_READY.xlsx` or directly append to `data/custom/cleaned_team_pairs.jsonl`.

### Step 2: Linguistic Verification
* Verify that Hindi spelling uses standard Unicode Devanagari (avoid non-standard zero-width joiners).
* Verify that Mundari transcription accurately captures Austrian-Asiatic glottal stops or retroflex sounds using standard Devanagari orthography.
* Cross-reference against Hoffman's *Encyclopaedia Mundarica* or Bhaduri's *A Mundari-English Dictionary*.

### Step 3: Run Integrity & Validation Tests
```bash
pytest tests/test_educational_content_layer.py -v
```

---

## 5. How to Add or Update Multimodal Image Assets

1. **Format & Sizing**:
   * Preferred format: `.jpg` or `.png`.
   * Minimum resolution: $800 \times 800$ pixels.
   * Clear, high-contrast, uncluttered foreground object suitable for primary school children.
2. **Directory Placement**:
   * Save the image in `data/custom/images/<Category>/<ItemName>.<ext>`.
   * Example: `data/custom/images/Animals/Rabbit.jpg`.
3. **Relative Path Integrity**:
   * Never reference local filesystem paths like `C:\Users\...`.
   * Use relative paths matching the directory hierarchy.
4. **Update the Manifest**:
   * Ensure `image_manifest.json` and `cleaned_team_pairs.jsonl` reflect the added image.
   * Run verification to confirm the image is readable:
     ```python
     from PIL import Image
     img = Image.open("data/custom/images/Animals/Rabbit.jpg")
     img.verify()
     ```

---

## 6. Training & Evaluation Datasets (NMT)

### Data Splits (`data/processed/`)
* **Total Pairs**: 17,863 sentence pairs (17,783 canonical corpus pairs + 95 approved educational team pairs).
* **Train Set (`merged_train.jsonl`)**: 16,059 pairs (90%) used for Seq2Seq Transformer training.
* **Val Set (`merged_val.jsonl`)**: 902 pairs (5%) used for early stopping and perplexity checkpointing.
* **Test Set (`merged_test.jsonl`)**: 902 pairs (5%) held out for final BLEU/chrF++ evaluation.

### Licensing & Usage Constraints
* All base parallel text is governed under the **KPL BY-NC-SA-FS 1.0** license.
* Non-commercial, educational use only. Derivative models retain share-alike terms.
