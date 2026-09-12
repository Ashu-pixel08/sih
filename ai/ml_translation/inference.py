"""
ai/ml_translation/inference.py
=============================================================================
SIH260042: Neural Machine Translation Inference Engine (Generative Decoding)
=============================================================================
Provides autoregressive generative decoding (Greedy Search and Beam Search)
for Hindi -> Mundari translation. Generates unseen sentences token-by-token
with:
  - Repetition suppression (sign-aware repetition penalty & n-gram blocking)
  - Devanagari Mundari orthographic cleaning & subword detokenization
  - Strict generation scoring (model_score / generation_confidence)
  - Quality gate linguistic validation (detects repetition, copying, gibberish)
  - Mandatory provenance and linguistic safety metadata
=============================================================================
"""

import os
import sys
import time
import math
import re
import unicodedata
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Tuple, Dict, Any

import torch
import torch.nn.functional as F

from ai.translation.hindi_normalizer import normalize_hindi
from ai.ml_translation.tokenizer import NMTTokenizer, PAD_ID, BOS_ID, EOS_ID, UNK_ID
from ai.ml_translation.model import Seq2SeqTransformer
from ai.ml_translation.quality_gate import TranslationQualityGate, QualityGateResult


def clean_mundari_orthography(text: str) -> str:
    """
    Cleans and detokenizes Devanagari Mundari text after subword decoding:
      1. Unicode NFC canonical normalization
      2. Attaches glottal stop / visarga markers to preceding syllables (: or ः)
      3. Re-attaches Devanagari vowel signs (matras), virama, anusvara
      4. Fixes spacing before punctuation marks (।, ?, !, etc.)
      5. Removes consecutive duplicate words across Unicode forms
      6. Collapses redundant whitespace
    """
    if not text:
        return ""

    # 1. Unicode canonical normalization (NFC)
    t = unicodedata.normalize("NFC", text)

    # 2. Attach colon/visarga glottal marker: 'मेना :' -> 'मेनाः'
    t = re.sub(r'(\S)\s*[:ः]\s*', r'\1ः ', t)

    # 3. Attach Devanagari vowel signs (matras), halant, anusvara if separated
    t = re.sub(r'\s+([\u093e-\u094c\u094d\u0902\u0903])', r'\1', t)

    # 4. Clean spaces before punctuation
    t = re.sub(r'\s+([।,?!;:\.\(\)\"\'\[\]\/])', r'\1', t)

    # 5. Deduplicate consecutive identical words
    words = t.split()
    dedup_words: List[str] = []
    for w in words:
        clean_w = re.sub(r'[।,?!;:\.\(\)\"\'\[\]\/ः]', '', w).strip()
        prev_clean = re.sub(r'[।,?!;:\.\(\)\"\'\[\]\/ः]', '', dedup_words[-1]).strip() if dedup_words else ""
        if clean_w and clean_w == prev_clean:
            continue
        dedup_words.append(w)
    t = " ".join(dedup_words)

    # 6. Normalize whitespace
    t = re.sub(r'\s+', ' ', t).strip()
    return t


@dataclass
class NeuralTranslationResult:
    translated_text: str
    source_text: str
    normalized_source: str
    model_score: float
    latency_ms: float
    confidence: float = 0.0  # Backward-compatible alias for model_score
    generation_confidence: float = 0.0  # Explicit alias
    translation_source: str = "NEURAL_MODEL"
    requires_validation: bool = True
    provenance_label: str = "AI-GENERATED — REQUIRES LINGUISTIC VALIDATION"
    tokens_generated: int = 0
    beam_size: int = 1
    model_architecture: str = "Transformer-Seq2Seq"
    quality_gate_passed: bool = True
    quality_gate_reasons: List[str] = field(default_factory=list)
    score_type: str = "TOKEN_LIKELIHOOD (geometric mean token probability; NOT translation accuracy)"

    def __post_init__(self):
        if self.confidence == 0.0 and self.model_score != 0.0:
            self.confidence = self.model_score
        if self.generation_confidence == 0.0:
            self.generation_confidence = self.model_score

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class NeuralTranslationEngine:
    """
    Production-ready Generative Translation Engine for Hindi -> Mundari.
    Loads trained Seq2Seq Transformer checkpoint and BPE tokenizers.
    Applies sign-aware repetition penalty, n-gram blocking, and quality gate.
    """

    def __init__(
        self,
        checkpoint_path: str = "models/nmt/checkpoints/best_transformer.pt",
        tokenizer_dir: str = "models/nmt/tokenizer",
        device: Optional[str] = None
    ):
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        self.checkpoint_path = checkpoint_path
        self.tokenizer_dir = tokenizer_dir

        # Load Tokenizers
        hi_tok_path = os.path.join(tokenizer_dir, "hindi_bpe.json")
        unr_tok_path = os.path.join(tokenizer_dir, "mundari_bpe.json")
        if not os.path.exists(hi_tok_path) or not os.path.exists(unr_tok_path):
            raise FileNotFoundError(f"Tokenizer files not found in {tokenizer_dir}")

        self.hi_tokenizer = NMTTokenizer(hi_tok_path)
        self.unr_tokenizer = NMTTokenizer(unr_tok_path)

        # Load Model
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Model checkpoint not found at {checkpoint_path}")

        checkpoint = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
        cfg = checkpoint.get("config", {})

        self.model = Seq2SeqTransformer(
            src_vocab_size=cfg.get("src_vocab_size", self.hi_tokenizer.vocab_size),
            tgt_vocab_size=cfg.get("tgt_vocab_size", self.unr_tokenizer.vocab_size),
            d_model=cfg.get("d_model", 256),
            nhead=cfg.get("nhead", 4),
            num_encoder_layers=cfg.get("num_encoder_layers", 3),
            num_decoder_layers=cfg.get("num_decoder_layers", 3),
            dim_feedforward=cfg.get("dim_feedforward", 512),
            dropout=cfg.get("dropout", 0.1),
            pad_idx=cfg.get("pad_idx", PAD_ID),
            tie_weights=cfg.get("tie_weights", False)
        ).to(self.device)

        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()

        self.val_loss = checkpoint.get("val_loss", 0.0)
        self.epoch = checkpoint.get("epoch", 0)

        # Initialize Linguistic Quality Gate
        self.quality_gate = TranslationQualityGate()

    @torch.no_grad()
    def generate_greedy(
        self,
        src_tokens: List[int],
        max_len: int = 50,
        repetition_penalty: float = 1.25,
        no_repeat_ngram_size: int = 2
    ) -> Tuple[List[int], float]:
        """
        Greedy autoregressive decoding with sign-aware repetition penalty and n-gram blocking.
        """
        src = torch.tensor([src_tokens], dtype=torch.long, device=self.device)
        memory = self.model.encode(src)

        ys = torch.tensor([[BOS_ID]], dtype=torch.long, device=self.device)
        log_probs: List[float] = []
        min_len = max(2, min(8, int(len(src_tokens) * 0.35)))

        for step in range(max_len):
            tgt_mask = self.model.generate_causal_mask(ys.size(1), self.device)
            out = self.model.decode(ys, memory, tgt_mask=tgt_mask)
            logits = out[:, -1, :].clone()

            # Sign-aware repetition penalty
            for prev_token in set(ys[0].tolist()):
                if prev_token not in (PAD_ID, BOS_ID, EOS_ID):
                    if logits[0, prev_token] < 0:
                        logits[0, prev_token] *= repetition_penalty
                    else:
                        logits[0, prev_token] /= repetition_penalty

            # N-gram blocking
            curr_seq = ys[0].tolist()
            if no_repeat_ngram_size > 0 and len(curr_seq) >= no_repeat_ngram_size:
                prefix = tuple(curr_seq[-(no_repeat_ngram_size - 1):])
                for i in range(len(curr_seq) - no_repeat_ngram_size + 1):
                    if tuple(curr_seq[i:i + no_repeat_ngram_size - 1]) == prefix:
                        blocked_token = curr_seq[i + no_repeat_ngram_size - 1]
                        logits[0, blocked_token] = -float('inf')

            # Minimum length constraint: suppress EOS until min_len reached
            if step < min_len:
                logits[0, EOS_ID] = -float('inf')

            probs = F.softmax(logits, dim=-1)
            next_prob, next_token_idx = torch.max(probs, dim=-1)
            next_token = next_token_idx.item()

            token_log_prob = math.log(max(next_prob.item(), 1e-12))
            log_probs.append(token_log_prob)

            if next_token == EOS_ID:
                break

            ys = torch.cat([ys, torch.tensor([[next_token]], device=self.device)], dim=1)

        # Geometric mean token confidence
        avg_log_prob = sum(log_probs) / max(1, len(log_probs))
        model_score = math.exp(max(-10.0, avg_log_prob))
        model_score = max(0.001, min(0.99, model_score))

        generated_ids = ys[0, 1:].tolist()  # strip BOS
        return generated_ids, model_score

    @torch.no_grad()
    def generate_beam(
        self,
        src_tokens: List[int],
        beam_size: int = 3,
        max_len: int = 50,
        repetition_penalty: float = 1.25,
        no_repeat_ngram_size: int = 2
    ) -> Tuple[List[int], float]:
        """
        Beam search autoregressive decoding with sign-aware penalty, n-gram blocking,
        and length normalization.
        """
        src = torch.tensor([src_tokens], dtype=torch.long, device=self.device)
        memory = self.model.encode(src)

        beams: List[Tuple[List[int], float]] = [([BOS_ID], 0.0)]
        completed_beams: List[Tuple[List[int], float]] = []
        min_len = max(2, min(8, int(len(src_tokens) * 0.35)))

        for step in range(max_len):
            new_candidates: List[Tuple[List[int], float]] = []

            for seq, score in beams:
                if seq[-1] == EOS_ID:
                    completed_beams.append((seq, score))
                    continue

                ys = torch.tensor([seq], dtype=torch.long, device=self.device)
                tgt_mask = self.model.generate_causal_mask(ys.size(1), self.device)
                out = self.model.decode(ys, memory, tgt_mask=tgt_mask)
                logits = out[:, -1, :].clone()

                # Sign-aware repetition penalty (properly penalizes negative logits)
                for prev_token in set(seq):
                    if prev_token not in (PAD_ID, BOS_ID, EOS_ID):
                        if logits[0, prev_token] < 0:
                            logits[0, prev_token] *= repetition_penalty
                        else:
                            logits[0, prev_token] /= repetition_penalty

                # N-gram repetition blocking
                if no_repeat_ngram_size > 0 and len(seq) >= no_repeat_ngram_size:
                    prefix = tuple(seq[-(no_repeat_ngram_size - 1):])
                    for i in range(len(seq) - no_repeat_ngram_size + 1):
                        if tuple(seq[i:i + no_repeat_ngram_size - 1]) == prefix:
                            blocked_token = seq[i + no_repeat_ngram_size - 1]
                            logits[0, blocked_token] = -float('inf')

                # Suppress EOS until min_len steps reached
                if step < min_len:
                    logits[0, EOS_ID] = -float('inf')

                log_probs = F.log_softmax(logits, dim=-1)
                topk_log_probs, topk_indices = torch.topk(log_probs, beam_size, dim=-1)

                for k in range(beam_size):
                    next_token = topk_indices[0, k].item()
                    next_score = score + topk_log_probs[0, k].item()
                    new_candidates.append((seq + [next_token], next_score))

            if not new_candidates:
                break

            # Rank candidates by length-normalized score
            ranked = sorted(new_candidates, key=lambda x: x[1] / (len(x[0]) ** 0.7), reverse=True)
            beams = ranked[:beam_size]

            if all(b[0][-1] == EOS_ID for b in beams):
                completed_beams.extend(beams)
                break

        if not completed_beams:
            completed_beams = beams

        best_seq, best_score = max(completed_beams, key=lambda x: x[1] / (len(x[0]) ** 0.7))

        cleaned_ids = [t for t in best_seq if t not in (BOS_ID, EOS_ID, PAD_ID)]
        avg_log_prob = best_score / max(1, len(cleaned_ids))
        model_score = math.exp(max(-10.0, avg_log_prob))
        model_score = max(0.001, min(0.99, model_score))

        return cleaned_ids, model_score

    def translate(
        self,
        hindi_text: str,
        beam_size: int = 3,
        max_len: int = 50,
        no_repeat_ngram_size: int = 2
    ) -> NeuralTranslationResult:
        """
        Translates a Hindi sentence into Mundari using the neural Seq2Seq model.
        Applies orthographic cleaning and runs the linguistic quality gate.
        """
        start_time = time.perf_counter()

        norm_hindi = normalize_hindi(hindi_text)
        src_tokens = self.hi_tokenizer.encode(norm_hindi, add_special_tokens=True)

        if beam_size > 1:
            generated_ids, model_score = self.generate_beam(
                src_tokens,
                beam_size=beam_size,
                max_len=max_len,
                no_repeat_ngram_size=no_repeat_ngram_size
            )
        else:
            generated_ids, model_score = self.generate_greedy(
                src_tokens,
                max_len=max_len,
                no_repeat_ngram_size=no_repeat_ngram_size
            )

        raw_decoded = self.unr_tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        cleaned_mundari = clean_mundari_orthography(raw_decoded)

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        # Validate with Linguistic Quality Gate
        qg_result = self.quality_gate.validate(
            translated_text=cleaned_mundari,
            source_text=hindi_text,
            model_score=model_score
        )

        return NeuralTranslationResult(
            translated_text=cleaned_mundari,
            source_text=hindi_text,
            normalized_source=norm_hindi,
            model_score=round(model_score, 3),
            confidence=round(model_score, 3),
            generation_confidence=round(model_score, 3),
            latency_ms=round(latency_ms, 2),
            translation_source="NEURAL_MODEL",
            requires_validation=True,
            provenance_label="AI-GENERATED — REQUIRES LINGUISTIC VALIDATION",
            tokens_generated=len(generated_ids),
            beam_size=beam_size,
            quality_gate_passed=qg_result.is_valid,
            quality_gate_reasons=qg_result.rejection_reasons
        )
