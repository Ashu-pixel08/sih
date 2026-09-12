"""
ai/translation/hindi_normalizer.py
=============================================================================
SIH260042: Unified Devanagari Hindi Text Normalizer
=============================================================================
Provides deterministic, standard normalization for Hindi text queries across
all translation tiers:
1. Unicode NFC normalization.
2. Strip zero-width characters (ZWJ, ZWNJ, BOM).
3. Standardize Devanagari colons / visargas (e.g. छ: -> छः -> छह).
4. Devanagari punctuation (danda ।, double danda ॥, ?, !, ,, ;, quotes, brackets).
5. Whitespace collapsing and trimming.
6. Anusvara (\u0902) and Chandrabindu (\u0901) normalization so 'पाँच' and 'पांच'
   evaluate to identical search keys.
7. Common Devanagari numeral spelling variant mappings (e.g. छह / छः / छ:, पंद्रह / पन्द्रह).
=============================================================================
"""

import re
import unicodedata
from typing import Dict

# Zero-width characters to strip
ZERO_WIDTH_PATTERN = re.compile(r"[\u200b\u200c\u200d\ufeff]")

# Punctuation regex covering standard ASCII and Indic punctuation (excluding visarga \u0903)
PUNCTUATION_PATTERN = re.compile(r"[\u0964\u0965।,!?;:\'\"\-—–()\[\]{}.\/\\*#@~`^+=<>|_]")

# Whitespace collapsing
WHITESPACE_PATTERN = re.compile(r"\s+")

# Standard numeral spelling aliases
NUMERAL_SPELLING_ALIASES: Dict[str, str] = {
    "पांच": "पाँच",
    "छ": "छह",
    "छः": "छह",
    "छ:": "छह",
    "पन्द्रह": "पंद्रह",
    "अट्ठारह": "अठारह",
    "उन्इस": "उन्नीस",
    "उनिस": "उन्नीस",
}

# Devanagari digit to word mapping
DEVANAGARI_DIGITS_TO_WORDS: Dict[str, str] = {
    "१": "एक", "२": "दो", "३": "तीन", "४": "चार", "५": "पाँच",
    "६": "छह", "७": "सात", "८": "आठ", "९": "नौ", "१०": "दस",
    "११": "ग्यारह", "१२": "बारह", "१३": "तेरह", "१४": "चौदह", "१५": "पंद्रह",
    "१६": "सोलह", "१७": "सत्रह", "१८": "अठारह", "१९": "उन्नीस", "२०": "बीस",
}

# ASCII digit to word mapping
ASCII_DIGITS_TO_WORDS: Dict[str, str] = {
    "1": "एक", "2": "दो", "3": "तीन", "4": "चार", "5": "पाँच",
    "6": "छह", "7": "सात", "8": "आठ", "9": "नौ", "10": "दस",
    "11": "ग्यारह", "12": "बारह", "13": "तेरह", "14": "चौदह", "15": "पंद्रह",
    "16": "सोलह", "17": "सत्रह", "18": "अठारह", "19": "उन्नीस", "20": "बीस",
}


def normalize_hindi(text: str) -> str:
    """
    Standard clean normalization preserving standard word tokens while removing
    superfluous punctuation, extra whitespace, and zero-width artifacts.
    """
    if not text:
        return ""

    # 1. Unicode NFC normalization
    normalized = unicodedata.normalize("NFC", str(text))

    # 2. Strip zero-width characters
    normalized = ZERO_WIDTH_PATTERN.sub("", normalized)

    # 3. Handle known shorthand like 'छ:' or 'छः' before punctuation stripping
    if normalized.strip() in ("छ:", "छः", "छ"):
        return "छह"

    # 4. Replace punctuation and Indic danda with whitespace
    normalized = PUNCTUATION_PATTERN.sub(" ", normalized)

    # 5. Collapse whitespace and trim
    normalized = WHITESPACE_PATTERN.sub(" ", normalized).strip()

    return normalized


def normalize_for_lookup(text: str) -> str:
    """
    Deep normalization for dictionary and vector lookup:
    1. Runs normalize_hindi.
    2. Equates anusvara (\u0902) and chandrabindu (\u0901) to standard anusvara.
    3. Resolves known digit strings and spelling aliases.
    """
    cleaned = normalize_hindi(text)
    if not cleaned:
        return ""

    # Check digit conversions directly
    if cleaned in ASCII_DIGITS_TO_WORDS:
        return normalize_for_lookup(ASCII_DIGITS_TO_WORDS[cleaned])
    if cleaned in DEVANAGARI_DIGITS_TO_WORDS:
        return normalize_for_lookup(DEVANAGARI_DIGITS_TO_WORDS[cleaned])

    # Check direct word spelling aliases
    if cleaned in NUMERAL_SPELLING_ALIASES:
        cleaned = NUMERAL_SPELLING_ALIASES[cleaned]

    # Unify chandrabindu (\u0901) -> anusvara (\u0902)
    unified = cleaned.replace("\u0901", "\u0902")

    # Re-check alias on unified
    if unified in NUMERAL_SPELLING_ALIASES:
        unified = NUMERAL_SPELLING_ALIASES[unified].replace("\u0901", "\u0902")

    return unified
