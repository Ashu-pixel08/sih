"""
consistency_linter.py - Non-Generative Linguistic & Structural Consistency Linter

Performs deterministic rule-based checks on candidate bilingual parallel records.
Identifies potential anomalies, typos, formatting issues, and alignment discrepancies.

IMPORTANT DISCLAIMER:
This linter is a rule-based consistency tool, NOT an artificial intelligence or native speaker.
It flags surface anomalies requiring human review or caution. It does NOT evaluate linguistic
authenticity or native fluency.
"""

import re
import unicodedata
from typing import Dict, List, Any, Optional, Set, Tuple


class ConsistencyLinter:
    """Non-generative consistency and hygiene linter for Hindi-Mundari bilingual records."""

    # Hindi number words mapped to corresponding Mundari number roots/words
    NUMBER_MAPPINGS = {
        "एक": ["मिअद", "मियद", "मिद", "मोयोद", "मोसा"],
        "दो": ["बारिया", "बरिया", "बार", "बर", "बरन"],
        "तीन": ["आपि", "अपिया", "पे", "पिया"],
        "चार": ["उपून", "उपुनिया", "पून", "पुनिया"],
        "चौथी": ["उपुनिया", "उपून"],
        "पांच": ["मोणे", "मोड़े"],
        "छह": ["तुरुइ"],
        "सात": ["एया"],
        "आठ": ["इरिल"],
        "नौ": ["आरे"],
        "दस": ["गेल", "गेलिया"],
        "दसवीं": ["गेल", "गेलसा:", "गेलिया"]
    }

    # Established Mundari reference vocabulary roots for glossary consistency
    KNOWN_MUNDARI_LEXICON = {
        "ओड़अ:", "ओड़ाः", "गोमके", "जीव", "पेड़े:", "पेड़ेजान", "हुलांग", "सिरमा",
        "दिया", "इड़िंग", "इड़िं:", "इंड़ी", "कुड़ाम", "होयो", "मोचा", "रिमिल",
        "गमा", "हाई", "हाईको", "हाईकोअ:", "दअ:", "दाः", "बोरो", "तरन", "होटो:",
        "ती:", "सिंगी", "रासिका", "चोके", "चोकेको", "चोकेकोअ:", "गति", "गतिकिन",
        "दुबपे", "तिंगुपे", "लेकापे", "ओलपे", "पाड़ावपे", "आयूमपे", "जोहार", "खूब",
        "बुगी", "बुगीन", "मियद", "मिअद", "बारिया", "उपुनिया", "गेलसा:"
    }

    # Spelling variations of verb roots observed across corpora
    KNOWN_SPELLING_VARIANTS = {
        "इड़िंग": ["इड़िं:", "इंड़ी"],
        "इड़िं:": ["इड़िंग", "इंड़ी"],
        "इंड़ी": ["इड़िंग", "इड़िं:"],
        "ओड़अ:": ["ओड़ाः", "ओड़ा"],
        "दअ:": ["दाः", "दा"],
        "ती:": ["तीः", "ती"],
        "पेड़े:": ["पेड़ेः", "पेड़े"]
    }

    @staticmethod
    def check_unicode_normalization(text: str) -> Tuple[bool, Optional[str]]:
        """Checks whether string is in Unicode NFC canonical composition form."""
        if not text:
            return True, None
        normalized = unicodedata.normalize("NFC", text)
        if text != normalized:
            return False, "Text is not in Unicode NFC form"
        return True, None

    @staticmethod
    def check_whitespace_anomalies(text: str) -> List[str]:
        """Detects leading/trailing spaces, multiple spaces, or spaces before punctuation."""
        anomalies = []
        if not text:
            return anomalies

        if text != text.strip():
            anomalies.append("Leading or trailing whitespace detected")

        if re.search(r"\s{2,}", text):
            anomalies.append("Consecutive multiple spaces detected")

        # Space preceding colon, danda, question mark, or exclamation
        if re.search(r"\s+([:!?,|।])", text):
            match = re.search(r"\s+([:!?,|।])", text)
            anomalies.append(f"Extraneous whitespace preceding punctuation '{match.group(1)}'")

        return anomalies

    @staticmethod
    def check_suspicious_punctuation(text: str) -> List[str]:
        """Detects unbalanced brackets, unclosed quotes, or stray symbols."""
        anomalies = []
        if not text:
            return anomalies

        # Unbalanced parentheses
        if text.count("(") != text.count(")"):
            anomalies.append("Unbalanced parentheses '(' and ')'")
        if text.count("[") != text.count("]"):
            anomalies.append("Unbalanced brackets '[' and ']'")
        if text.count("{") != text.count("}"):
            anomalies.append("Unbalanced curly braces '{' and '}'")

        # Double punctuation
        if re.search(r"[।?!]{2,}", text):
            anomalies.append("Multiple consecutive sentence terminators detected")

        # Parenthetical glossing detection (e.g. 'दाऊड़ा (डाली)')
        if re.search(r"\([^)]+\)", text):
            anomalies.append("Parenthetical glossing detected in text; verify if bilingual translation note")

        return anomalies

    @staticmethod
    def check_untranslated_latin_tokens(text: str) -> List[str]:
        """Flags raw Latin ASCII tokens in Devanagari corpus text."""
        anomalies = []
        if not text:
            return anomalies

        # Find Latin words
        latin_words = re.findall(r"\b[A-Za-z]{2,}\b", text)
        if latin_words:
            anomalies.append(f"Unexplained Latin ASCII tokens found in text: {latin_words}")

        return anomalies

    @staticmethod
    def check_alignment_length_ratio(hindi_text: str, mundari_text: str) -> Tuple[bool, float, Optional[str]]:
        """
        Validates character length ratio between Hindi and Mundari parallel strings.
        Normal bilingual sentence pairs typically have character length ratio between 0.25 and 4.0.
        """
        h_len = len(hindi_text.strip())
        m_len = len(mundari_text.strip())

        if h_len == 0 or m_len == 0:
            return False, 0.0, "Empty source or target string"

        ratio = round(h_len / m_len, 2)
        if ratio < 0.25 or ratio > 4.0:
            return False, ratio, f"Extreme length disparity: Hindi={h_len} chars, Mundari={m_len} chars (Ratio: {ratio})"

        return True, ratio, None

    def check_numerical_consistency(self, hindi_text: str, mundari_text: str) -> List[str]:
        """
        Verifies that numbers present in the Hindi sentence correspond to Mundari equivalents.
        """
        anomalies = []
        for hi_num, mun_roots in self.NUMBER_MAPPINGS.items():
            # Check whole word boundary for Hindi number
            pattern = rf"(?<!\w){re.escape(hi_num)}(?!\w)"
            if re.search(pattern, hindi_text):
                # Check if any corresponding Mundari root is in the Mundari text
                found = any(m_root in mundari_text for m_root in mun_roots)
                if not found:
                    anomalies.append(
                        f"Numerical divergence: Hindi contains '{hi_num}', but Mundari does not contain expected roots {mun_roots}"
                    )
        return anomalies

    def check_corpus_spelling_consistency(self, text: str) -> List[str]:
        """
        Flags whether text uses divergent spelling variants of known unstable roots.
        """
        notices = []
        for term, variants in self.KNOWN_SPELLING_VARIANTS.items():
            if term in text:
                notices.append(f"Contains root '{term}' which has known variants {variants} in corpus")
        return notices

    def check_glossary_presence(self, mundari_text: str) -> List[str]:
        """Returns verified lexicon terms found in the Mundari sentence."""
        return [term for term in self.KNOWN_MUNDARI_LEXICON if term in mundari_text]

    def lint_record(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the complete suite of non-generative consistency checks on a single record."""
        rec_id = rec.get("record_id", "UNKNOWN")
        hi_text = rec.get("hindi_text", "")
        mun_text = rec.get("mundari_text", "")

        findings = {
            "record_id": rec_id,
            "passed": True,
            "errors": [],
            "warnings": [],
            "anomalies": [],
            "metrics": {
                "hindi_char_count": len(hi_text),
                "mundari_char_count": len(mun_text),
                "length_ratio": 0.0,
                "attested_lexicon_terms": []
            }
        }

        # 1. Unicode NFC check
        for lang, txt in [("Hindi", hi_text), ("Mundari", mun_text)]:
            is_nfc, nfc_err = self.check_unicode_normalization(txt)
            if not is_nfc:
                findings["warnings"].append(f"{lang}: {nfc_err}")

        # 2. Whitespace checks
        for lang, txt in [("Hindi", hi_text), ("Mundari", mun_text)]:
            ws_errs = self.check_whitespace_anomalies(txt)
            for err in ws_errs:
                findings["warnings"].append(f"{lang}: {err}")
                findings["anomalies"].append(f"WHITESPACE: {lang} - {err}")

        # 3. Punctuation checks
        for lang, txt in [("Hindi", hi_text), ("Mundari", mun_text)]:
            punc_errs = self.check_suspicious_punctuation(txt)
            for err in punc_errs:
                findings["warnings"].append(f"{lang}: {err}")
                findings["anomalies"].append(f"PUNCTUATION: {lang} - {err}")

        # 4. Latin tokens check
        latin_errs = self.check_untranslated_latin_tokens(mun_text)
        if latin_errs:
            findings["warnings"].extend(latin_errs)
            findings["anomalies"].extend(latin_errs)

        # 5. Alignment length ratio check
        ratio_ok, ratio, ratio_msg = self.check_alignment_length_ratio(hi_text, mun_text)
        findings["metrics"]["length_ratio"] = ratio
        if not ratio_ok and ratio_msg:
            if ratio == 0.0:
                findings["errors"].append(ratio_msg)
                findings["passed"] = False
            else:
                findings["warnings"].append(ratio_msg)
                findings["anomalies"].append(f"ALIGNMENT: {ratio_msg}")

        # 6. Numerical consistency check
        num_errs = self.check_numerical_consistency(hi_text, mun_text)
        if num_errs:
            findings["warnings"].extend(num_errs)
            findings["anomalies"].extend(num_errs)

        # 7. Lexicon glossary match
        matched_lexicon = self.check_glossary_presence(mun_text)
        findings["metrics"]["attested_lexicon_terms"] = matched_lexicon

        # 8. Spelling variant tracking
        spelling_notes = self.check_corpus_spelling_consistency(mun_text)
        if spelling_notes:
            findings["anomalies"].extend(spelling_notes)

        # 9. Typo detection heuristics (e.g., 'चोकेकोअ: गाा')
        if "गाा" in mun_text and ("गमा" in hi_text or "बारिश" in hi_text):
            typo_msg = "SUSPECTED TYPO: 'गाा' found in Mundari where 'गमा' (rain) is contextually expected"
            findings["warnings"].append(typo_msg)
            findings["anomalies"].append(typo_msg)

        if findings["errors"]:
            findings["passed"] = False

        return findings
