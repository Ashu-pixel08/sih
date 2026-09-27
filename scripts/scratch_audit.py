"""
Audit existing corpus, phrasebooks, and candidate sentences for Golden Demo Set.
"""
import sys
import os
import json
import re

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from ai.translation.translation_engine import TranslationEngine
from ai.translation.hinglish_normalizer import HinglishNormalizer
from ai.speech.pronunciation_service import PronunciationService

def audit_corpus():
    tsv_path = os.path.join(PROJECT_ROOT, "data", "raw", "translation", "translation-hi-unr.tsv")
    pairs = []
    with open(tsv_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            parts = line.strip().split("\t")
            if len(parts) == 2:
                pairs.append((idx, parts[0].strip(), parts[1].strip()))
    
    print(f"Loaded {len(pairs)} parallel pairs from TSV.")
    return pairs

def test_engine_on_candidates():
    engine = TranslationEngine(enable_neural=True)
    hnorm = HinglishNormalizer()
    p_service = PronunciationService(project_root=PROJECT_ROOT)

    candidates_hi = [
        ("HI_CAND_1", "आज हम नंबर के बारे में पढ़ेंगे। चलो बताओ, कौन 1 से 10 तक की गिनती बताएगा?"),
        ("HI_CAND_2", "सब बच्चे ध्यान से सुनो, मैं एक नंबर बोलूँगा और तुम सब उसके बाद वही नंबर बोलना।"),
        ("HI_CAND_3", "बहुत अच्छा, अब कौन मुझे बता सकता है कि पाँच के बाद कौन सा नंबर आता है?"),
        ("HI_CAND_4", "अपनी किताब खोलो और नंबर वाले पेज पर जाओ, फिर एक से दस तक की गिनती पढ़ो।"),
        ("HI_CAND_5", "अब हम सब मिलकर एक से दस तक की गिनती बोलेंगे, पहले मैं बोलूँगा और फिर तुम लोग दोहराना।"),
        ("HI_CAND_6", "बहुत बढ़िया, अब तुममें से कौन आगे आकर दस तक की गिनती सबको सुनाएगा?")
    ]

    candidates_hinglish = [
        ("HING_CAND_1", "aaj hum number ke baare mein padhenge, chalo batao kaun 1 se 10 tak ki ginti batayega"),
        ("HING_CAND_2", "sab bacche dhyan se suno, pehle main bolunga phir tum log repeat karna"),
        ("HING_CAND_3", "bahut achha, ab batao paanch ke baad kaunsa number aata hai")
    ]

    print("\n--- HINDI CANDIDATES ---")
    for cid, text in candidates_hi:
        res = engine.translate(text, direction="hi-unr")
        audio_res, audio_err = p_service.synthesize(res.translated_text, "mundari") if res.translated_text else (None, "NO_TEXT")
        print(f"\nID: {cid}")
        print(f"Input: {text}")
        print(f"Status: {res.status} | MatchType: {res.match_type} | Conf: {res.confidence}")
        print(f"Source: {res.translation_source} | Provenance: {res.provenance}")
        print(f"Output: {res.translated_text}")
        print(f"Audio: {'YES' if audio_res else 'NO'} ({getattr(audio_res, 'verification_status', audio_err)})")

    print("\n--- HINGLISH CANDIDATES ---")
    for cid, text in candidates_hinglish:
        norm_res = hnorm.normalize(text)
        res = engine.translate(text, direction="hi-unr", src_lang="hinglish")
        audio_res, audio_err = p_service.synthesize(res.translated_text, "mundari") if res.translated_text else (None, "NO_TEXT")
        print(f"\nID: {cid}")
        print(f"Input: {text}")
        print(f"Norm Status: {norm_res.status} | Norm Conf: {norm_res.confidence}")
        print(f"Normalized Hindi: {norm_res.normalized_hindi}")
        print(f"Unmapped: {norm_res.unmapped_tokens}")
        print(f"Trans Status: {res.status} | Conf: {res.confidence} | Output: {res.translated_text}")
        print(f"Audio: {'YES' if audio_res else 'NO'} ({getattr(audio_res, 'verification_status', audio_err)})")

if __name__ == "__main__":
    test_engine_on_candidates()
