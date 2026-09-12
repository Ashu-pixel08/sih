"""
reporter.py - Candidate Dataset Profiling and Reporting Tool
Generates statistical, vocabulary, category, licensing, and demographic summaries
for any candidate dataset before ingestion.
"""

import os
import sys
import json
import re
from collections import Counter
from typing import Dict, List, Any


class DatasetReporter:
    """Generates detailed reports on candidate datasets."""

    WORD_TOKENIZER = re.compile(r"[\s,;:.?!()\"\[\]{}।]+")

    def analyze_dataset(self, file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}

        records = []
        if file_path.endswith(".json"):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for k in ["records", "phrases", "recordings", "utterances", "competencies"]:
                    if k in data and isinstance(data[k], list):
                        records = data[k]
                        break
            elif isinstance(data, list):
                records = data
        elif file_path.endswith(".tsv"):
            with open(file_path, "r", encoding="utf-8") as f:
                for idx, line in enumerate(f):
                    parts = line.strip().split("\t")
                    if len(parts) >= 2:
                        records.append({
                            "hindi_text": parts[0],
                            "mundari_text": parts[1],
                            "domain": "GENERAL",
                            "grade": 1,
                            "license": "KPL-BY-NC-SA-FS-1.0",
                            "acceptance_status": "SOURCE_FOUND"
                        })

        total = len(records)
        hindi_tokens = Counter()
        mundari_tokens = Counter()
        categories = Counter()
        grades = Counter()
        licenses = Counter()
        statuses = Counter()
        sources = Counter()
        speakers = Counter()
        dialects = Counter()
        missing_fields = Counter()
        audio_durations_sec = []

        unique_sentence_pairs = set()

        for r in records:
            h = r.get("hindi_text") or r.get("transcript") or r.get("hindi_source_text") or ""
            m = r.get("mundari_text") or r.get("mundari_source_text") or ""

            if h and m:
                unique_sentence_pairs.add((h.strip(), m.strip()))

            for token in self.WORD_TOKENIZER.split(h):
                t = token.strip()
                if t:
                    hindi_tokens[t] += 1

            for token in self.WORD_TOKENIZER.split(m):
                t = token.strip()
                if t:
                    mundari_tokens[t] += 1

            cat = r.get("category") or r.get("domain") or r.get("subject") or "UNCATEGORIZED"
            categories[cat] += 1

            gr = r.get("grade")
            if gr is not None:
                grades[f"Grade_{gr}"] += 1
            else:
                missing_fields["grade"] += 1

            lic = r.get("license") or r.get("license_provenance") or "UNSPECIFIED"
            licenses[lic] += 1

            stat = r.get("acceptance_status") or r.get("validation_status") or r.get("speech_status") or "UNSPECIFIED"
            statuses[stat] += 1

            src = r.get("source") or r.get("source_document") or "UNSPECIFIED"
            sources[src] += 1

            spk = r.get("speaker_id")
            if spk:
                speakers[spk] += 1

            dia = r.get("dialect")
            if dia:
                dialects[dia] += 1

            dur_ms = r.get("duration_ms")
            dur_s = r.get("duration_sec")
            if dur_ms:
                audio_durations_sec.append(dur_ms / 1000.0)
            elif dur_s:
                audio_durations_sec.append(dur_s)

        total_audio_hours = sum(audio_durations_sec) / 3600.0 if audio_durations_sec else 0.0

        return {
            "dataset_file": os.path.basename(file_path),
            "total_records": total,
            "unique_sentence_pairs": len(unique_sentence_pairs),
            "lexical_metrics": {
                "total_hindi_tokens": sum(hindi_tokens.values()),
                "unique_hindi_vocabulary": len(hindi_tokens),
                "total_mundari_tokens": sum(mundari_tokens.values()),
                "unique_mundari_vocabulary": len(mundari_tokens)
            },
            "audio_metrics": {
                "audio_files_annotated": len(audio_durations_sec),
                "total_duration_hours": round(total_audio_hours, 3),
                "unique_speakers": len(speakers),
                "unique_dialects": len(dialects)
            },
            "distributions": {
                "categories": dict(categories.most_common(10)),
                "grades": dict(grades.most_common()),
                "licenses": dict(licenses.most_common(5)),
                "validation_statuses": dict(statuses.most_common()),
                "top_sources": dict(sources.most_common(5)),
                "dialects": dict(dialects.most_common(5))
            },
            "missing_fields": dict(missing_fields)
        }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python reporter.py <path_to_dataset_file>")
        sys.exit(1)

    rep = DatasetReporter()
    summary = rep.analyze_dataset(sys.argv[1])
    print(json.dumps(summary, indent=2, ensure_ascii=False))
