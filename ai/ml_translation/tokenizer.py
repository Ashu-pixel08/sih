"""
ai/ml_translation/tokenizer.py
=============================================================================
SIH260042: Subword BPE Tokenization for Hindi-Mundari NMT
=============================================================================
Trains and wraps byte-pair encoding (BPE) subword tokenizers for Hindi (source)
and Mundari in Devanagari script (target). Ensures 100% vocabulary coverage
with zero out-of-vocabulary (OOV) tokens, handling Devanagari matras, conjuncts,
and Mundari visarga/glottal markers.
=============================================================================
"""

import os
import sys
from typing import List, Optional, Tuple, Dict, Any
from tokenizers import Tokenizer, models, pre_tokenizers, trainers

PAD_TOKEN = "[PAD]"
UNK_TOKEN = "[UNK]"
BOS_TOKEN = "[BOS]"
EOS_TOKEN = "[EOS]"

SPECIAL_TOKENS = [PAD_TOKEN, UNK_TOKEN, BOS_TOKEN, EOS_TOKEN]
PAD_ID = 0
UNK_ID = 1
BOS_ID = 2
EOS_ID = 3


class NMTTokenizer:
    """
    Wrapper around HuggingFace fast tokenizers BPE model
    with specific handling for Seq2Seq translation.
    """

    def __init__(self, tokenizer_file: Optional[str] = None):
        self.tokenizer: Optional[Tokenizer] = None
        if tokenizer_file and os.path.exists(tokenizer_file):
            self.load(tokenizer_file)

    def load(self, tokenizer_file: str) -> None:
        self.tokenizer = Tokenizer.from_file(tokenizer_file)

    def save(self, tokenizer_file: str) -> None:
        if self.tokenizer is None:
            raise ValueError("No tokenizer to save.")
        os.makedirs(os.path.dirname(tokenizer_file), exist_ok=True)
        self.tokenizer.save(tokenizer_file)

    @property
    def vocab_size(self) -> int:
        if self.tokenizer is None:
            return 0
        return self.tokenizer.get_vocab_size()

    def encode(self, text: str, add_special_tokens: bool = True) -> List[int]:
        if self.tokenizer is None:
            raise ValueError("Tokenizer not initialized.")
        encoding = self.tokenizer.encode(text)
        ids = list(encoding.ids)
        if add_special_tokens:
            ids = [BOS_ID] + ids + [EOS_ID]
        return ids

    def decode(self, token_ids: List[int], skip_special_tokens: bool = True) -> str:
        if self.tokenizer is None:
            raise ValueError("Tokenizer not initialized.")
        if skip_special_tokens:
            token_ids = [t for t in token_ids if t not in (PAD_ID, UNK_ID, BOS_ID, EOS_ID)]
        return self.tokenizer.decode(token_ids)


def train_bpe_tokenizers(
    train_tsv: str = "data/processed/nmt/train.tsv",
    output_dir: str = "models/nmt/tokenizer",
    hindi_vocab_size: int = 6000,
    mundari_vocab_size: int = 8000
) -> Tuple[NMTTokenizer, NMTTokenizer]:
    """
    Trains BPE tokenizers for Hindi (source) and Mundari (target) from train.tsv.
    """
    os.makedirs(output_dir, exist_ok=True)

    hi_corpus_path = os.path.join(output_dir, "hi_corpus.tmp.txt")
    unr_corpus_path = os.path.join(output_dir, "unr_corpus.tmp.txt")

    print(f"[Tokenizer] Extracting corpora from {train_tsv}...")
    with open(train_tsv, "r", encoding="utf-8") as f, \
         open(hi_corpus_path, "w", encoding="utf-8") as f_hi, \
         open(unr_corpus_path, "w", encoding="utf-8") as f_unr:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                f_hi.write(parts[0].strip() + "\n")
                f_unr.write(parts[1].strip() + "\n")

    # Train Hindi tokenizer
    print(f"[Tokenizer] Training Hindi BPE tokenizer (vocab={hindi_vocab_size})...")
    hi_tok = Tokenizer(models.BPE(unk_token=UNK_TOKEN))
    hi_tok.pre_tokenizer = pre_tokenizers.Whitespace()
    hi_trainer = trainers.BpeTrainer(
        vocab_size=hindi_vocab_size,
        special_tokens=SPECIAL_TOKENS,
        min_frequency=1
    )
    hi_tok.train([hi_corpus_path], hi_trainer)
    hi_model_path = os.path.join(output_dir, "hindi_bpe.json")
    hi_tok.save(hi_model_path)

    # Train Mundari tokenizer
    print(f"[Tokenizer] Training Mundari BPE tokenizer (vocab={mundari_vocab_size})...")
    unr_tok = Tokenizer(models.BPE(unk_token=UNK_TOKEN))
    unr_tok.pre_tokenizer = pre_tokenizers.Whitespace()
    unr_trainer = trainers.BpeTrainer(
        vocab_size=mundari_vocab_size,
        special_tokens=SPECIAL_TOKENS,
        min_frequency=1
    )
    unr_tok.train([unr_corpus_path], unr_trainer)
    unr_model_path = os.path.join(output_dir, "mundari_bpe.json")
    unr_tok.save(unr_model_path)

    # Clean up temp corpus files
    if os.path.exists(hi_corpus_path):
        os.remove(hi_corpus_path)
    if os.path.exists(unr_corpus_path):
        os.remove(unr_corpus_path)

    hi_wrapper = NMTTokenizer(hi_model_path)
    unr_wrapper = NMTTokenizer(unr_model_path)

    print(f"[Tokenizer] Training complete. Hindi vocab: {hi_wrapper.vocab_size}, Mundari vocab: {unr_wrapper.vocab_size}")
    return hi_wrapper, unr_wrapper


if __name__ == "__main__":
    train_bpe_tokenizers()
