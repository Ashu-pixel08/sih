"""
Bilingual Translation Engine for Mother Tongue-Based Education.

Implements a transparent three-tier translation architecture:
1. Tier 1: Exact Verified Educational Retrieval
   - Canonical 1-20 numbers and core FLN classroom instructions
   - Deterministic dictionary lookup (100% precision, zero hallucination)
   - Status: VERIFIED_EDUCATIONAL_LOOKUP (Confidence: 1.0)
   - Or: COMPOSED_FROM_ATTESTED_FRAGMENTS (Confidence: 1.0)
2. Tier 2: Corpus Sentence Retrieval
   - Sourced from the validated 17,809 Hindi-Mundari parallel sentence pairs
   - Character n-gram TF-IDF vector space retrieval
   - Matches returned ONLY when cosine similarity exceeds calibrated threshold
   - Status: CORPUS_RETRIEVAL_MATCH (Confidence: cosine similarity >= 0.55)
3. Tier 3: Out of Vocabulary / Low Confidence Fallback
   - Status: OUT_OF_VOCABULARY_UNVERIFIED (Confidence: similarity < 0.55)
   - Refuses to hallucinate synthetic translations
"""

import os
import sys
import re
import json
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

# Ensure workspace root is in sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_proj_dir = os.path.abspath(os.path.join(_current_dir, "..", ".."))
if _proj_dir not in sys.path:
    sys.path.insert(0, _proj_dir)

try:
    from .hindi_normalizer import (
        normalize_hindi,
        normalize_for_lookup,
        NUMERAL_SPELLING_ALIASES,
        DEVANAGARI_DIGITS_TO_WORDS,
        ASCII_DIGITS_TO_WORDS
    )
except ImportError:
    try:
        from ai.translation.hindi_normalizer import (
            normalize_hindi,
            normalize_for_lookup,
            NUMERAL_SPELLING_ALIASES,
            DEVANAGARI_DIGITS_TO_WORDS,
            ASCII_DIGITS_TO_WORDS
        )
    except ImportError:
        from hindi_normalizer import (
            normalize_hindi,
            normalize_for_lookup,
            NUMERAL_SPELLING_ALIASES,
            DEVANAGARI_DIGITS_TO_WORDS,
            ASCII_DIGITS_TO_WORDS
        )


@dataclass
class TranslationResult:
    status: str
    confidence: float
    source_text: str
    normalized_source: str
    translated_text: Optional[str]
    match_type: str
    provenance: str
    metadata: Dict[str, Any]
    translation_source: str = "CORPUS_RETRIEVAL"
    requires_validation: bool = False
    provenance_label: str = ""
    ui_status: str = "AI TRANSLATION — REVIEW"

    def __post_init__(self):
        if not hasattr(self, "ui_status") or self.ui_status == "AI TRANSLATION — REVIEW":
            if self.translation_source in ("EDUCATIONAL_REGISTRY", "VERIFIED_LOOKUP") or self.status in ("VERIFIED_EDUCATIONAL_LOOKUP", "COMPOSED_FROM_ATTESTED_FRAGMENTS", "CANONICAL_NUMERAL"):
                self.ui_status = "VERIFIED EDUCATIONAL"
            elif self.status in ("OUT_OF_VOCABULARY_UNVERIFIED", "UNATTESTED_INPUT") or self.translated_text is None:
                self.ui_status = "TRANSLATION UNAVAILABLE"
            elif self.translation_source == "NEURAL_MODEL":
                if self.metadata and self.metadata.get("ui_status"):
                    self.ui_status = self.metadata["ui_status"]
                else:
                    self.ui_status = "AI TRANSLATION — REVIEW"
            else:
                self.ui_status = "AI TRANSLATION — REVIEW"



class TranslationEngine:
    """Offline-capable hybrid retrieval and translation engine for Hindi -> Mundari."""

    # Calibrated Confidence Thresholds
    SIMILARITY_MIN_THRESHOLD: float = 0.55
    EXACT_SIMILARITY_THRESHOLD: float = 0.90

    # Core classroom phrases fallback (verified MTB-MLE educational terminology)
    EDUCATIONAL_PHRASEBOOK: Dict[str, Dict[str, Any]] = {
        "नमस्ते": {
            "mundari_text": "जोहार",
            "phonetic": "johar",
            "root": "जोहार",
            "meaning_hi": "नमस्कार / अभिवादन",
            "context": "FLN_CLASSROOM_GREETING"
        },
        "जोहार": {
            "mundari_text": "जोहार",
            "phonetic": "johar",
            "root": "जोहार",
            "meaning_hi": "नमस्कार / अभिवादन",
            "context": "FLN_CLASSROOM_GREETING"
        },
        "बैठो": {
            "mundari_text": "दुबपे",
            "phonetic": "dubpe",
            "root": "दुब",
            "meaning_hi": "बैठ जाइए",
            "context": "FLN_CLASSROOM_INSTRUCTION"
        },
        "बैठिए": {
            "mundari_text": "दुबपे",
            "phonetic": "dubpe",
            "root": "दुब",
            "meaning_hi": "बैठ जाइए",
            "context": "FLN_CLASSROOM_INSTRUCTION"
        },
        "खड़े हो जाओ": {
            "mundari_text": "तिंगुपे",
            "phonetic": "tingupe",
            "root": "तिंगु",
            "meaning_hi": "खड़े हो जाइए",
            "context": "FLN_CLASSROOM_INSTRUCTION"
        },
        "गिनो": {
            "mundari_text": "लेकापे",
            "phonetic": "lekape",
            "root": "लेका",
            "meaning_hi": "गिनती करें",
            "context": "FLN_CLASSROOM_INSTRUCTION"
        },
        "गिनिए": {
            "mundari_text": "लेकापे",
            "phonetic": "lekape",
            "root": "लेका",
            "meaning_hi": "गिनती करें",
            "context": "FLN_CLASSROOM_INSTRUCTION"
        },
        "लिखो": {
            "mundari_text": "ओलपे",
            "phonetic": "olpe",
            "root": "ओल",
            "meaning_hi": "लिखिए",
            "context": "FLN_CLASSROOM_INSTRUCTION"
        },
        "पढ़ो": {
            "mundari_text": "पाड़ावपे",
            "phonetic": "parawpe",
            "root": "पाड़ाव",
            "meaning_hi": "पढ़िए",
            "context": "FLN_CLASSROOM_INSTRUCTION"
        },
        "सुनो": {
            "mundari_text": "आयूमपे",
            "phonetic": "ayumpe",
            "root": "आयूम",
            "meaning_hi": "सुनिए / ध्यान दीजिए",
            "context": "FLN_CLASSROOM_INSTRUCTION"
        },
        "शाबाश": {
            "mundari_text": "खूब बुगीन",
            "phonetic": "khub bugin",
            "root": "बुगी",
            "meaning_hi": "बहुत अच्छा",
            "context": "FLN_CLASSROOM_PRAISE"
        },
        "बहुत अच्छा": {
            "mundari_text": "खूब बुगीन",
            "phonetic": "khub bugin",
            "root": "बुगी",
            "meaning_hi": "बहुत अच्छा",
            "context": "FLN_CLASSROOM_PRAISE"
        }
    }

    def __init__(
        self,
        registry_path: Optional[str] = None,
        corpus_tsv_path: Optional[str] = None,
        phrasebook_path: Optional[str] = None,
        similarity_threshold: float = 0.55,
        enable_neural: bool = False,
        neural_checkpoint_path: Optional[str] = None,
        neural_tokenizer_dir: Optional[str] = None
    ):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        if not os.path.exists(os.path.join(base_dir, "content")):
            base_dir = _proj_dir

        self.base_dir = base_dir
        self.registry_path = registry_path or os.path.join(base_dir, "content", "content_registry.json")
        
        # Check expanded phrasebook first, fallback to base phrasebook
        expanded_pb = os.path.join(base_dir, "content", "translations", "classroom_phrases_expanded.json")
        default_pb = os.path.join(base_dir, "content", "translations", "classroom_phrasebook.json")
        if phrasebook_path:
            self.phrasebook_path = phrasebook_path
        elif os.path.exists(expanded_pb):
            self.phrasebook_path = expanded_pb
        else:
            self.phrasebook_path = default_pb

        merged_corpus = os.path.join(base_dir, "data", "processed", "nmt_merged", "all_pairs.tsv")
        default_corpus = merged_corpus if os.path.exists(merged_corpus) else os.path.join(base_dir, "data", "raw", "translation", "translation-hi-unr.tsv")
        self.corpus_tsv_path = corpus_tsv_path or default_corpus
        self.similarity_threshold = similarity_threshold

        # 1. Load Tier 1 Educational Registry (Bidirectional)
        self.educational_lookup: Dict[str, Dict[str, Any]] = {}
        self.reverse_educational_lookup: Dict[str, Dict[str, Any]] = {}
        self._load_tier1_registry()

        # 2. Load Tier 3 Parallel Corpus (Bidirectional Fallback)
        self.hindi_corpus: List[str] = []
        self.mundari_corpus: List[str] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.corpus_matrix = None
        self.reverse_vectorizer: Optional[TfidfVectorizer] = None
        self.reverse_corpus_matrix = None
        self._corpus_exact_map_hi: Dict[str, int] = {}
        self._corpus_exact_map_unr: Dict[str, int] = {}
        self._load_tier2_corpus()

        # 3. Load Tier 2 Neural Machine Translation Model
        self.enable_neural = enable_neural
        final_ckpt = os.path.join(base_dir, "models", "nmt", "final", "best_transformer.pt")
        full_corpus_ckpt = os.path.join(base_dir, "models", "nmt", "checkpoints_full_corpus", "best_transformer.pt")
        standard_ckpt = os.path.join(base_dir, "models", "nmt", "checkpoints", "best_transformer.pt")
        default_ckpt = final_ckpt if os.path.exists(final_ckpt) else (full_corpus_ckpt if os.path.exists(full_corpus_ckpt) else standard_ckpt)
        self.neural_checkpoint_path = neural_checkpoint_path or default_ckpt
        self.neural_tokenizer_dir = neural_tokenizer_dir or os.path.join(base_dir, "models", "nmt", "tokenizer")
        self.neural_engine = None
        if self.enable_neural:
            self._load_neural_engine()

    def _load_neural_engine(self) -> None:
        """Loads neural Seq2Seq Transformer model for generative Hindi -> Mundari translation."""
        if os.path.exists(self.neural_checkpoint_path) and os.path.exists(self.neural_tokenizer_dir):
            try:
                from ai.ml_translation.inference import NeuralTranslationEngine
                self.neural_engine = NeuralTranslationEngine(
                    checkpoint_path=self.neural_checkpoint_path,
                    tokenizer_dir=self.neural_tokenizer_dir,
                    device="cpu"
                )
                print(f"[TranslationEngine] NeuralTranslationEngine (Tier 2) initialized successfully from: {self.neural_checkpoint_path}")
            except Exception as e:
                print(f"[TranslationEngine] Notice: NeuralTranslationEngine not initialized: {e}")


    def _normalize_text(self, text: str) -> str:
        """Standardizes Hindi text: removes punctuation, trims, collapses whitespace."""
        return normalize_hindi(text)

    def _normalize_for_lookup(self, text: str) -> str:
        """Deep normalization equating anusvara/chandrabindu and numeral spellings."""
        return normalize_for_lookup(text)

    def _load_tier1_registry(self) -> None:
        """Loads canonical 1-20 numbers and phrasebook into fast lookup table."""
        # A. Numbers 1 to 20
        if os.path.exists(self.registry_path):
            with open(self.registry_path, "r", encoding="utf-8") as f:
                reg_data = json.load(f)

            for item in reg_data.get("items", []):
                val_data = {
                    "number": item["number"],
                    "class_index": item["class_index"],
                    "label_id": item["label_id"],
                    "hindi_numeral": item["hindi_numeral"],
                    "hindi_text": item["hindi_text"],
                    "mundari_numeral": item["mundari_numeral"],
                    "mundari_text": item["mundari_text"],
                    "mundari_root": item["mundari_root"],
                    "mundari_phonetic": item["mundari_phonetic"],
                    "variants": item.get("variants_attested", []),
                    "audio_asset": item["audio_asset"],
                    "audio_status": item["audio_status"],
                    "flashcard_asset": item["flashcard_asset"],
                    "nipun_competency_code": item.get("nipun_competency_code", "UNVERIFIED"),
                    "learning_outcome": item.get("learning_outcome", ""),
                    "category": "FLN_GRADE1_NUMBER",
                    "provenance": "OFFLINE_CONTENT_REGISTRY"
                }

                num_str = str(item["number"])
                hi_word = item["hindi_text"]
                norm_hi = self._normalize_text(hi_word)
                lookup_hi = self._normalize_for_lookup(hi_word)

                self.educational_lookup[num_str] = val_data
                self.educational_lookup[item["hindi_numeral"].strip()] = val_data
                self.educational_lookup[norm_hi] = val_data
                self.educational_lookup[lookup_hi] = val_data

                # Explicitly register orthographic variants
                if "पाँच" in (norm_hi, hi_word) or "पांच" in (lookup_hi, hi_word):
                    self.educational_lookup["पाँच"] = val_data
                    self.educational_lookup["पांच"] = val_data
                if "छह" in (norm_hi, hi_word):
                    self.educational_lookup["छः"] = val_data
                    self.educational_lookup["छ:"] = val_data
                    self.educational_lookup["छ"] = val_data
                if "पंद्रह" in (norm_hi, lookup_hi):
                    self.educational_lookup["पंद्रह"] = val_data
                    self.educational_lookup["पन्द्रह"] = val_data
                if "अठारह" in (norm_hi, lookup_hi):
                    self.educational_lookup["अठारह"] = val_data
                    self.educational_lookup["अट्ठारह"] = val_data

                for v in item.get("variants_attested", []):
                    self.educational_lookup[self._normalize_text(v)] = val_data
                    self.educational_lookup[self._normalize_for_lookup(v)] = val_data

                # Reverse lookup mapping (Mundari -> Hindi)
                mun_norm = self._normalize_text(item["mundari_text"])
                mun_lookup = self._normalize_for_lookup(item["mundari_text"])
                self.reverse_educational_lookup[mun_norm] = val_data
                self.reverse_educational_lookup[mun_lookup] = val_data

                if mun_norm.endswith("िया"):
                    self.reverse_educational_lookup[mun_norm[:-3] + "िआ"] = val_data
                elif mun_norm.endswith("िआ"):
                    self.reverse_educational_lookup[mun_norm[:-3] + "िया"] = val_data

                if item.get("mundari_root"):
                    root_norm = self._normalize_text(item["mundari_root"])
                    self.reverse_educational_lookup.setdefault(root_norm, val_data)
                if item.get("mundari_numeral"):
                    self.reverse_educational_lookup[str(item["mundari_numeral"]).strip()] = val_data
                for var in item.get("variants_attested", []):
                    var_norm = self._normalize_text(var)
                    self.reverse_educational_lookup.setdefault(var_norm, val_data)
                    self.reverse_educational_lookup.setdefault(self._normalize_for_lookup(var), val_data)
                    if var_norm.endswith("िया"):
                        self.reverse_educational_lookup.setdefault(var_norm[:-3] + "िआ", val_data)
                    elif var_norm.endswith("िआ"):
                        self.reverse_educational_lookup.setdefault(var_norm[:-3] + "िया", val_data)

            # Mundari orthographic and dialectal variants for reverse lookup
            mun_spelling_variants = {
                "मिअद": ["मिएद", "मिअद्", "मिएद्"],
                "बारिया": ["बारेया", "बारिय", "बारेय"],
                "अपिया": ["अपिए", "अपिय"],
                "उपुनिया": ["उपूनिया", "उपुनिए"],
                "मोड़ेया": ["मोड़े", "मोड़ोया"],
                "तुरिया": ["तुरिए", "तुरूय", "तुरूइ"],
                "एयाएया": ["एया", "एयाए"],
                "इरालिया": ["इरालिय", "इराल"],
                "अरेया": ["अरेय", "अरे", "आरेया"],
                "गेलेया": ["गेल", "गेले", "गेलिया"],
                "हिसि": ["मिअद हिसि", "मिएद हिसि"]
            }
            for canon_mun, variants in mun_spelling_variants.items():
                if canon_mun in self.reverse_educational_lookup:
                    vdata = self.reverse_educational_lookup[canon_mun]
                    for v in variants:
                        self.reverse_educational_lookup[self._normalize_text(v)] = vdata
                        self.reverse_educational_lookup[self._normalize_for_lookup(v)] = vdata

        # B. Classroom Phrasebook from JSON (expanded or base)
        if os.path.exists(self.phrasebook_path):
            try:
                with open(self.phrasebook_path, "r", encoding="utf-8") as f:
                    pb_data = json.load(f)
                for item in pb_data.get("phrases", []):
                    phrase_entry = {
                        "phrase_id": item.get("phrase_id"),
                        "hindi_text": item["hindi_text"],
                        "mundari_text": item["mundari_text"],
                        "mundari_phonetic": item.get("mundari_phonetic", ""),
                        "mundari_root": item.get("mundari_root", ""),
                        "category": item.get("category", "FLN_CLASSROOM_INTERACTION"),
                        "verification_level": item.get("verification_level", "CORPUS_ATTESTED"),
                        "context": item.get("context", ""),
                        "provenance": item.get("provenance", "OFFLINE_PHRASEBOOK"),
                        "audio_asset": item.get("audio_asset"),
                        "audio_status": item.get("audio_status", "NOT_PRE_RECORDED")
                    }
                    norm_hi = self._normalize_text(item["hindi_text"])
                    lookup_hi = self._normalize_for_lookup(item["hindi_text"])
                    self.educational_lookup[norm_hi] = phrase_entry
                    self.educational_lookup[lookup_hi] = phrase_entry
                    for variant in item.get("hindi_variants", []):
                        self.educational_lookup[self._normalize_text(variant)] = phrase_entry
                        self.educational_lookup[self._normalize_for_lookup(variant)] = phrase_entry

                    # Reverse lookup mapping: exact full phrase takes precedence
                    norm_pb_mun = self._normalize_text(item["mundari_text"])
                    lookup_pb_mun = self._normalize_for_lookup(item["mundari_text"])
                    self.reverse_educational_lookup.setdefault(norm_pb_mun, phrase_entry)
                    self.reverse_educational_lookup.setdefault(lookup_pb_mun, phrase_entry)

                    if item.get("mundari_root"):
                        norm_pb_root = self._normalize_text(item["mundari_root"])
                        self.reverse_educational_lookup.setdefault(norm_pb_root, phrase_entry)
            except Exception as e:
                print(f"Notice: Failed to load phrasebook from {self.phrasebook_path}: {e}")

        # C. Fallback / Built-in Classroom Phrasebook
        for phrase, pdata in self.EDUCATIONAL_PHRASEBOOK.items():
            norm_phrase = self._normalize_text(phrase)
            lookup_phrase = self._normalize_for_lookup(phrase)
            entry = {
                "hindi_text": phrase,
                "mundari_text": pdata["mundari_text"],
                "mundari_phonetic": pdata["phonetic"],
                "mundari_root": pdata["root"],
                "category": pdata["context"],
                "meaning_hi": pdata["meaning_hi"],
                "verification_level": "CORPUS_ATTESTED",
                "provenance": "BUILTIN_EDUCATIONAL_PHRASEBOOK"
            }
            if norm_phrase not in self.educational_lookup:
                self.educational_lookup[norm_phrase] = entry
            if lookup_phrase not in self.educational_lookup:
                self.educational_lookup[lookup_phrase] = entry

            norm_mun = self._normalize_text(pdata["mundari_text"])
            lookup_mun = self._normalize_for_lookup(pdata["mundari_text"])
            self.reverse_educational_lookup.setdefault(norm_mun, entry)
            self.reverse_educational_lookup.setdefault(lookup_mun, entry)

        # D. Verified Educational Vocabulary from Team Dataset (Cleaned & Validated)
        team_pairs_path = os.path.join(self.base_dir, "data", "custom", "cleaned_team_pairs.jsonl")
        if os.path.exists(team_pairs_path):
            try:
                with open(team_pairs_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        item = json.loads(line)
                        status = item.get("promotion_status") or item.get("validation_status")
                        if item.get("training_eligible") and status in ("APPROVED_TRAINING_PAIR", "LOANWORD_CORROBORATED"):
                            hi_text = item.get("hindi", "").strip()
                            mun_text = item.get("mundari", "").strip()
                            img_path = item.get("image_path") or (item.get("image_metadata") or {}).get("resolved_disk_path")
                            if hi_text and mun_text:
                                entry = {
                                    "hindi_text": hi_text,
                                    "mundari_text": mun_text,
                                    "mundari_phonetic": item.get("phonetic", ""),
                                    "mundari_root": item.get("root", mun_text),
                                    "category": item.get("category", "FLN_VOCABULARY"),
                                    "verification_level": status,
                                    "provenance": "TEAM_EDUCATIONAL_DATASET",
                                    "source": item.get("provenance", "SIH_CUSTOM_DATASET"),
                                    "image_path": img_path,
                                    "audio_asset": None,
                                    "audio_status": "NOT_PRE_RECORDED"
                                }
                                norm_hi = self._normalize_text(hi_text)
                                lookup_hi = self._normalize_for_lookup(hi_text)
                                self.educational_lookup.setdefault(norm_hi, entry)
                                self.educational_lookup.setdefault(lookup_hi, entry)

                                norm_mun = self._normalize_text(mun_text)
                                lookup_mun = self._normalize_for_lookup(mun_text)
                                self.reverse_educational_lookup.setdefault(norm_mun, entry)
                                self.reverse_educational_lookup.setdefault(lookup_mun, entry)
            except Exception as e:
                print(f"Notice: Failed to load team pairs from {team_pairs_path}: {e}")

    def _load_tier2_corpus(self) -> None:
        """Loads parallel corpus and fits bidirectional char-wb TF-IDF vectorizers."""
        if not os.path.exists(self.corpus_tsv_path):
            return

        with open(self.corpus_tsv_path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                parts = line.strip().split("\t")
                if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                    hi_sent = parts[0].strip()
                    unr_sent = parts[1].strip()
                    self.hindi_corpus.append(hi_sent)
                    self.mundari_corpus.append(unr_sent)

                    # Build fast exact match dictionaries
                    norm_hi = self._normalize_text(hi_sent)
                    lookup_hi = self._normalize_for_lookup(hi_sent)
                    if norm_hi not in self._corpus_exact_map_hi:
                        self._corpus_exact_map_hi[norm_hi] = len(self.hindi_corpus) - 1
                    if lookup_hi not in self._corpus_exact_map_hi:
                        self._corpus_exact_map_hi[lookup_hi] = len(self.hindi_corpus) - 1

                    norm_unr = self._normalize_text(unr_sent)
                    lookup_unr = self._normalize_for_lookup(unr_sent)
                    if norm_unr not in self._corpus_exact_map_unr:
                        self._corpus_exact_map_unr[norm_unr] = len(self.mundari_corpus) - 1
                    if lookup_unr not in self._corpus_exact_map_unr:
                        self._corpus_exact_map_unr[lookup_unr] = len(self.mundari_corpus) - 1

        if self.hindi_corpus and self.mundari_corpus:
            # Character n-grams with word boundary (2 to 4 chars) handles Indian language morphology
            self.vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=2)
            self.corpus_matrix = self.vectorizer.fit_transform(self.hindi_corpus)

            # Reverse vectorizer for Mundari -> Hindi retrieval
            self.reverse_vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=2)
            self.reverse_corpus_matrix = self.reverse_vectorizer.fit_transform(self.mundari_corpus)

    def translate(self, text: str, direction: str = "hi-unr", use_neural: Optional[bool] = None) -> TranslationResult:
        """
        Translates input text between Hindi and Mundari.
        direction: 'hi-unr' (Hindi -> Mundari, default) or 'unr-hi' (Mundari -> Hindi).
        use_neural: Override flag for Tier 2 Neural Translation Engine (defaults to self.enable_neural).
        """
        norm_dir = (direction or "hi-unr").strip().lower()
        if norm_dir in ("unr-hi", "mundari-hindi", "mun-hi", "unr_to_hi", "reverse"):
            return self.translate_mundari_to_hindi(text)
        return self.translate_hindi_to_mundari(text, use_neural=use_neural)

    def translate_hindi_to_mundari(self, text: str, use_neural: Optional[bool] = None) -> TranslationResult:
        """
        Translates Hindi input text to Mundari through the 4-Tier Architecture:
          - Tier 1: Exact Verified Educational Retrieval (100% precision, zero hallucination)
          - Tier 2: Neural Translation Model (generative Seq2Seq Transformer for unseen sentences)
          - Tier 3: Parallel Corpus Sentence Retrieval (TF-IDF similarity fallback)
          - Tier 4: Safe Out-of-Vocabulary Fallback (refusal to hallucinate on unintelligible input)
        """
        raw_input = text or ""
        norm_input = self._normalize_text(raw_input)
        lookup_key = self._normalize_for_lookup(raw_input)
        should_use_neural = use_neural if use_neural is not None else self.enable_neural

        if not norm_input and not lookup_key:
            return TranslationResult(
                status="OUT_OF_VOCABULARY_UNVERIFIED",
                confidence=0.0,
                source_text=raw_input,
                normalized_source=norm_input,
                translated_text=None,
                match_type="EMPTY_INPUT",
                provenance="NONE",
                translation_source="SAFE_FALLBACK",
                requires_validation=False,
                provenance_label="EMPTY_INPUT",
                metadata={"message": "Input is empty or whitespace"}
            )

        # -------------------------------------------------------------
        # TIER 1: Exact Verified Educational Retrieval (Zero Hallucination)
        # -------------------------------------------------------------
        match_data = self.educational_lookup.get(lookup_key) or self.educational_lookup.get(norm_input)
        if match_data is not None:
            v_level = match_data.get("verification_level", "")
            cat = match_data.get("category", "")
            if v_level == "COMPOSED_FROM_ATTESTED_FRAGMENTS":
                status = "COMPOSED_FROM_ATTESTED_FRAGMENTS"
            elif cat == "COMMON_VOCABULARY":
                status = "CORPUS_ATTESTED_VOCABULARY"
            elif cat == "IDENTITY_EXPRESSION":
                status = "CORPUS_ATTESTED_EXPRESSION"
            else:
                status = "VERIFIED_EDUCATIONAL_LOOKUP"

            match_type = "TIER_1_EXACT_EDUCATIONAL"
            provenance = match_data.get("provenance") or "OFFLINE_CONTENT_REGISTRY"
            return TranslationResult(
                status=status,
                confidence=1.0,
                source_text=raw_input,
                normalized_source=norm_input,
                translated_text=match_data["mundari_text"],
                match_type=match_type,
                provenance=provenance,
                translation_source="EDUCATIONAL_REGISTRY",
                requires_validation=False,
                provenance_label=provenance,
                metadata=match_data
            )

        # Fast exact parallel corpus match (if exact sentence is present in the 17,809 corpus)
        if lookup_key in self._corpus_exact_map_hi or norm_input in self._corpus_exact_map_hi:
            best_idx = self._corpus_exact_map_hi.get(lookup_key, self._corpus_exact_map_hi.get(norm_input))
            return TranslationResult(
                status="CORPUS_RETRIEVAL_MATCH",
                confidence=1.0,
                source_text=raw_input,
                normalized_source=norm_input,
                translated_text=self.mundari_corpus[best_idx],
                match_type="TIER_2_EXACT_CORPUS",
                provenance="KARYA_PARALLEL_CORPUS_RETRIEVAL",
                translation_source="CORPUS_RETRIEVAL",
                requires_validation=True,
                provenance_label="PARALLEL_CORPUS_EXACT_MATCH",
                metadata={
                    "matched_hindi_sentence": self.hindi_corpus[best_idx],
                    "corpus_row_index": best_idx,
                    "similarity_score": 1.0,
                    "notice": "Exact parallel corpus sentence match."
                }
            )

        # -------------------------------------------------------------
        # TIER 2: Neural Translation Model (Generative Seq2Seq Transformer)
        # -------------------------------------------------------------
        has_devanagari = bool(re.search(r'[\u0900-\u097F]', raw_input))
        neural_rejection_reasons: List[str] = []
        if should_use_neural and self.neural_engine is not None and has_devanagari:
            try:
                n_res = self.neural_engine.translate(raw_input, beam_size=3)
                if n_res.quality_gate_passed and n_res.translated_text and len(n_res.translated_text.strip()) > 0:
                    return TranslationResult(
                        status="NEURAL_TRANSLATION_GENERATED",
                        confidence=round(n_res.model_score, 4),
                        source_text=raw_input,
                        normalized_source=norm_input,
                        translated_text=n_res.translated_text,
                        match_type="TIER_2_NEURAL_GENERATED",
                        provenance="NEURAL_MODEL_ESTIMATED",
                        translation_source="NEURAL_MODEL",
                        requires_validation=True,
                        provenance_label="AI-GENERATED — REQUIRES LINGUISTIC VALIDATION",
                        ui_status=getattr(n_res, "ui_status", "AI TRANSLATION — REVIEW"),
                        metadata={
                            "model_score": n_res.model_score,
                            "score_type": "TOKEN_LIKELIHOOD (geometric mean token probability; NOT translation accuracy)",
                            "quality_gate_passed": True,
                            "latency_ms": n_res.latency_ms,
                            "tokens_generated": n_res.tokens_generated,
                            "beam_size": n_res.beam_size,
                            "audio_status": "NOT_PRE_RECORDED (Text translation only; no synthetic audio)",
                            "notice": "AI-ESTIMATED (UNVERIFIED) — Requires human native linguistic validation before classroom broadcast"
                        }
                    )
                else:
                    neural_rejection_reasons = n_res.quality_gate_reasons or ["FAILED_QUALITY_GATE"]
            except Exception as e:
                # Log and fallback gracefully to Tier 3
                neural_rejection_reasons = [f"INFERENCE_EXCEPTION: {str(e)}"]

        # -------------------------------------------------------------
        # TIER 3: Corpus Sentence Retrieval (TF-IDF Similarity Fallback)
        # -------------------------------------------------------------
        if self.vectorizer is not None and self.corpus_matrix is not None:
            q_vec = self.vectorizer.transform([norm_input])
            similarities = (self.corpus_matrix * q_vec.T).toarray().ravel()
            best_idx = int(np.argmax(similarities))
            best_sim = float(similarities[best_idx])

            # Check if normalized string matches best candidate exactly
            matched_hindi_norm = self._normalize_text(self.hindi_corpus[best_idx])
            matched_hindi_lookup = self._normalize_for_lookup(self.hindi_corpus[best_idx])
            if norm_input == matched_hindi_norm or lookup_key == matched_hindi_lookup:
                best_sim = 1.0

            if best_sim >= self.similarity_threshold:
                match_type = "TIER_2_EXACT_CORPUS" if best_sim >= self.EXACT_SIMILARITY_THRESHOLD else "TIER_2_SIMILARITY_CORPUS"
                return TranslationResult(
                    status="CORPUS_RETRIEVAL_MATCH",
                    confidence=round(best_sim, 4),
                    source_text=raw_input,
                    normalized_source=norm_input,
                    translated_text=self.mundari_corpus[best_idx],
                    match_type=match_type,
                    provenance="KARYA_PARALLEL_CORPUS_RETRIEVAL",
                    translation_source="CORPUS_RETRIEVAL",
                    requires_validation=True,
                    provenance_label="PARALLEL_CORPUS_RETRIEVAL",
                    metadata={
                        "matched_hindi_sentence": self.hindi_corpus[best_idx],
                        "corpus_row_index": best_idx,
                        "similarity_score": round(best_sim, 4),
                        "notice": "Corpus sentence retrieval match; not a trained translation model.",
                        "fallback_from_neural": bool(neural_rejection_reasons),
                        "neural_rejection_reasons": neural_rejection_reasons
                    }
                )
            else:
                return TranslationResult(
                    status="OUT_OF_VOCABULARY_UNVERIFIED",
                    confidence=round(best_sim, 4),
                    source_text=raw_input,
                    normalized_source=norm_input,
                    translated_text=None,
                    match_type="BELOW_CONFIDENCE_THRESHOLD",
                    provenance="NONE",
                    translation_source="SAFE_FALLBACK",
                    requires_validation=False,
                    provenance_label="UNATTESTED_INPUT_SAFE_FALLBACK",
                    metadata={
                        "best_similarity": round(best_sim, 4),
                        "threshold": self.similarity_threshold,
                        "top_unverified_candidate": self.hindi_corpus[best_idx] if best_sim > 0 else None,
                        "message": (
                            f"Neural model rejected low-confidence or ungrounded generation ({', '.join(neural_rejection_reasons)}). "
                            f"Parallel corpus similarity ({round(best_sim, 3)}) is below threshold ({self.similarity_threshold}). "
                            "Refusing to hallucinate unverified translation."
                        ) if neural_rejection_reasons else "Similarity below confidence threshold. Refusing to hallucinate.",
                        "fallback_from_neural": bool(neural_rejection_reasons),
                        "neural_rejection_reasons": neural_rejection_reasons
                    }
                )

        # -------------------------------------------------------------
        # TIER 4: Safe Out of Vocabulary Fallback
        # -------------------------------------------------------------
        return TranslationResult(
            status="OUT_OF_VOCABULARY_UNVERIFIED",
            confidence=0.0,
            source_text=raw_input,
            normalized_source=norm_input,
            translated_text=None,
            match_type="NO_CORPUS_LOADED",
            provenance="NONE",
            translation_source="SAFE_FALLBACK",
            requires_validation=False,
            provenance_label="UNATTESTED_INPUT_SAFE_FALLBACK",
            metadata={"message": "Corpus data not available"}
        )


    def translate_mundari_to_hindi(self, text: str) -> TranslationResult:
        """
        Translates Mundari input text to Hindi (Reverse Pipeline).
        Executes Tier 1 exact reverse educational lookup first.
        Falls back to Tier 2 TF-IDF reverse corpus similarity search if unmapped.
        Rejects low-confidence matches as OUT_OF_VOCABULARY_UNVERIFIED.
        """
        raw_input = text or ""
        norm_input = self._normalize_text(raw_input)
        lookup_key = self._normalize_for_lookup(raw_input)

        if not norm_input and not lookup_key:
            return TranslationResult(
                status="OUT_OF_VOCABULARY_UNVERIFIED",
                confidence=0.0,
                source_text=raw_input,
                normalized_source=norm_input,
                translated_text=None,
                match_type="EMPTY_INPUT",
                provenance="NONE",
                metadata={"message": "Input is empty or whitespace"}
            )

        # -------------------------------------------------------------
        # TIER 1: Exact Verified Educational Retrieval (Reverse Direction)
        # -------------------------------------------------------------
        match_data = self.reverse_educational_lookup.get(lookup_key) or self.reverse_educational_lookup.get(norm_input)
        if match_data is not None:
            v_level = match_data.get("verification_level", "")
            cat = match_data.get("category", "")
            if v_level == "COMPOSED_FROM_ATTESTED_FRAGMENTS":
                status = "COMPOSED_FROM_ATTESTED_FRAGMENTS"
            elif cat == "COMMON_VOCABULARY":
                status = "CORPUS_ATTESTED_VOCABULARY"
            elif cat == "IDENTITY_EXPRESSION":
                status = "CORPUS_ATTESTED_EXPRESSION"
            else:
                status = "VERIFIED_EDUCATIONAL_LOOKUP"

            match_type = "TIER_1_EXACT_EDUCATIONAL"
            provenance = match_data.get("provenance") or "OFFLINE_CONTENT_REGISTRY"
            return TranslationResult(
                status=status,
                confidence=1.0,
                source_text=raw_input,
                normalized_source=norm_input,
                translated_text=match_data["hindi_text"],
                match_type=match_type,
                provenance=provenance,
                translation_source="EDUCATIONAL_REGISTRY",
                requires_validation=False,
                provenance_label=provenance,
                metadata=match_data
            )

        # -------------------------------------------------------------
        # TIER 2: Reverse Corpus Sentence Retrieval (TF-IDF Similarity)
        # -------------------------------------------------------------
        # A. Check fast exact corpus match
        if lookup_key in self._corpus_exact_map_unr or norm_input in self._corpus_exact_map_unr:
            best_idx = self._corpus_exact_map_unr.get(lookup_key, self._corpus_exact_map_unr.get(norm_input))
            return TranslationResult(
                status="CORPUS_RETRIEVAL_MATCH",
                confidence=1.0,
                source_text=raw_input,
                normalized_source=norm_input,
                translated_text=self.hindi_corpus[best_idx],
                match_type="TIER_2_EXACT_CORPUS",
                provenance="KARYA_PARALLEL_CORPUS_RETRIEVAL",
                translation_source="CORPUS_RETRIEVAL",
                requires_validation=True,
                provenance_label="PARALLEL_CORPUS_EXACT_MATCH",
                metadata={
                    "matched_mundari_sentence": self.mundari_corpus[best_idx],
                    "corpus_row_index": best_idx,
                    "similarity_score": 1.0,
                    "notice": "Exact parallel corpus sentence match."
                }
            )

        # B. TF-IDF character n-gram similarity search
        if self.reverse_vectorizer is not None and self.reverse_corpus_matrix is not None:
            q_vec = self.reverse_vectorizer.transform([norm_input])
            similarities = (self.reverse_corpus_matrix * q_vec.T).toarray().ravel()
            best_idx = int(np.argmax(similarities))
            best_sim = float(similarities[best_idx])

            matched_unr_norm = self._normalize_text(self.mundari_corpus[best_idx])
            matched_unr_lookup = self._normalize_for_lookup(self.mundari_corpus[best_idx])
            if norm_input == matched_unr_norm or lookup_key == matched_unr_lookup:
                best_sim = 1.0

            if best_sim >= self.similarity_threshold:
                match_type = "TIER_2_EXACT_CORPUS" if best_sim >= self.EXACT_SIMILARITY_THRESHOLD else "TIER_2_SIMILARITY_CORPUS"
                return TranslationResult(
                    status="CORPUS_RETRIEVAL_MATCH",
                    confidence=round(best_sim, 4),
                    source_text=raw_input,
                    normalized_source=norm_input,
                    translated_text=self.hindi_corpus[best_idx],
                    match_type=match_type,
                    provenance="KARYA_PARALLEL_CORPUS_RETRIEVAL",
                    translation_source="CORPUS_RETRIEVAL",
                    requires_validation=True,
                    provenance_label="PARALLEL_CORPUS_RETRIEVAL",
                    metadata={
                        "matched_mundari_sentence": self.mundari_corpus[best_idx],
                        "corpus_row_index": best_idx,
                        "similarity_score": round(best_sim, 4),
                        "notice": "Corpus sentence retrieval match; not a trained translation model."
                    }
                )
            else:
                return TranslationResult(
                    status="OUT_OF_VOCABULARY_UNVERIFIED",
                    confidence=round(best_sim, 4),
                    source_text=raw_input,
                    normalized_source=norm_input,
                    translated_text=None,
                    match_type="BELOW_CONFIDENCE_THRESHOLD",
                    provenance="NONE",
                    translation_source="SAFE_FALLBACK",
                    requires_validation=False,
                    provenance_label="UNATTESTED_INPUT_SAFE_FALLBACK",
                    metadata={
                        "best_similarity": round(best_sim, 4),
                        "threshold": self.similarity_threshold,
                        "top_unverified_candidate": self.mundari_corpus[best_idx] if best_sim > 0 else None,
                        "message": "Similarity below confidence threshold. Refusing to hallucinate."
                    }
                )

        # Fallback if corpus not available
        return TranslationResult(
            status="OUT_OF_VOCABULARY_UNVERIFIED",
            confidence=0.0,
            source_text=raw_input,
            normalized_source=norm_input,
            translated_text=None,
            match_type="NO_CORPUS_LOADED",
            provenance="NONE",
            translation_source="SAFE_FALLBACK",
            requires_validation=False,
            provenance_label="UNATTESTED_INPUT_SAFE_FALLBACK",
            metadata={"message": "Corpus data not available"}
        )



if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    engine = TranslationEngine()
    print("Translation Engine Initialized.")

    test_queries = [
        "पाँच", "पांच", "छ:", "छः", "छह", "पन्द्रह", "पंद्रह",
        "5", "१४", "नमस्ते", "बैठो", "खड़े हो जाओ", "किताब खोलो",
        "गिनो", "लिखो", "पढ़ो", "बहुत अच्छा",
        "हेलो", "नमस्ते बच्चों", "सभी किताब खोलो", "मेरा नाम",
        "पानी के फव्वारों को हफ्ते में एक दिन सुखा दें।",
        "घर बार सब जल उठा।",
        "क्वांटम कंप्यूटिंग अल्गोरिदम"
    ]

    for q in test_queries:
        res = engine.translate(q)
        print(f"\nQuery: '{q}'")
        print(f"  Status: {res.status} (Confidence: {res.confidence})")
        print(f"  Match Type: {res.match_type}")
        print(f"  Translation: {res.translated_text}")
