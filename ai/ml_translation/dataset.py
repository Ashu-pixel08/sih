"""
ai/ml_translation/dataset.py
=============================================================================
SIH260042: Neural Machine Translation Dataset Preparation & Split Management
=============================================================================
Loads the clean Hindi-Mundari parallel corpus, applies deterministic
deduplication based on normalized Hindi, ensures zero train/val/test leakage,
reserves benchmark generalization evaluation queries, and provides PyTorch
Dataset classes for training and evaluation.
=============================================================================
"""

import os
import sys
import csv
import random
from typing import List, Tuple, Dict, Any, Optional
import torch
from torch.utils.data import Dataset

from ai.translation.hindi_normalizer import normalize_hindi

# Increase csv field size limit for large text entries
try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    csv.field_size_limit(2147483647)

# Benchmark generalization test sentences explicitly reserved from training
BENCHMARK_UNSEEN_QUERIES = [
    "कैसे हैं आप लोग?",
    "आपका नाम क्या है?",
    "आज आप स्कूल आए हैं?",
    "बच्चे कहाँ हैं?",
    "हम आज पढ़ाई करेंगे।",
    "क्या आप तैयार हैं?",
    "यह कौन है?",
    "आप क्या कर रहे हैं?",
    "मैं स्कूल जा रहा हूँ।",
    "बच्चे ध्यान से सुनो।"
]


def load_and_split_corpus(
    tsv_path: str = "data/raw/translation/translation-hi-unr.tsv",
    output_dir: str = "data/processed/nmt",
    train_ratio: float = 0.85,
    val_ratio: float = 0.075,
    test_ratio: float = 0.075,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Loads raw TSV, deduplicates by normalized Hindi, excludes benchmark unseen queries
    from training, and saves deterministic train/val/test splits.
    """
    os.makedirs(output_dir, exist_ok=True)
    random.seed(seed)

    raw_pairs: List[Tuple[str, str]] = []
    with open(tsv_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                hi = parts[0].strip()
                unr = parts[1].strip()
                if hi and unr:
                    raw_pairs.append((hi, unr))

    total_raw = len(raw_pairs)

    # 1. Deduplication on normalized Hindi to prevent leakage
    seen_normalized: set = set()
    clean_pairs: List[Tuple[str, str]] = []
    duplicates = 0

    # Normalized benchmark unseen queries to strictly keep out of training
    norm_benchmark_queries = {normalize_hindi(q) for q in BENCHMARK_UNSEEN_QUERIES}

    reserved_for_test: List[Tuple[str, str]] = []

    for hi, unr in raw_pairs:
        norm_hi = normalize_hindi(hi)
        if norm_hi in seen_normalized:
            duplicates += 1
            continue
        seen_normalized.add(norm_hi)

        if norm_hi in norm_benchmark_queries:
            # If a benchmark query happens to exist in raw corpus, hold it out strictly in test
            reserved_for_test.append((hi, unr))
        else:
            clean_pairs.append((hi, unr))

    # Shuffle clean pairs deterministically
    random.shuffle(clean_pairs)

    total_clean = len(clean_pairs)
    val_count = int(total_clean * val_ratio)
    test_count = int(total_clean * test_ratio)
    train_count = total_clean - val_count - test_count

    train_pairs = clean_pairs[:train_count]
    val_pairs = clean_pairs[train_count:train_count + val_count]
    test_pairs = clean_pairs[train_count + val_count:] + reserved_for_test

    # Verify zero overlap between train and val/test
    train_norm_set = {normalize_hindi(h) for h, _ in train_pairs}
    val_norm_set = {normalize_hindi(h) for h, _ in val_pairs}
    test_norm_set = {normalize_hindi(h) for h, _ in test_pairs}

    train_val_overlap = train_norm_set.intersection(val_norm_set)
    train_test_overlap = train_norm_set.intersection(test_norm_set)

    assert len(train_val_overlap) == 0, f"Leakage detected between train and val: {len(train_val_overlap)}"
    assert len(train_test_overlap) == 0, f"Leakage detected between train and test: {len(train_test_overlap)}"

    # Save to disk
    train_file = os.path.join(output_dir, "train.tsv")
    val_file = os.path.join(output_dir, "val.tsv")
    test_file = os.path.join(output_dir, "test.tsv")

    def _write_tsv(filepath: str, pairs: List[Tuple[str, str]]):
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            for h, u in pairs:
                writer.writerow([h, u])

    _write_tsv(train_file, train_pairs)
    _write_tsv(val_file, val_pairs)
    _write_tsv(test_file, test_pairs)

    stats = {
        "total_raw_pairs": total_raw,
        "duplicates_removed": duplicates,
        "total_unique_pairs": total_clean + len(reserved_for_test),
        "train_pairs": len(train_pairs),
        "val_pairs": len(val_pairs),
        "test_pairs": len(test_pairs),
        "train_file": train_file,
        "val_file": val_file,
        "test_file": test_file,
        "train_val_leakage": len(train_val_overlap),
        "train_test_leakage": len(train_test_overlap)
    }

    return stats


class HindiMundariDataset(Dataset):
    """
    PyTorch Dataset for Seq2Seq Hindi -> Mundari translation (HuggingFace compatible).
    Handles tokenization for encoder-decoder models.
    """

    def __init__(
        self,
        tsv_path: str,
        tokenizer: Any,
        max_source_len: int = 128,
        max_target_len: int = 128,
        prefix: str = "translate Hindi to Mundari: "
    ):
        self.pairs: List[Tuple[str, str]] = []
        with open(tsv_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 2 and parts[0].strip() and parts[1].strip():
                    self.pairs.append((parts[0].strip(), parts[1].strip()))

        self.tokenizer = tokenizer
        self.max_source_len = max_source_len
        self.max_target_len = max_target_len
        self.prefix = prefix

    def __len__(self) -> int:
        return len(self.pairs)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        hi_text, unr_text = self.pairs[idx]
        src_text = (self.prefix + hi_text) if self.prefix else hi_text

        model_inputs = self.tokenizer(
            src_text,
            max_length=self.max_source_len,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )

        labels = self.tokenizer(
            unr_text,
            max_length=self.max_target_len,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        ).input_ids

        # Replace padding token id with -100 so loss ignores padding
        pad_token_id = self.tokenizer.pad_token_id if self.tokenizer.pad_token_id is not None else 0
        labels[labels == pad_token_id] = -100

        item = {
            "input_ids": model_inputs.input_ids.squeeze(0),
            "attention_mask": model_inputs.attention_mask.squeeze(0),
            "labels": labels.squeeze(0)
        }
        return item


class NativeSeq2SeqDataset(Dataset):
    """
    High-performance PyTorch Dataset using our NMTTokenizer wrappers
    with fast token ID lists.
    """

    def __init__(
        self,
        tsv_path: str,
        hi_tokenizer: Any,
        unr_tokenizer: Any,
        max_len: int = 80
    ):
        self.pairs: List[Tuple[str, str]] = []
        with open(tsv_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 2 and parts[0].strip() and parts[1].strip():
                    self.pairs.append((parts[0].strip(), parts[1].strip()))

        self.hi_tokenizer = hi_tokenizer
        self.unr_tokenizer = unr_tokenizer
        self.max_len = max_len

    def __len__(self) -> int:
        return len(self.pairs)

    def __getitem__(self, idx: int) -> Tuple[List[int], List[int]]:
        hi_text, unr_text = self.pairs[idx]
        src_ids = self.hi_tokenizer.encode(hi_text, add_special_tokens=True)[:self.max_len]
        tgt_ids = self.unr_tokenizer.encode(unr_text, add_special_tokens=True)[:self.max_len]
        return src_ids, tgt_ids


def collate_seq2seq(batch: List[Tuple[List[int], List[int]]], pad_id: int = 0) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Dynamic padding collate function for fast mini-batch training.
    Returns:
      src_padded: [batch_size, max_src_len_in_batch]
      tgt_input:  [batch_size, max_tgt_len_in_batch - 1] (BOS ... token_N)
      tgt_output: [batch_size, max_tgt_len_in_batch - 1] (token_1 ... EOS)
    """
    src_list, tgt_list = zip(*batch)

    max_src_len = max(len(s) for s in src_list)
    max_tgt_len = max(len(t) for t in tgt_list)

    batch_size = len(batch)
    src_tensor = torch.full((batch_size, max_src_len), pad_id, dtype=torch.long)
    tgt_in_tensor = torch.full((batch_size, max_tgt_len - 1), pad_id, dtype=torch.long)
    tgt_out_tensor = torch.full((batch_size, max_tgt_len - 1), pad_id, dtype=torch.long)

    for i, (s, t) in enumerate(zip(src_list, tgt_list)):
        src_tensor[i, :len(s)] = torch.tensor(s, dtype=torch.long)
        # Teacher forcing: input is [BOS, t1, ..., tn], target is [t1, ..., tn, EOS]
        tgt_in_tensor[i, :len(t) - 1] = torch.tensor(t[:-1], dtype=torch.long)
        tgt_out_tensor[i, :len(t) - 1] = torch.tensor(t[1:], dtype=torch.long)

    return src_tensor, tgt_in_tensor, tgt_out_tensor

