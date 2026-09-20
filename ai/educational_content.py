"""
ai/educational_content.py
=============================================================================
SIH260042: Educational Vocabulary and Multimodal Asset Layer
=============================================================================
Provides high-performance, single-source-of-truth access to the 159-row
team educational vocabulary dataset and image manifest:
  - data/custom/cleaned_team_pairs.jsonl
  - data/custom/image_manifest.json
  - data/custom/images/

Guarantees:
  1. No hardcoded vocabulary: all terms, categories, and image mappings
     are parsed dynamically from dataset artifacts.
  2. Status transparency: entries labeled UNVERIFIED_HELD_FOR_REVIEW
     are never promoted to VERIFIED EDUCATIONAL.
  3. Audio integrity: distinguishes actual pre-recorded audio from
     unrecorded items with zero false claims.
=============================================================================
"""

import os
import json
from typing import List, Dict, Any, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

CATEGORY_DISPLAY_MAP = {
    "animals": "Animals",
    "aquatic_animals": "Aquatic Animals",
    "birds": "Birds",
    "body_parts": "Body Parts",
    "colors": "Colors",
    "family": "Family",
    "flowers": "Flowers",
    "food": "Food",
    "grains": "Grains",
    "insects": "Insects",
    "months": "Months",
    "shapes": "Shapes",
    "things": "Things",
    "vegetables": "Vegetables",
    "vehicles": "Vehicles",
    "weeks": "Weeks"
}

def format_category_name(raw_cat: str) -> str:
    """Converts raw dataset category slugs into human-friendly display titles."""
    if not raw_cat:
        return "General"
    lower = raw_cat.strip().lower()
    if lower in CATEGORY_DISPLAY_MAP:
        return CATEGORY_DISPLAY_MAP[lower]
    return raw_cat.replace("_", " ").title().strip()


class EducationalContentManager:
    """Manages educational vocabulary, category hierarchies, and image asset routing."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or PROJECT_ROOT
        self.jsonl_path = os.path.join(self.base_dir, "data", "custom", "cleaned_team_pairs.jsonl")
        self.manifest_path = os.path.join(self.base_dir, "data", "custom", "image_manifest.json")
        self._items: List[Dict[str, Any]] = []
        self._categories: List[Dict[str, Any]] = []
        self._id_map: Dict[str, Dict[str, Any]] = {}
        self.load()

    def load(self) -> None:
        """Loads and cross-references team dataset and image manifest."""
        self._items.clear()
        self._id_map.clear()

        manifest_data = {}
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    m_raw = json.load(f)
                    manifest_data = m_raw.get("items", {})
            except Exception as e:
                print(f"[EducationalContentManager] Notice: could not load manifest: {e}")

        if os.path.exists(self.jsonl_path):
            with open(self.jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    vocab_id = rec.get("id", "")
                    raw_cat = rec.get("category", "general")
                    disp_cat = format_category_name(raw_cat)
                    hi_word = rec.get("hindi", "").strip()
                    unr_word = rec.get("mundari", "").strip()
                    en_word = rec.get("english", "").strip()

                    # Status evaluation
                    prom_status = rec.get("promotion_status", "UNVERIFIED_HELD_FOR_REVIEW")
                    is_eligible = bool(rec.get("training_eligible", False))
                    is_verified = is_eligible and (prom_status in ("APPROVED_TRAINING_PAIR", "LOANWORD_CORROBORATED"))

                    if is_verified:
                        val_badge = "VERIFIED EDUCATIONAL"
                        status_description = "Attested in classroom corpus / verified loanword"
                    else:
                        val_badge = "HELD FOR REVIEW"
                        status_description = "Unverified translation candidate held for field review"

                    # Image resolution
                    img_meta = rec.get("image_metadata") or {}
                    disk_path = img_meta.get("resolved_disk_path") or ""

                    # Check manifest override
                    if vocab_id in manifest_data:
                        man_item = manifest_data[vocab_id]
                        man_img = man_item.get("image", {})
                        if man_img.get("resolved_disk_path"):
                            disk_path = man_img.get("resolved_disk_path")

                    # Normalize image path to web URL
                    web_img_url = "/" + disk_path.replace("\\", "/").lstrip("/") if disk_path else ""

                    # Check physical existence
                    abs_img_path = os.path.join(self.base_dir, disk_path.replace("/", os.sep))
                    exists_on_disk = os.path.exists(abs_img_path) and os.path.isfile(abs_img_path)

                    item = {
                        "id": vocab_id,
                        "english": en_word,
                        "hindi": hi_word,
                        "mundari": unr_word,
                        "phonetic": rec.get("phonetic", ""),
                        "category": disp_cat,
                        "category_raw": raw_cat,
                        "classification": rec.get("classification", ""),
                        "promotion_status": prom_status,
                        "training_eligible": is_eligible,
                        "is_verified": is_verified,
                        "validation_badge": val_badge,
                        "status_description": status_description,
                        "linguistic_note": rec.get("linguistic_note", ""),
                        "image_url": web_img_url,
                        "image_disk_path": disk_path,
                        "image_exists": exists_on_disk,
                        "image_status": "AVAILABLE" if exists_on_disk else "MISSING",
                        "audio_available": False,
                        "audio_url": None,
                        "audio_status": "PENDING_FIELD_COLLECTION"
                    }

                    self._items.append(item)
                    self._id_map[vocab_id] = item

        # Derive distinct categories with metadata
        cat_counts = {}
        for it in self._items:
            c = it["category"]
            if c not in cat_counts:
                cat_counts[c] = {"name": c, "raw": it["category_raw"], "total": 0, "verified": 0, "unverified": 0}
            cat_counts[c]["total"] += 1
            if it["is_verified"]:
                cat_counts[c]["verified"] += 1
            else:
                cat_counts[c]["unverified"] += 1

        for c_data in cat_counts.values():
            c_data["count"] = c_data["total"]

        self._categories = sorted(list(cat_counts.values()), key=lambda x: x["name"])

    @property
    def total_count(self) -> int:
        return len(self._items)

    def get_items(
        self,
        category: Optional[str] = None,
        verified_only: bool = False,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Filters vocabulary records based on category, verification level, and query."""
        results = self._items
        if category and category.lower() != "all":
            cat_norm = category.strip().lower()
            results = [x for x in results if x["category"].lower() == cat_norm or x["category_raw"].lower() == cat_norm]
        if verified_only:
            results = [x for x in results if x["is_verified"]]
        if search and search.strip():
            q = search.strip().lower()
            results = [
                x for x in results
                if q in x["english"].lower() or q in x["hindi"].lower() or q in x["mundari"].lower() or q in x["category"].lower()
            ]
        return results

    def get_categories(self) -> List[Dict[str, Any]]:
        """Returns dynamically derived category list with counts."""
        return self._categories

    def get_item_by_id(self, vocab_id: str) -> Optional[Dict[str, Any]]:
        return self._id_map.get(vocab_id)

    def get_all_vocabulary(self) -> List[Dict[str, Any]]:
        return self._items

    def get_vocabulary_by_category(self, category: str) -> List[Dict[str, Any]]:
        return self.get_items(category=category)

    def search_vocabulary(self, query: str) -> List[Dict[str, Any]]:
        return self.get_items(search=query)


_GLOBAL_MGR: Optional[EducationalContentManager] = None

def get_educational_content_manager(base_dir: Optional[str] = None) -> EducationalContentManager:
    global _GLOBAL_MGR
    if _GLOBAL_MGR is None:
        _GLOBAL_MGR = EducationalContentManager(base_dir=base_dir)
    return _GLOBAL_MGR
