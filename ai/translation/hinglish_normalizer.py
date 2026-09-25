"""
ai/translation/hinglish_normalizer.py
=============================================================================
SIH260042: Governed Hinglish (Latin-Script Hindi) Text Normalizer
=============================================================================
Transforms Romanized/Hinglish classroom utterances into standardized Devanagari
Hindi representations for downstream consumption by the existing Hindi -> Mundari
translation engine.

Design Principles:
1. Grounded in Governed Data: Uses data/approved/hinglish/governed_hinglish_lexicon.json.
2. Longest-Match-First Phrase Normalization: Handles multi-word idioms and commands
   (e.g., "kitab kholo", "namaste bachcho", "khade ho jao") before word-level checks.
3. Spelling & Phonetic Variant Resilience: Handles common transliteration variations
   (e.g., "baitho" / "betho", "panch" / "paanch", "accha" / "achha").
4. Strict Anti-Hallucination & Ambiguity Safety:
   - Unattested words (e.g. "xyzrandom") are preserved as raw Latin tokens without
     fabricating synthetic Devanagari.
   - Ambiguous words (e.g. "kal" = yesterday vs. tomorrow) trigger lower confidence
     and explicit status metadata.
=============================================================================
"""

import os
import re
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set


@dataclass
class HinglishNormalizationResult:
    """Structured result returned by the Hinglish normalizer."""
    original_text: str
    normalized_hindi: str
    status: str  # EXACT_MATCH, RULE_NORMALIZED, PARTIAL, UNRESOLVED, AMBIGUOUS
    confidence: float
    tokens_mapped: List[Tuple[str, str]] = field(default_factory=list)
    unmapped_tokens: List[str] = field(default_factory=list)
    notes: str = ""

    @property
    def is_fully_normalized(self) -> bool:
        return self.status in ("EXACT_MATCH", "RULE_NORMALIZED") and len(self.unmapped_tokens) == 0


class HinglishNormalizer:
    """
    Deterministic transliteration and normalization layer converting Hinglish into
    standardized Devanagari Hindi.
    """

    def __init__(self, lexicon_path: Optional[str] = None):
        if not lexicon_path:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            lexicon_path = os.path.join(base_dir, "data", "approved", "hinglish", "governed_hinglish_lexicon.json")

        self.lexicon_path = lexicon_path
        self.phrase_map: Dict[str, Dict[str, str]] = {}
        self.word_map: Dict[str, Dict[str, str]] = {}
        self.ambiguous_tokens: Set[str] = set()

        self._load_lexicon()

    def _load_lexicon(self) -> None:
        """Loads and indexes the governed Hinglish lexicon."""
        if not os.path.exists(self.lexicon_path):
            return

        try:
            with open(self.lexicon_path, "r", encoding="utf-8") as f:
                entries = json.load(f)

            for entry in entries:
                h_key = entry.get("hinglish", "").strip().lower()
                if not h_key:
                    continue

                if entry.get("category") == "AMBIGUOUS" or entry.get("status") == "HELD_FOR_REVIEW":
                    self.ambiguous_tokens.add(h_key)

                # Split into phrases (>1 token) vs single words
                tokens = h_key.split()
                if len(tokens) > 1:
                    self.phrase_map[h_key] = entry
                else:
                    self.word_map[h_key] = entry

        except Exception as e:
            # Fallback gracefully
            print(f"[HinglishNormalizer] Warning: Could not load lexicon at {self.lexicon_path}: {e}")

    @staticmethod
    def _clean_input(text: str) -> str:
        """Lowercases, normalizes whitespace and standardizes common punctuation."""
        if not text:
            return ""
        # Strip extraneous punctuation characters but preserve spaces
        cleaned = re.sub(r"[^\w\s\u0900-\u097F]", " ", str(text).lower())
        return re.sub(r"\s+", " ", cleaned).strip()

    @staticmethod
    def _phonetic_key(word: str) -> str:
        """Generates a simplified phonetic key to catch common vowel/consonant variations."""
        k = word.lower()
        k = k.replace("aa", "a").replace("ee", "i").replace("oo", "u")
        k = k.replace("chh", "ch").replace("sh", "s").replace("th", "t")
        k = k.replace("ph", "f").replace("w", "v")
        # Collapse repeated consonants (e.g. bachcho -> bacho, attharah -> atharah)
        k = re.sub(r"(.)\1+", r"\1", k)
        return k

    def normalize(self, text: str) -> HinglishNormalizationResult:
        """
        Normalizes a Hinglish input string into Devanagari Hindi text.
        """
        cleaned = self._clean_input(text)
        if not cleaned:
            return HinglishNormalizationResult(
                original_text=text or "",
                normalized_hindi="",
                status="EMPTY_INPUT",
                confidence=0.0,
                notes="Input string is empty."
            )

        # 1. Direct multi-word phrase match (greedy exact match on whole input)
        if cleaned in self.phrase_map:
            entry = self.phrase_map[cleaned]
            return HinglishNormalizationResult(
                original_text=text,
                normalized_hindi=entry["hindi"],
                status="EXACT_MATCH",
                confidence=1.0,
                tokens_mapped=[(cleaned, entry["hindi"])],
                notes=f"Attested phrase match: {entry.get('source', '')}"
            )

        # 2. Direct single-word exact match
        if cleaned in self.word_map:
            entry = self.word_map[cleaned]
            if cleaned in self.ambiguous_tokens:
                return HinglishNormalizationResult(
                    original_text=text,
                    normalized_hindi=entry["hindi"],
                    status="AMBIGUOUS",
                    confidence=0.5,
                    tokens_mapped=[(cleaned, entry["hindi"])],
                    notes="Ambiguous input with multiple senses (held for contextual review)."
                )
            return HinglishNormalizationResult(
                original_text=text,
                normalized_hindi=entry["hindi"],
                status="EXACT_MATCH",
                confidence=1.0,
                tokens_mapped=[(cleaned, entry["hindi"])],
                notes=f"Attested word match: {entry.get('source', '')}"
            )

        # 3. Check phonetic key across word map
        input_phonetic = self._phonetic_key(cleaned)
        for w_key, entry in self.word_map.items():
            if self._phonetic_key(w_key) == input_phonetic:
                return HinglishNormalizationResult(
                    original_text=text,
                    normalized_hindi=entry["hindi"],
                    status="RULE_NORMALIZED",
                    confidence=0.95,
                    tokens_mapped=[(cleaned, entry["hindi"])],
                    notes=f"Phonetic variation resolved to {w_key} ({entry['hindi']})"
                )

        # 4. Multi-token sequential normalization (Greedy phrase + token sliding window)
        tokens = cleaned.split()
        normalized_words: List[str] = []
        tokens_mapped: List[Tuple[str, str]] = []
        unmapped_tokens: List[str] = []
        i = 0
        n = len(tokens)
        has_ambiguous = False

        while i < n:
            matched = False

            # Try multi-word subphrases (lengths 4, 3, 2)
            for length in range(min(4, n - i), 1, -1):
                subphrase = " ".join(tokens[i:i + length])
                if subphrase in self.phrase_map:
                    target_hi = self.phrase_map[subphrase]["hindi"]
                    normalized_words.append(target_hi)
                    tokens_mapped.append((subphrase, target_hi))
                    i += length
                    matched = True
                    break

            if matched:
                continue

            # Single token lookup
            curr_token = tokens[i]
            if re.match(r"^__name_\d+__$", curr_token, re.IGNORECASE):
                # Preserved proper name placeholder (e.g. __NAME_0__)
                placeholder = curr_token.upper()
                normalized_words.append(placeholder)
                tokens_mapped.append((curr_token, placeholder))
            elif curr_token in self.word_map:
                entry = self.word_map[curr_token]
                if curr_token in self.ambiguous_tokens:
                    has_ambiguous = True
                target_hi = entry["hindi"]
                normalized_words.append(target_hi)
                tokens_mapped.append((curr_token, target_hi))
            else:
                # Check phonetic match for single token
                curr_phonetic = self._phonetic_key(curr_token)
                found_phonetic = False
                for w_key, entry in self.word_map.items():
                    if self._phonetic_key(w_key) == curr_phonetic:
                        target_hi = entry["hindi"]
                        normalized_words.append(target_hi)
                        tokens_mapped.append((curr_token, target_hi))
                        found_phonetic = True
                        break

                if not found_phonetic:
                    # Unknown word: PRESERVE WITHOUT HALLUCINATION
                    normalized_words.append(curr_token)
                    unmapped_tokens.append(curr_token)

            i += 1

        # Synthesize overall status and confidence
        normalized_str = " ".join(normalized_words)
        if len(unmapped_tokens) == 0:
            if has_ambiguous:
                status = "AMBIGUOUS"
                conf = 0.6
            else:
                status = "RULE_NORMALIZED"
                conf = 0.95
        elif len(tokens_mapped) > 0:
            status = "PARTIAL"
            conf = round(len(tokens_mapped) / n, 2) * 0.8
        else:
            status = "UNRESOLVED"
            conf = 0.0

        return HinglishNormalizationResult(
            original_text=text,
            normalized_hindi=normalized_str,
            status=status,
            confidence=conf,
            tokens_mapped=tokens_mapped,
            unmapped_tokens=unmapped_tokens,
            notes=f"Mapped {len(tokens_mapped)} of {n} segments; unmapped: {unmapped_tokens}"
        )
