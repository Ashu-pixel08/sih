"""
Audit governed Hinglish lexicon
"""
import sys
import os
import json

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lex_path = os.path.join(PROJECT_ROOT, "data", "approved", "hinglish", "governed_hinglish_lexicon.json")

with open(lex_path, "r", encoding="utf-8") as f:
    entries = json.load(f)

print(f"Total entries: {len(entries)}")
phrases = [e for e in entries if len(e.get("hinglish", "").split()) > 1]
print(f"Multi-word phrases: {len(phrases)}")
for p in phrases:
    print(f"  '{p['hinglish']}' -> '{p['hindi']}' [{p.get('category')}] ({p.get('status')})")

print("\nSingle word sample:")
for w in entries[:20]:
    if len(w.get("hinglish", "").split()) == 1:
        print(f"  '{w['hinglish']}' -> '{w['hindi']}'")
