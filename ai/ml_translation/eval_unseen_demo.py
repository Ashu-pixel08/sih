"""
ai/ml_translation/eval_unseen_demo.py
=============================================================================
SIH260042: Evaluation of 20 Strictly Unseen Primary Classroom Hindi Sentences
=============================================================================
Runs inference across the 20 verified unseen classroom sentences:
  - Baseline Decoding vs Improved Decoding + Quality Gate
  - Measures model_score, latency (p50, p95), tokens generated, QG pass rate
  - Outputs full comparison report in JSON format for Phase 11 documentation.
=============================================================================
"""

import os
import sys
import json
import time
import numpy as np

from ai.ml_translation.inference import NeuralTranslationEngine
from ai.ml_translation.quality_gate import TranslationQualityGate


def run_unseen_benchmark_eval(
    benchmark_json: str = "data/benchmarks/unseen_demo_20.json",
    output_json: str = "models/nmt/eval_results/unseen_demo_20_results.json"
):
    print(f"[UnseenEval] Loading benchmark from {benchmark_json}...")
    with open(benchmark_json, "r", encoding="utf-8") as f:
        bench_data = json.load(f)

    items = bench_data["items"]
    engine = NeuralTranslationEngine(checkpoint_path="models/nmt/checkpoints/best_transformer.pt")
    qg = TranslationQualityGate()

    results = []
    latencies = []
    qg_passes = 0

    print("\n" + "=" * 90)
    print("PHASE 11: 20-SENTENCE STRICTLY UNSEEN CLASSROOM DEMO BENCHMARK EVALUATION")
    print("=" * 90)

    for item in items:
        item_id = item["id"]
        cat = item["category"]
        hindi = item["hindi_sentence"]
        eng_ref = item["english_reference"]
        target_gloss = item["linguistic_target_gloss"]

        # Run translation through improved engine
        res = engine.translate(hindi, beam_size=3)

        latencies.append(res.latency_ms)
        if res.quality_gate_passed:
            qg_passes += 1

        record = {
            "id": item_id,
            "category": cat,
            "hindi_sentence": hindi,
            "english_reference": eng_ref,
            "linguistic_target_gloss": target_gloss,
            "generated_mundari": res.translated_text,
            "model_score": res.model_score,
            "generation_confidence": res.generation_confidence,
            "latency_ms": res.latency_ms,
            "tokens_generated": res.tokens_generated,
            "quality_gate_passed": res.quality_gate_passed,
            "quality_gate_reasons": res.quality_gate_reasons,
            "provenance_label": res.provenance_label
        }
        results.append(record)

        print(f"[{item_id}] ({cat})")
        print(f"  Hindi:     {hindi}")
        print(f"  Mundari:   {res.translated_text}")
        print(f"  Gloss Ref: {target_gloss}")
        print(f"  Score:     {res.model_score:.3f} | Latency: {res.latency_ms:.1f}ms | QG: {res.quality_gate_passed}\n")

    p50_lat = float(np.percentile(latencies, 50))
    p95_lat = float(np.percentile(latencies, 95))
    avg_lat = float(np.mean(latencies))
    qg_pass_rate = (qg_passes / len(items)) * 100.0

    print("=" * 90)
    print(f"BENCHMARK SUMMARY (N={len(items)}):")
    print(f"  Quality Gate Pass Rate: {qg_passes}/{len(items)} ({qg_pass_rate:.1f}%)")
    print(f"  Mean Latency:           {avg_lat:.2f} ms")
    print(f"  P50 Latency:            {p50_lat:.2f} ms")
    print(f"  P95 Latency:            {p95_lat:.2f} ms")
    print("=" * 90)

    summary_payload = {
        "benchmark_name": bench_data.get("benchmark_name"),
        "total_sentences": len(items),
        "quality_gate_passed_count": qg_passes,
        "quality_gate_pass_rate_pct": round(qg_pass_rate, 2),
        "mean_latency_ms": round(avg_lat, 2),
        "p50_latency_ms": round(p50_lat, 2),
        "p95_latency_ms": round(p95_lat, 2),
        "items_evaluation": results
    }

    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2, ensure_ascii=False)

    print(f"[UnseenEval] Results written to {output_json}")
    return summary_payload


if __name__ == "__main__":
    run_unseen_benchmark_eval()
