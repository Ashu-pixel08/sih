"""
ai/ml_translation/eval_model_b.py
=============================================================================
SIH260042: Evaluation of Model B on Test Split and 20 Unseen Demo Benchmark
=============================================================================
Evaluates models/nmt/checkpoints/model_b.pt:
  1. 500 test split sentences (BLEU, ChrF++, latency, QG pass rate)
  2. 20 unseen demo sentences
=============================================================================
"""

import os
import sys
import json
import time
import numpy as np
import sacrebleu

from ai.ml_translation.inference import NeuralTranslationEngine
from ai.ml_translation.quality_gate import TranslationQualityGate


def evaluate_model_b(
    checkpoint_path: str = "models/nmt/checkpoints/model_b.pt",
    test_tsv: str = "data/processed/nmt/test.tsv",
    demo_json: str = "data/benchmarks/unseen_demo_20.json",
    output_json: str = "models/nmt/eval_results/model_b_evaluation_report.json"
):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print(f"[Model B Eval] Loading engine from {checkpoint_path}...")
    engine = NeuralTranslationEngine(checkpoint_path=checkpoint_path)
    qg = engine.quality_gate

    # 1. 20 Unseen Demo Sentences
    print("\n" + "=" * 80)
    print("EVALUATING MODEL B ON 20 UNSEEN DEMO SENTENCES")
    print("=" * 80)
    with open(demo_json, "r", encoding="utf-8") as f:
        demo_data = json.load(f)

    demo_results = []
    demo_latencies = []
    demo_qg_passes = 0

    for item in demo_data["items"]:
        res = engine.translate(item["hindi_sentence"], beam_size=3)
        demo_latencies.append(res.latency_ms)
        if res.quality_gate_passed:
            demo_qg_passes += 1

        rec = {
            "id": item["id"],
            "category": item["category"],
            "hindi_sentence": item["hindi_sentence"],
            "english_reference": item["english_reference"],
            "linguistic_target_gloss": item["linguistic_target_gloss"],
            "generated_mundari": res.translated_text,
            "model_score": res.model_score,
            "latency_ms": res.latency_ms,
            "quality_gate_passed": res.quality_gate_passed,
            "quality_gate_reasons": res.quality_gate_reasons
        }
        demo_results.append(rec)
        print(f"[{item['id']}] {item['hindi_sentence']}")
        print(f"  -> {res.translated_text} (Score: {res.model_score:.3f}, Latency: {res.latency_ms:.1f}ms, QG: {res.quality_gate_passed})")

    demo_p50 = float(np.percentile(demo_latencies, 50))
    demo_p95 = float(np.percentile(demo_latencies, 95))
    demo_mean = float(np.mean(demo_latencies))

    # 2. 500 Test Split Evaluation
    print("\n" + "=" * 80)
    print("EVALUATING MODEL B ON 500 TEST SENTENCES")
    print("=" * 80)
    test_pairs = []
    with open(test_tsv, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 2 and parts[0].strip() and parts[1].strip():
                test_pairs.append((parts[0].strip(), parts[1].strip()))
            if len(test_pairs) >= 500:
                break

    sources = [p[0] for p in test_pairs]
    references = [p[1] for p in test_pairs]
    hyps_clean = []
    hyps_raw = []
    test_latencies = []

    t_start = time.time()
    for i, src in enumerate(sources):
        res = engine.translate(src, beam_size=3)
        hyps_clean.append(res.translated_text)
        test_latencies.append(res.latency_ms)

        # Raw BPE output without orthography cleaner
        tokens = engine.hi_tokenizer.encode(src)
        g_ids, _ = engine.generate_beam(tokens, beam_size=3, no_repeat_ngram_size=0)
        raw_text = engine.unr_tokenizer.decode(g_ids, skip_special_tokens=True).strip()
        hyps_raw.append(raw_text)

        if (i + 1) % 100 == 0:
            print(f"Processed {i+1}/500 test sentences...")

    bleu_clean = sacrebleu.corpus_bleu(hyps_clean, [[r] for r in references])
    chrf_clean = sacrebleu.corpus_chrf(hyps_clean, [[r] for r in references])

    bleu_raw = sacrebleu.corpus_bleu(hyps_raw, [[r] for r in references])
    chrf_raw = sacrebleu.corpus_chrf(hyps_raw, [[r] for r in references])

    test_mean_lat = float(np.mean(test_latencies))
    test_p50_lat = float(np.percentile(test_latencies, 50))
    test_p95_lat = float(np.percentile(test_latencies, 95))

    qg_passed = sum(1 for h, s in zip(hyps_clean, sources) if qg.validate(h, s).is_valid)
    qg_pass_rate = (qg_passed / len(sources)) * 100.0

    print("\n" + "=" * 80)
    print("MODEL B FINAL METRICS")
    print("=" * 80)
    print(f"Validation Loss:        5.2078 (PPL: 182.69)")
    print(f"Clean SacreBLEU (13a):  {bleu_clean.score:.2f}")
    print(f"Clean ChrF++:           {chrf_clean.score:.2f}")
    print(f"Raw SacreBLEU (13a):    {bleu_raw.score:.2f}")
    print(f"Raw ChrF++:             {chrf_raw.score:.2f}")
    print(f"Quality Gate Pass Rate: {qg_passed}/500 ({qg_pass_rate:.1f}%)")
    print(f"Test Latency: Mean={test_mean_lat:.2f}ms, P50={test_p50_lat:.2f}ms, P95={test_p95_lat:.2f}ms")
    print(f"Unseen Demo (N=20): Mean={demo_mean:.2f}ms, P50={demo_p50:.2f}ms, P95={demo_p95:.2f}ms")
    print("=" * 80)

    report = {
        "model_name": "Model B (Continued Seq2Seq Transformer)",
        "checkpoint": checkpoint_path,
        "val_loss": 5.2078,
        "val_ppl": 182.69,
        "test_eval_count": len(sources),
        "clean_sacrebleu": round(bleu_clean.score, 2),
        "clean_chrf": round(chrf_clean.score, 2),
        "raw_sacrebleu": round(bleu_raw.score, 2),
        "raw_chrf": round(chrf_raw.score, 2),
        "qg_pass_rate_pct": round(qg_pass_rate, 2),
        "test_mean_latency_ms": round(test_mean_lat, 2),
        "test_p50_latency_ms": round(test_p50_lat, 2),
        "test_p95_latency_ms": round(test_p95_lat, 2),
        "unseen_demo_mean_latency_ms": round(demo_mean, 2),
        "unseen_demo_p95_latency_ms": round(demo_p95, 2),
        "unseen_demo_results": demo_results
    }

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"[Model B Eval] Report saved to {output_json}")
    return report


if __name__ == "__main__":
    evaluate_model_b()
