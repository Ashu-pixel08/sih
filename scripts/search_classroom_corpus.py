"""
Search parallel corpus for attested classroom and numeracy sentences.
"""
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")

tsv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw", "translation", "translation-hi-unr.tsv")

with open(tsv_path, "r", encoding="utf-8") as f:
    lines = [line.strip().split("\t") for line in f if "\t" in line]

print(f"Total lines: {len(lines)}")

# Search for sentences containing teaching/classroom/counting words
targets = [
    "गिन", "संख्या", "नंबर", "किताब", "स्कूल", "पढ़ा", "पढ़", "सीख", "सुनो", "ध्यान",
    "एक से", "दस तक", "पाँच", "पांच", "बच्चे", "बच्चो", "बोलो", "सवाल", "उत्तर"
]

found = []
for idx, (hi, unr) in enumerate(lines):
    hi_words = hi.split()
    if 5 <= len(hi_words) <= 30:
        matches = [t for t in targets if t in hi]
        if len(matches) >= 2:
            found.append((idx, hi, unr, len(hi_words), matches))

print(f"Found {len(found)} candidate sentences.")
found.sort(key=lambda x: -len(x[4]))

for idx, hi, unr, wcnt, matches in found[:40]:
    print(f"\n[Row {idx}] (words: {wcnt}, matches: {matches})")
    print(f"  HI:  {hi}")
    print(f"  UNR: {unr}")
