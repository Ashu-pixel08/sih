"""
Test candidate natural classroom sentences of varying lengths through TranslationEngine,
Quality Gate, and PronunciationService.
"""
import sys
import os
import json

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from ai.translation.translation_engine import TranslationEngine
from ai.translation.hinglish_normalizer import HinglishNormalizer
from ai.speech.pronunciation_service import PronunciationService
from ai.ml_translation.quality_gate import TranslationQualityGate

engine = TranslationEngine(enable_neural=True)
hnorm = HinglishNormalizer()
p_service = PronunciationService(project_root=PROJECT_ROOT)
qgate = TranslationQualityGate()

test_sentences = [
    # Variations of candidate 1
    "आज हम सब मिलकर एक से दस तक गिनती सीखेंगे।",
    "सभी बच्चे ध्यान से सुनो, अब हम एक से दस तक गिनेंगे।",
    "चलो सब मिलकर एक से दस तक गिनते हैं।",
    
    # Variations of candidate 2
    "सब बच्चे ध्यान से सुनो और मेरे बाद बोलो।",
    "सभी बच्चे ध्यान से सुनो और एक साथ बोलो।",
    "सब बच्चे बैठो और ध्यान से सुनो।",
    
    # Variations of candidate 3
    "बहुत अच्छा, अब बताओ पाँच के बाद क्या आता है?",
    "बहुत अच्छा, अब बताओ यह कौन सी संख्या है?",
    "बहुत अच्छा, सब बच्चे एक साथ बोलो।",
    
    # Variations of candidate 4
    "अपनी किताब खोलो और एक से दस तक गिनो।",
    "सभी बच्चे अपनी किताब खोलो और पढ़ो।",
    "किताब खोलो और एक से दस तक की गिनती पढ़ो।",
    
    # Variations of candidate 5
    "अब हम सब मिलकर एक से दस तक बोलेंगे।",
    "पहले मैं बोलूँगा और फिर तुम सब बोलना।",
    "एक साथ बोलो, एक दो तीन चार पाँच छह सात आठ नौ दस।",
    
    # Variations of candidate 6 & Student responses
    "मेरा नाम बिरसा है, मैं एक से दस तक सुनाऊँगा।",
    "मेरा नाम राहुल है और मैं स्कूल में पढ़ता हूँ।",
    "बहुत बढ़िया, अब तुम आगे आकर गिनती सुनाओ।"
]

print(f"{'Sentence':<50} | {'Status':<25} | {'Source':<18} | {'Conf':<6} | {'Output'}")
print("-" * 130)

for s in test_sentences:
    res = engine.translate(s, direction="hi-unr")
    out = res.translated_text or "NONE"
    print(f"{s:<50} | {res.status:<25} | {res.translation_source:<18} | {res.confidence:<6.3f} | {out}")
