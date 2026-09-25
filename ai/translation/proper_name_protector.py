"""
ai/translation/proper_name_protector.py
=============================================================================
SIH260042: Bhasha Setu Proper Name & Personal Name Preservation Layer
=============================================================================
ARCHITECTURAL PRINCIPLE:
In vernacular education and classroom dialogue, personal proper names
(e.g., student names like "Rahul", "Priya", "Amit", "Birsa", "Somra", "राहुल")
must NEVER be translated, normalized, transliterated across scripts, or
fragmented by subword/BPE tokenizers.

WHY PRESERVING EXACT NAMES IS CRITICAL:
1. Identity Integrity: A student's or teacher's name is not a dictionary word.
   Translating "कमल" to "Lotus" or passing "Rahul" through a Mundari neural
   model produces either OOV refusal, hallucinations, or phonetic mangling.
2. Cross-Script Respect: When a Hindi teacher addresses a student "Rahul",
   the teacher/student UI and pronunciation should honor the user's exact
   input token ("Rahul"), rather than arbitrary or flawed transliteration.
3. Zero-Hallucination Safety: Preserving names via safe placeholder spans
   prevents rare proper nouns from corrupting neural Seq2Seq attention.

PIPELINE DESIGN:
  Input Query (Hindi / Hinglish / Mundari)
               │
               ▼
   [ProperNameProtector.protect()]
   - Detects candidate personal names using contextual patterns,
     morphosyntactic anchors, and cross-script signals.
   - Shields candidate tokens with deterministic placeholders:
     __NAME_0__, __NAME_1__, ...
   - Employs strict negative vocabulary filtering (FLN numbers,
     classroom verbs, educational nouns, language names NEVER shielded).
               │
               ▼
   [Normalization & Translation Pipeline]
   - HinglishNormalizer preserves __NAME_0__ as attested token.
   - Translation Engine maps structured educational templates
     (e.g. "मेरा नाम __NAME_0__ है" -> "आञाः नुतुम __NAME_0__")
     or passes shielded text to neural/retrieval engine.
               │
               ▼
   [ProperNameProtector.restore()]
   - Drops original exact name strings back into place.
   - Performs fail-safe regex cleanup to guarantee NO placeholder
     (__NAME_X__) can ever leak to the user interface.
=============================================================================
"""

import re
from typing import Dict, List, Optional, Set, Tuple


class ProperNameProtector:
    """
    Conservative, language-independent proper name preservation layer.
    Safely shields personal names before translation and restores exact user
    strings post-translation without script alteration or semantic corruption.
    """

    # Negative Vocabulary: Words that MUST NEVER be protected as names
    NEGATIVE_VOCABULARY: Set[str] = {
        # --- Numbers 1-20 (Hindi, Hinglish, Mundari) ---
        "एक", "दो", "तीन", "चार", "पाँच", "पांच", "छह", "छः", "सात", "आठ", "नौ", "दस",
        "ग्यारह", "बारह", "तेरह", "चौदह", "पंद्रह", "सोलह", "सत्रह", "अठारह", "उन्नीस", "बीस",
        "ek", "do", "teen", "char", "chaar", "paanch", "panch", "chheh", "chhe", "chhah",
        "saat", "aath", "nau", "das", "gyarah", "barah", "terah", "chaudah", "pandrah",
        "solah", "satrah", "atharah", "unnees", "unnis", "bees", "bis",
        "मियाद", "मिअद", "बारिया", "बरिया", "अपिया", "अपि", "उपुनियां", "उपुन", "मोड़ेया", "मोड़े",
        "तुरूइया", "तुरुइ", "एया", "इरलिया", "इरल", "आरेया", "आरे", "गेलेया", "गेल",
        "गेलमियाद", "गेलबारिया", "गेलअपिया", "गेलउपुनियां", "गेलमोड़ेया", "गेलतुरूइया", "गेनएया",
        "गेलइरलिया", "गेलआरेया", "बारहिसि", "हिसि",

        # --- Classroom Nouns & Objects ---
        "किताब", "किताबें", "कापी", "कॉपी", "कलम", "पेंसिल", "पेन", "सेब", "आम", "पानी", "फल",
        "पेड़", "घर", "स्कूल", "कक्षा", "पाठ", "सवाल", "उत्तर", "भाषा", "बच्चा", "बच्चे", "बच्चों",
        "छात्र", "छात्रा", "शिक्षक", "शिक्षिका", "सर", "मैडम", "दीदी", "भैया", "लड़का", "लड़की",
        "kitab", "kitaben", "kopi", "copy", "kalam", "pencil", "pen", "seb", "aam", "pani", "paani",
        "fal", "ped", "ghar", "school", "kaksha", "path", "sawal", "uttar", "bhasha", "bachha",
        "bachhe", "bachho", "chhatra", "shikshak", "sir", "madam", "didi", "bhaiya", "ladka", "ladki",
        "किताबा", "किताबको", "दाः", "ओड़ाः", "होन", "होनको", "माहातो", "शिक्षक", "बिर", "गाड़ा",

        # --- Classroom Verbs & Commands ---
        "बैठो", "बैठिए", "बैठ", "उठो", "उठिए", "उठ", "पढ़ो", "पढ़िए", "पढ़", "लिखो", "लिखिए", "लिख",
        "गिनो", "गिनिए", "गिन", "सुनो", "सुनिए", "सुन", "बोलो", "बोलिए", "बोल", "आओ", "आइए", "आ",
        "जाओ", "जाइए", "जा", "देखो", "देखिए", "देख", "छूओ", "छूइए", "छू", "बताओ", "बताइए", "बता",
        "खोलो", "खोलिए", "खोल", "बंद", "करो", "कीजिए", "कर", "लो", "लीजिए", "ले", "दो", "दीजिए",
        "चलो", "चलिए", "चल", "खाओ", "खाइए", "खा", "पियो", "पीजिए", "पी", "गाओ", "गाइए", "गा",
        "नाचो", "नाचिए", "नाच", "रहो", "रहिए", "रह", "बुलाओ", "बुलाइए", "बुला",
        "baitho", "baithiye", "utho", "uthiye", "padho", "padhiye", "likho", "likhiye",
        "gino", "giniye", "suno", "suniye", "bolo", "boliye", "aao", "aaiye", "jao", "jaiye",
        "dekho", "dekhiye", "chhuo", "batao", "kholo", "karo", "kijiye", "lo", "chalo", "khao",
        "bulao", "bulaiye", "bula",
        "दुबपे", "दुबमे", "ओलपे", "ओलमे", "पाड़ावपे", "पाड़ावमे", "लेकापे", "लेकामे", "आयूमपे", "आयूममे",
        "कजिपे", "काजीपे", "हिजुमे", "हिजुपे", "सेनेपे", "सेनेमे", "जोमपे", "राःएमे", "राःपे", "केड़ाएमे", "केड़ापे",

        # --- Language Names (Strictly preserved as language entities, NOT people) ---
        "हिंदी", "हिन्दी", "मुंडारी", "मुण्डारी", "अंग्रेज़ी", "अंग्रेजी", "संस्कृत", "उर्दू",
        "hindi", "mundari", "english", "sanskrit", "urdu",

        # --- Greetings, Particles & Discourse ---
        "नमस्ते", "प्रणाम", "जोहार", "धन्यवाद", "अलविदा", "हाँ", "नहीं", "मत", "कृपया",
        "namaste", "pranam", "johar", "dhanyawad", "alvida", "haan", "nahi", "nahin", "mat", "kripya",

        # --- Pronouns, Prepositions, Auxiliaries ---
        "मेरा", "मेरी", "मेरे", "तुम्हारा", "तुम्हारी", "तुम्हारे", "आपका", "आपकी", "आपके",
        "उसका", "उसकी", "उसके", "इसका", "इसकी", "इसके", "अपना", "अपनी", "अपने", "हमारा", "हमारी", "हमारे",
        "मैं", "हम", "तुम", "आप", "वह", "यह", "वे", "ये", "सब", "सभी", "लोग", "कोई", "कुछ",
        "क्या", "कौन", "कहाँ", "कहाँ", "कब", "कैसे", "क्यों", "इधर", "उधर", "यहाँ", "यहां", "वहाँ", "वहां",
        "को", "में", "से", "का", "की", "के", "ने", "पर", "तक", "लिए", "बारे",
        "है", "हैं", "हो", "हूँ", "था", "थी", "थे", "होगी", "होगा", "होंगे",
        "और", "तथा", "एवं", "या", "अथवा", "लेकिन", "परंतु", "किंतु", "तो", "भी", "ही",
        "mera", "meri", "mere", "tumhara", "tumhari", "tumhare", "apka", "apki", "apke",
        "uska", "uski", "uske", "iska", "iski", "iske", "apna", "apni", "apne", "hamara",
        "main", "hum", "ham", "tum", "aap", "wo", "woh", "ye", "yeh", "sab", "sabhi",
        "kya", "kaun", "kahan", "kab", "kaise", "kyun", "idhar", "udhar", "yahan", "vahan",
        "ko", "mein", "me", "se", "ka", "ki", "ke", "ne", "par", "tak", "liye",
        "hai", "hain", "ho", "hoon", "h", "tha", "thi", "the", "hoga", "hogi",
        "aur", "ya", "lekin", "to", "bhi", "hi",
        "आञ", "आञाः", "आम", "आमाः", "इनिः", "नेआ", "एना", "सोबेन", "तना", "मेनाः", "गे", "रे", "ते", "ओड़ोः"
    }

    # Educational Template Mappings for Protected Classroom Patterns
    # Maps Hindi template -> Mundari template
    HI_TO_UNR_TEMPLATES = {
        # Identity / Name introductions
        "मेरा नाम __NAME_0__ है": "आञाः नुतुम __NAME_0__",
        "मेरा नाम __NAME_0__": "आञाः नुतुम __NAME_0__",
        "नाम __NAME_0__ है": "आञाः नुतुम __NAME_0__",
        "नाम __NAME_0__": "आञाः नुतुम __NAME_0__",
        "मेरा नाम है __NAME_0__": "आञाः नुतुम __NAME_0__",
        "नाम है __NAME_0__": "आञाः नुतुम __NAME_0__",

        # Calling commands
        "__NAME_0__ को बुलाओ": "__NAME_0__ के राःएमे",
        "__NAME_0__ को बुलाइए": "__NAME_0__ के राःएमे",
        "__NAME_0__ को बुला": "__NAME_0__ के राःएमे",

        # Movement / Posture commands
        "__NAME_0__ बैठो": "__NAME_0__ दुबपे",
        "__NAME_0__ बैठिए": "__NAME_0__ दुबपे",
        "__NAME_0__ यहाँ आओ": "__NAME_0__ नेताः हिजुमे",
        "__NAME_0__ यहां आओ": "__NAME_0__ नेताः हिजुमे",
        "__NAME_0__ इधर आओ": "__NAME_0__ नेताः हिजुमे",
        "__NAME_0__ पढ़ो": "__NAME_0__ पाड़ावपे",
        "__NAME_0__ पढ़िए": "__NAME_0__ पाड़ावपे",
        "__NAME_0__ लिखो": "__NAME_0__ ओलपे",
        "__NAME_0__ लिखिए": "__NAME_0__ ओलपे",
        "__NAME_0__ गिनो": "__NAME_0__ लेकापे",
        "__NAME_0__ सुनो": "__NAME_0__ आयूमपे",

        # Two-name coordination
        "__NAME_0__ और __NAME_1__ बैठो": "__NAME_0__ ओड़ोः __NAME_1__ दुबपे",
        "__NAME_0__ और __NAME_1__ यहाँ आओ": "__NAME_0__ ओड़ोः __NAME_1__ नेताः हिजुमे",
        "__NAME_0__ और __NAME_1__ पढ़ो": "__NAME_0__ ओड़ोः __NAME_1__ पाड़ावपे",
        "__NAME_0__ और __NAME_1__ लिखो": "__NAME_0__ ओड़ोः __NAME_1__ ओलपे",

        # Greetings with personal name
        "नमस्ते __NAME_0__": "जोहार __NAME_0__",
        "जोहार __NAME_0__": "जोहार __NAME_0__",
        "__NAME_0__ नमस्ते": "__NAME_0__ जोहार",
        "__NAME_0__ जोहार": "__NAME_0__ जोहार",

        # End of sentence address
        "यहाँ बैठो __NAME_0__": "नेताः दुबपे __NAME_0__",
        "यहां बैठो __NAME_0__": "नेताः दुबपे __NAME_0__",
        "इधर बैठो __NAME_0__": "नेताः दुबपे __NAME_0__",
        "बैठो __NAME_0__": "दुबपे __NAME_0__",
        "यहाँ आओ __NAME_0__": "नेताः हिजुमे __NAME_0__",
        "यहां आओ __NAME_0__": "नेताः हिजुमे __NAME_0__",
        "इधर आओ __NAME_0__": "नेताः हिजुमे __NAME_0__",
        "किताब पढ़ो __NAME_0__": "किताबा पाड़ावपे __NAME_0__",

        # Standalone name
        "__NAME_0__": "__NAME_0__"
    }

    # Reverse Educational Template Mappings (Mundari -> Hindi)
    UNR_TO_HI_TEMPLATES = {
        "आञाः नुतुम __NAME_0__": "मेरा नाम __NAME_0__ है",
        "आञाः नुतुम __NAME_0__ तना": "मेरा नाम __NAME_0__ है",
        "आमाः नुतुम __NAME_0__": "तुम्हारा नाम __NAME_0__ है",
        "नुतुम __NAME_0__": "नाम __NAME_0__ है",
        "नुतुम __NAME_0__ तना": "नाम __NAME_0__ है",

        "__NAME_0__ के राःएमे": "__NAME_0__ को बुलाओ",
        "__NAME_0__ के केड़ाएमे": "__NAME_0__ को बुलाओ",
        "__NAME_0__ के राःपे": "__NAME_0__ को बुलाओ",
        "__NAME_0__ के केड़ापे": "__NAME_0__ को बुलाओ",

        "__NAME_0__ दुबपे": "__NAME_0__ बैठो",
        "__NAME_0__ दुबमे": "__NAME_0__ बैठो",
        "__NAME_0__ नेताः हिजुमे": "__NAME_0__ यहाँ आओ",
        "__NAME_0__ हिजुमे": "__NAME_0__ यहाँ आओ",
        "__NAME_0__ पाड़ावपे": "__NAME_0__ पढ़ो",
        "__NAME_0__ पाड़ावमे": "__NAME_0__ पढ़ो",
        "__NAME_0__ ओलपे": "__NAME_0__ लिखो",
        "__NAME_0__ ओलमे": "__NAME_0__ लिखो",
        "__NAME_0__ लेकापे": "__NAME_0__ गिनो",
        "__NAME_0__ आयूमपे": "__NAME_0__ सुनो",

        "__NAME_0__ ओड़ोः __NAME_1__ दुबपे": "__NAME_0__ और __NAME_1__ बैठो",
        "__NAME_0__ ओड़ोः __NAME_1__ नेताः हिजुमे": "__NAME_0__ और __NAME_1__ यहाँ आओ",

        "जोहार __NAME_0__": "नमस्ते __NAME_0__",
        "__NAME_0__ जोहार": "__NAME_0__ नमस्ते",

        "नेताः दुबपे __NAME_0__": "यहाँ बैठो __NAME_0__",
        "दुबपे __NAME_0__": "बैठो __NAME_0__",
        "नेताः हिजुमे __NAME_0__": "यहाँ आओ __NAME_0__",
        "किताबा पाड़ावपे __NAME_0__": "किताब पढ़ो __NAME_0__",

        "__NAME_0__": "__NAME_0__"
    }

    def __init__(self):
        pass

    def is_negative_word(self, token: str) -> bool:
        """Checks if a token is an ordinary vocabulary word that must NEVER be shielded as a name."""
        if not token:
            return True
        norm = token.strip().lower()
        if re.match(r"^__name_\d+__$", norm, re.IGNORECASE):
            return True
        if norm in self.NEGATIVE_VOCABULARY:
            return True
        # Check pure digits
        if norm.isdigit():
            return True
        return False

    ANCHOR_NAMES = ["राम", "सीता", "मोहन", "गीता"]

    def prepare_for_neural(self, text: str, name_map: Dict[str, str]) -> Tuple[str, Dict[str, str]]:
        """
        Substitutes __NAME_0__, __NAME_1__ with attested vocabulary anchor names (e.g. राम, सीता)
        so that Seq2Seq neural translation preserves syntactic slots without BPE fragmentation.
        Returns:
            (anchor_text, anchor_to_placeholder_map)
        """
        anchor_text = text
        anchor_map: Dict[str, str] = {}
        for i, placeholder in enumerate(name_map.keys()):
            anchor = self.ANCHOR_NAMES[i % len(self.ANCHOR_NAMES)]
            anchor_text = anchor_text.replace(placeholder, anchor)
            anchor_map[anchor] = placeholder
        return anchor_text, anchor_map

    def restore_from_neural(self, text: Optional[str], anchor_map: Dict[str, str]) -> Optional[str]:
        """
        Replaces neural anchor names back to their original __NAME_X__ placeholders.
        """
        if text is None or not anchor_map:
            return text
        res = text
        for anchor, placeholder in anchor_map.items():
            res = res.replace(anchor, placeholder)
        return res

    def detect_names(self, text: str, direction: str = "hi-unr") -> List[Tuple[int, int, str]]:
        """
        Detects candidate personal proper name spans within the input text.
        Returns a list of (start_idx, end_idx, name_str) sorted by start index.
        """
        if not text or not text.strip():
            return []

        raw = text.strip()
        spans: List[Tuple[int, int, str]] = []

        # -------------------------------------------------------------
        # PATTERN 1: Two Names with Conjunction (Rahul और Priya बैठो)
        # -------------------------------------------------------------
        p_two_names = re.finditer(
            r'\b([A-Za-z\u0900-\u097F]+)\s+(?:और|तथा|एवं|aur|odo|ओड़ोः)\s+([A-Za-z\u0900-\u097F]+)\b',
            raw,
            re.IGNORECASE
        )
        for m in p_two_names:
            w1 = m.group(1).strip()
            w2 = m.group(2).strip()
            if not self.is_negative_word(w1) and not self.is_negative_word(w2):
                spans.append((m.start(1), m.end(1), w1))
                spans.append((m.start(2), m.end(2), w2))

        # -------------------------------------------------------------
        # PATTERN 2: Explicit Identity Phrases ("मेरा नाम X है", "mera naam X hai")
        # -------------------------------------------------------------
        p_intro = re.finditer(
            r'(?:मेरा\s+नाम|नाम|mera\s+naam|naam|आञाः\s+नुतुम|आमाः\s+नुतुम|नुतुम)\s+(?:है|था|hai|h|tha|तना)?\s*([A-Za-z\u0900-\u097F]+)(?:\s+(?:है|था|hai|h|tha|तना))?',
            raw,
            re.IGNORECASE
        )
        for m in p_intro:
            cand = m.group(1).strip()
            if not self.is_negative_word(cand):
                spans.append((m.start(1), m.end(1), cand))

        # -------------------------------------------------------------
        # PATTERN 3: Calling Commands ("X को बुलाओ", "X ko bulao", "X के राःएमे")
        # -------------------------------------------------------------
        p_call = re.finditer(
            r'\b([A-Za-z\u0900-\u097F]+)\s+(?:को\s+(?:बुलाओ|बुलाइए|बुला)|ko\s+(?:bulao|bulaiye|bula)|के\s+(?:राःएमे|केड़ाएमे|राःपे|केड़ापे))\b',
            raw,
            re.IGNORECASE
        )
        for m in p_call:
            cand = m.group(1).strip()
            if not self.is_negative_word(cand):
                spans.append((m.start(1), m.end(1), cand))

        # -------------------------------------------------------------
        # PATTERN 4: Direct Person Commands ("X बैठो", "X यहाँ आओ", "X पढ़ो", "X likho")
        # -------------------------------------------------------------
        p_cmd = re.finditer(
            r'\b([A-Za-z\u0900-\u097F]+)\s+(?:बैठो|बैठिए|यहाँ\s+आओ|यहां\s+आओ|इधर\s+आओ|पढ़ो|पढ़िए|लिखो|लिखिए|गिनो|गिनिए|सुनो|सुनिए|'
            r'baitho|baithiye|yahan\s+aao|idhar\s+aao|padho|padhiye|likho|likhiye|suno|gino|'
            r'दुबपे|दुबमे|नेताः\s+हिजुमे|हिजुमे|हिजुपे|पाड़ावपे|पाड़ावमे|ओलपे|ओलमे|लेकापे|आयूमपे)\b',
            raw,
            re.IGNORECASE
        )
        for m in p_cmd:
            cand = m.group(1).strip()
            if not self.is_negative_word(cand):
                spans.append((m.start(1), m.end(1), cand))

        # -------------------------------------------------------------
        # PATTERN 5: Greetings ("नमस्ते X", "जोहार X", "namaste X", "X नमस्ते")
        # -------------------------------------------------------------
        p_greet = re.finditer(
            r'(?:नमस्ते|प्रणाम|जोहार|namaste|johar)\s+([A-Za-z\u0900-\u097F]+)\b|\b([A-Za-z\u0900-\u097F]+)\s+(?:नमस्ते|प्रणाम|जोहार|namaste|johar)',
            raw,
            re.IGNORECASE
        )
        for m in p_greet:
            cand = (m.group(1) or m.group(2) or "").strip()
            if cand and not self.is_negative_word(cand):
                s_idx = m.start(1) if m.group(1) else m.start(2)
                e_idx = m.end(1) if m.group(1) else m.end(2)
                spans.append((s_idx, e_idx, cand))

        # -------------------------------------------------------------
        # PATTERN 6: End of sentence address ("यहाँ बैठो Rahul", "किताब पढ़ो Rahul")
        # -------------------------------------------------------------
        p_end = re.finditer(
            r'(?:यहाँ\s+आओ|इधर\s+आओ|बैठो|बैठिए|पढ़ो|पढ़िए|लिखो|लिखिए|बुलाओ|बुलाइए)\s+([A-Za-z\u0900-\u097F]+)\s*$',
            raw,
            re.IGNORECASE
        )
        for m in p_end:
            cand = m.group(1).strip()
            if not self.is_negative_word(cand):
                spans.append((m.start(1), m.end(1), cand))

        # -------------------------------------------------------------
        # PATTERN 7: Script Discrepancy Signal (Latin token in Devanagari text)
        # e.g., "यह Rahul की किताब है" -> "Rahul" is Latin in Hindi text
        # -------------------------------------------------------------
        has_devanagari = bool(re.search(r'[\u0900-\u097F]', raw))
        if has_devanagari:
            p_latin_in_deva = re.finditer(r'\b([A-Za-z]{2,})\b', raw)
            for m in p_latin_in_deva:
                cand = m.group(1).strip()
                if not self.is_negative_word(cand):
                    spans.append((m.start(1), m.end(1), cand))

        # -------------------------------------------------------------
        # PATTERN 8: Capitalized Latin Word in Hinglish (Titlecase personal name)
        # e.g., "kal Rahul school gaya tha" -> "Rahul" is capitalized non-first token
        # -------------------------------------------------------------
        tokens_with_indices = [
            (m.start(1), m.end(1), m.group(1))
            for m in re.finditer(r'\b([A-Za-z\u0900-\u097F]+)\b', raw)
        ]
        for idx, (s_idx, e_idx, token) in enumerate(tokens_with_indices):
            # If capitalized Latin token
            if re.match(r'^[A-Z][a-z]+$', token) and not self.is_negative_word(token):
                # If it's not the first word, or if it's the only word in input
                if idx > 0 or len(tokens_with_indices) == 1:
                    spans.append((s_idx, e_idx, token))

        # -------------------------------------------------------------
        # PATTERN 9: Standalone Single Token Name
        # e.g., "Rahul" or "राहुल"
        # -------------------------------------------------------------
        if len(tokens_with_indices) == 1:
            s_idx, e_idx, token = tokens_with_indices[0]
            if not self.is_negative_word(token) and len(token) >= 2:
                spans.append((s_idx, e_idx, token))

        # Deduplicate and sort spans
        unique_spans: List[Tuple[int, int, str]] = []
        seen_ranges: Set[Tuple[int, int]] = set()

        # Sort by start ascending, then length descending
        spans.sort(key=lambda x: (x[0], -(x[1] - x[0])))

        for s_idx, e_idx, val in spans:
            # Overlap check
            overlap = False
            for prev_s, prev_e in seen_ranges:
                if not (e_idx <= prev_s or s_idx >= prev_e):
                    overlap = True
                    break
            if not overlap:
                seen_ranges.add((s_idx, e_idx))
                unique_spans.append((s_idx, e_idx, val))

        unique_spans.sort(key=lambda x: x[0])
        return unique_spans

    def protect(self, text: str, direction: str = "hi-unr") -> Tuple[str, Dict[str, str]]:
        """
        Shields detected personal names with unambiguous placeholders (__NAME_0__, __NAME_1__, ...).
        Returns:
            (protected_text, name_map)
        where name_map maps placeholder -> original_name.
        """
        if not text or not text.strip():
            return text, {}

        detected = self.detect_names(text, direction=direction)
        if not detected:
            return text, {}

        name_map: Dict[str, str] = {}
        # Reconstruct string with placeholders
        result_pieces: List[str] = []
        last_idx = 0

        for i, (s_idx, e_idx, original_name) in enumerate(detected):
            placeholder = f"__NAME_{i}__"
            name_map[placeholder] = original_name
            result_pieces.append(text[last_idx:s_idx])
            result_pieces.append(placeholder)
            last_idx = e_idx

        result_pieces.append(text[last_idx:])
        protected_text = "".join(result_pieces)
        return protected_text, name_map

    def restore(self, text: Optional[str], name_map: Dict[str, str]) -> Optional[str]:
        """
        Restores exact original proper name strings into translated text.
        Guarantees that NO placeholder (__NAME_X__) can ever leak to the caller.
        """
        if text is None or not name_map:
            return text

        restored = str(text)

        # 1. Substitute placeholders (case-insensitive for resilience)
        for placeholder, original_name in name_map.items():
            # Exact placeholder
            restored = restored.replace(placeholder, original_name)
            # Lowercase variant (e.g. __name_0__)
            restored = restored.replace(placeholder.lower(), original_name)
            # Mixed or spaced variants
            pattern = re.compile(re.escape(placeholder), re.IGNORECASE)
            restored = pattern.sub(original_name, restored)

        # 2. Safety Sweep: Ensure NO __NAME_X__ or __name_X__ survives
        # If any placeholder was somehow emitted by neural model or unmapped, clean it cleanly
        restored = re.sub(r'__NAME_\d+__', '', restored, flags=re.IGNORECASE)
        # Clean up possible double spaces left by removal
        restored = re.sub(r'\s+', ' ', restored).strip()

        return restored

    def try_template_translation(
        self,
        protected_text: str,
        name_map: Dict[str, str],
        direction: str = "hi-unr"
    ) -> Optional[str]:
        """
        Checks if the protected query matches an attested educational classroom phrase template.
        If matched, returns the translated text with placeholders restored.
        """
        if not protected_text or not name_map:
            return None

        # Clean/normalize whitespace for lookup
        clean_query = re.sub(r'\s+', ' ', protected_text.strip())
        norm_dir = (direction or "hi-unr").strip().lower()
        is_rev = norm_dir in ("unr-hi", "mundari-hindi", "mun-hi", "unr_to_hi", "reverse")

        templates = self.UNR_TO_HI_TEMPLATES if is_rev else self.HI_TO_UNR_TEMPLATES

        # Direct template lookup
        target_template = templates.get(clean_query)
        if target_template:
            return self.restore(target_template, name_map)

        # Case-insensitive / punctuation-stripped lookup
        clean_no_punct = re.sub(r'[^\w\s\u0900-\u097F_]', '', clean_query).strip()
        for tmpl_src, tmpl_target in templates.items():
            clean_tmpl = re.sub(r'[^\w\s\u0900-\u097F_]', '', tmpl_src).strip()
            if clean_no_punct == clean_tmpl:
                return self.restore(tmpl_target, name_map)

        return None
