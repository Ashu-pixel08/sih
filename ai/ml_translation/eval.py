"""
ai/ml_translation/eval.py
=============================================================================
SIH260042: Comprehensive Neural Machine Translation Evaluation Suite
=============================================================================
Evaluates the trained Hindi -> Mundari NMT model across:
  1. Held-out test split (1,334 clean pairs): SacreBLEU, ChrF++, exact match, latency
  2. 10 Benchmark Unseen Generalization queries (including 'कैसे हैं आप लोग?')
Reports raw unedited predictions, confidence metrics, and linguistic notes.
=============================================================================
"""

import os
import sys
import time
import json
from typing import List, Dict, Any

import numpy as np
import sacrebleu
from ai.ml_translation.inference import NeuralTranslationEngine
from ai.ml_translation.dataset import BENCHMARK_UNSEEN_QUERIES

BENCHMARK_EXPECTED_GLOSS = {
    "कैसे हैं आप लोग?": "How are you all? (Mundari: चिलेकान मेनाःपेआ? / ओको लेका मेनाःपेआ?)",
    "आपका नाम क्या है?": "What is your name? (Mundari: आमः नुतुम चिकनाः? / आपेआः नुतुम चिकनाः?)",
    "आज आप स्कूल आए हैं?": "Have you come to school today? (Mundari: तिशिं आम इसकुल हिजुःआकदा?)",
    "बच्चे कहाँ हैं?": "Where are the children? (Mundari: होनको ओकोरे मेनाःकोआ?)",
    "हम आज पढ़ाई करेंगे।": "We will study today. (Mundari: आबु तिशिं पढ़ाव बु एतोआ / पढ़ाव बु।) ",
    "क्या आप तैयार हैं?": "Are you ready? (Mundari: चेत् आम तय्यार मेनामा?)",
    "यह कौन है?": "Who is this? (Mundari: नेइ ओकोए ताना?)",
    "आप क्या कर रहे हैं?": "What are you doing? (Mundari: आम चिनाः चिकेयेतादा?)",
    "मैं स्कूल जा रहा हूँ।": "I am going to school. (Mundari: आइंग इसकुल ते सेनोःताना।) ",
    "बच्चे ध्यान से सुनो।": "Children, listen carefully. (Mundari: होनको ध्यान ते आयुम पे।)"
}


def run_evaluation(
    checkpoint_path: str = "models/nmt/checkpoints/best_transformer.pt",
    tokenizer_dir: str = "models/nmt/tokenizer",
    test_tsv: str = "data/processed/nmt/test.tsv",
    output_dir: str = "models/nmt/eval_results",
    max_test_samples: int = 500,
    beam_size: int = 3
) -> Dict[str, Any]:
    """
    Runs evaluation on test set and benchmark queries.
    """
    os.makedirs(output_dir, exist_ok=True)

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print(f"[Eval] Initializing NeuralTranslationEngine from {checkpoint_path}...")
    engine = NeuralTranslationEngine(checkpoint_path=checkpoint_path, tokenizer_dir=tokenizer_dir)

    # 1. Benchmark 10 Unseen Generalization Queries
    print("\n" + "=" * 80)
    print("BENCHMARK 10 UNSEEN GENERALIZATION QUERIES EVALUATION")
    print("=" * 80)

    benchmark_results: List[Dict[str, Any]] = []
    for q in BENCHMARK_UNSEEN_QUERIES:
        res = engine.translate(q, beam_size=beam_size)
        expected = BENCHMARK_EXPECTED_GLOSS.get(q, "N/A")
        record = {
            "hindi_input": q,
            "generated_mundari": res.translated_text,
            "expected_reference": expected,
            "confidence": res.confidence,
            "latency_ms": res.latency_ms,
            "translation_source": res.translation_source,
            "tokens_generated": res.tokens_generated,
            "provenance_label": res.provenance_label
        }
        benchmark_results.append(record)
        print(f"Hindi:       {q}")
        print(f"Generated:   {res.translated_text}")
        print(f"Expected:    {expected}")
        print(f"Confidence:  {res.confidence:.3f} | Latency: {res.latency_ms:.1f}ms\n")

    # 2. Test Split Evaluation (SacreBLEU & ChrF++)
    print("=" * 80)
    print(f"EVALUATING TEST SET ({test_tsv})...")
    print("=" * 80)

    test_pairs = []
    with open(test_tsv, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 2 and parts[0].strip() and parts[1].strip():
                test_pairs.append((parts[0].strip(), parts[1].strip()))

    if max_test_samples and len(test_pairs) > max_test_samples:
        test_eval_pairs = test_pairs[:max_test_samples]
    else:
        test_eval_pairs = test_pairs

    sources = [p[0] for p in test_eval_pairs]
    references = [p[1] for p in test_eval_pairs]
    hypotheses = []
    latencies = []
    exact_matches = 0

    eval_start_time = time.time()
    for i, src in enumerate(sources):
        res = engine.translate(src, beam_size=beam_size)
        hyp = res.translated_text
        hypotheses.append(hyp)
        latencies.append(res.latency_ms)
        if hyp.strip() == references[i].strip():
            exact_matches += 1

        if (i + 1) % 100 == 0 or (i + 1) == len(sources):
            print(f"[Eval] Processed {i+1}/{len(sources)} test sentences...")

    # Metrics computation
    bleu = sacrebleu.corpus_bleu(hypotheses, [[r] for r in references])
    chrf = sacrebleu.corpus_chrf(hypotheses, [[r] for r in references])
    avg_latency = float(np.mean(latencies)) if latencies else 0.0
    p50_latency = float(np.percentile(latencies, 50)) if latencies else 0.0
    p95_latency = float(np.percentile(latencies, 95)) if latencies else 0.0
    exact_match_pct = (exact_matches / max(1, len(sources))) * 100.0

    # Quality Gate pass count on test set
    qg = engine.quality_gate
    qg_passed = sum(1 for hyp, src in zip(hypotheses, sources) if qg.validate(hyp, src).is_valid)
    qg_pass_rate = (qg_passed / max(1, len(sources))) * 100.0

    print("\n" + "=" * 80)
    print("FINAL TEST SPLIT EVALUATION METRICS")
    print("=" * 80)
    print(f"Evaluated Pairs:         {len(sources)}")
    print(f"SacreBLEU Score:         {bleu.score:.2f}")
    print(f"ChrF++ Score:            {chrf.score:.2f}")
    print(f"Exact Match Percentage:  {exact_match_pct:.2f}%")
    print(f"Quality Gate Pass Rate:  {qg_passed}/{len(sources)} ({qg_pass_rate:.1f}%)")
    print(f"Average Latency:         {avg_latency:.2f} ms/sentence")
    print(f"P50 Latency:             {p50_latency:.2f} ms/sentence")
    print(f"P95 Latency:             {p95_latency:.2f} ms/sentence")
    print(f"Total Eval Duration:     {time.time() - eval_start_time:.1f}s")
    print("=" * 80)

    results_payload = {
        "test_split_size": len(test_pairs),
        "evaluated_sample_count": len(sources),
        "beam_size": beam_size,
        "sacrebleu_score": round(bleu.score, 2),
        "chrf_score": round(chrf.score, 2),
        "exact_match_pct": round(exact_match_pct, 2),
        "quality_gate_passed_count": qg_passed,
        "quality_gate_pass_rate_pct": round(qg_pass_rate, 2),
        "avg_latency_ms": round(avg_latency, 2),
        "p50_latency_ms": round(p50_latency, 2),
        "p95_latency_ms": round(p95_latency, 2),
        "benchmark_unseen_results": benchmark_results
    }

    eval_file = os.path.join(output_dir, "test_evaluation_report.json")
    with open(eval_file, "w", encoding="utf-8") as f:
        json.dump(results_payload, f, indent=2, ensure_ascii=False)

    print(f"[Eval] Full results written to {eval_file}")
    return results_payload


if __name__ == "__main__":
    run_evaluation()
