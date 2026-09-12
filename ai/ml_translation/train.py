"""
ai/ml_translation/train.py
=============================================================================
SIH260042: Mobile-Ready Seq2Seq Hindi -> Mundari NMT Training Pipeline
=============================================================================
Trains the neural Transformer encoder-decoder model on 15,127 clean Hindi-Mundari
parallel sentence pairs with:
  - Label-smoothed Cross Entropy loss (0.1 smoothing)
  - AdamW optimizer with warmup and cosine decay
  - Gradient clipping (norm 1.0)
  - Validation checkpointing on held-out validation set
  - Full metrics logging (train loss, val loss, perplexity)
=============================================================================
"""

import os
import sys
import time
import math
import json
import random
from typing import Dict, Any, List

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from ai.ml_translation.tokenizer import NMTTokenizer, PAD_ID, BOS_ID, EOS_ID
from ai.ml_translation.dataset import NativeSeq2SeqDataset, collate_seq2seq
from ai.ml_translation.model import Seq2SeqTransformer


def train_model(
    train_tsv: str = "data/processed/nmt/train.tsv",
    val_tsv: str = "data/processed/nmt/val.tsv",
    tokenizer_dir: str = "models/nmt/tokenizer",
    output_dir: str = "models/nmt/checkpoints",
    epochs: int = 10,
    batch_size: int = 64,
    learning_rate: float = 5e-4,
    weight_decay: float = 0.01,
    label_smoothing: float = 0.1,
    d_model: int = 256,
    nhead: int = 4,
    num_encoder_layers: int = 3,
    num_decoder_layers: int = 3,
    dim_feedforward: int = 512,
    dropout: float = 0.1,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Executes training loop with validation checkpointing.
    """
    torch.manual_seed(seed)
    random.seed(seed)
    os.makedirs(output_dir, exist_ok=True)

    # Set UTF-8 output if running on Windows
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[Training] Using compute device: {device}")

    # 1. Load tokenizers
    hi_tok_path = os.path.join(tokenizer_dir, "hindi_bpe.json")
    unr_tok_path = os.path.join(tokenizer_dir, "mundari_bpe.json")
    if not os.path.exists(hi_tok_path) or not os.path.exists(unr_tok_path):
        from ai.ml_translation.tokenizer import train_bpe_tokenizers
        hi_tokenizer, unr_tokenizer = train_bpe_tokenizers(train_tsv, tokenizer_dir)
    else:
        hi_tokenizer = NMTTokenizer(hi_tok_path)
        unr_tokenizer = NMTTokenizer(unr_tok_path)

    print(f"[Training] Hindi vocab size: {hi_tokenizer.vocab_size}, Mundari vocab size: {unr_tokenizer.vocab_size}")

    # 2. Datasets & Loaders
    train_dataset = NativeSeq2SeqDataset(train_tsv, hi_tokenizer, unr_tokenizer)
    val_dataset = NativeSeq2SeqDataset(val_tsv, hi_tokenizer, unr_tokenizer)

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        collate_fn=lambda b: collate_seq2seq(b, pad_id=PAD_ID),
        num_workers=0
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=lambda b: collate_seq2seq(b, pad_id=PAD_ID),
        num_workers=0
    )

    print(f"[Training] Train samples: {len(train_dataset)} ({len(train_loader)} batches)")
    print(f"[Training] Validation samples: {len(val_dataset)} ({len(val_loader)} batches)")

    # 3. Model Architecture
    model = Seq2SeqTransformer(
        src_vocab_size=hi_tokenizer.vocab_size,
        tgt_vocab_size=unr_tokenizer.vocab_size,
        d_model=d_model,
        nhead=nhead,
        num_encoder_layers=num_encoder_layers,
        num_decoder_layers=num_decoder_layers,
        dim_feedforward=dim_feedforward,
        dropout=dropout,
        pad_idx=PAD_ID
    ).to(device)

    total_params = model.count_parameters()
    print(f"[Training] Model parameters: {total_params:,} ({model.get_model_size_mb():.2f} MB float32)")

    # 4. Criterion & Optimizer
    criterion = nn.CrossEntropyLoss(ignore_index=PAD_ID, label_smoothing=label_smoothing)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=learning_rate,
        betas=(0.9, 0.98),
        eps=1e-9,
        weight_decay=weight_decay
    )

    # Learning rate scheduler: 1 epoch linear warmup, then cosine decay
    total_steps = epochs * len(train_loader)
    warmup_steps = len(train_loader)

    def lr_lambda(step: int) -> float:
        if step < warmup_steps:
            return float(step + 1) / float(max(1, warmup_steps))
        progress = float(step - warmup_steps) / float(max(1, total_steps - warmup_steps))
        return max(0.05, 0.5 * (1.0 + math.cos(math.pi * progress)))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    # 5. Training Loop
    best_val_loss = float("inf")
    best_checkpoint_path = os.path.join(output_dir, "best_transformer.pt")
    metrics_log_path = os.path.join(output_dir, "training_metrics.json")
    history: List[Dict[str, Any]] = []

    start_total_time = time.time()

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss_accum = 0.0
        train_tokens = 0
        epoch_start = time.time()

        for batch_idx, (src, tgt_in, tgt_out) in enumerate(train_loader):
            src = src.to(device)
            tgt_in = tgt_in.to(device)
            tgt_out = tgt_out.to(device)

            src_mask, tgt_mask, src_padding_mask, tgt_padding_mask = model.create_masks(src, tgt_in, device)

            optimizer.zero_grad()
            logits = model(
                src=src,
                tgt=tgt_in,
                src_mask=src_mask,
                tgt_mask=tgt_mask,
                src_padding_mask=src_padding_mask,
                tgt_padding_mask=tgt_padding_mask
            )

            # Flatten logits and targets for cross-entropy
            logits_flat = logits.reshape(-1, model.tgt_vocab_size)
            tgt_out_flat = tgt_out.reshape(-1)

            loss = criterion(logits_flat, tgt_out_flat)
            loss.backward()

            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            scheduler.step()

            non_pad_count = (tgt_out_flat != PAD_ID).sum().item()
            train_loss_accum += loss.item() * non_pad_count
            train_tokens += non_pad_count

        train_loss = train_loss_accum / max(1, train_tokens)
        train_ppl = math.exp(min(train_loss, 20.0))

        # Validation
        model.eval()
        val_loss_accum = 0.0
        val_tokens = 0
        with torch.no_grad():
            for src, tgt_in, tgt_out in val_loader:
                src = src.to(device)
                tgt_in = tgt_in.to(device)
                tgt_out = tgt_out.to(device)

                src_mask, tgt_mask, src_padding_mask, tgt_padding_mask = model.create_masks(src, tgt_in, device)
                logits = model(
                    src=src,
                    tgt=tgt_in,
                    src_mask=src_mask,
                    tgt_mask=tgt_mask,
                    src_padding_mask=src_padding_mask,
                    tgt_padding_mask=tgt_padding_mask
                )
                logits_flat = logits.reshape(-1, model.tgt_vocab_size)
                tgt_out_flat = tgt_out.reshape(-1)
                loss = criterion(logits_flat, tgt_out_flat)

                non_pad_count = (tgt_out_flat != PAD_ID).sum().item()
                val_loss_accum += loss.item() * non_pad_count
                val_tokens += non_pad_count

        val_loss = val_loss_accum / max(1, val_tokens)
        val_ppl = math.exp(min(val_loss, 20.0))
        epoch_sec = time.time() - epoch_start

        # Checkpoint saving
        is_best = val_loss < best_val_loss
        if is_best:
            best_val_loss = val_loss
            checkpoint = {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_loss": val_loss,
                "train_loss": train_loss,
                "config": {
                    "src_vocab_size": hi_tokenizer.vocab_size,
                    "tgt_vocab_size": unr_tokenizer.vocab_size,
                    "d_model": d_model,
                    "nhead": nhead,
                    "num_encoder_layers": num_encoder_layers,
                    "num_decoder_layers": num_decoder_layers,
                    "dim_feedforward": dim_feedforward,
                    "dropout": dropout,
                    "pad_idx": PAD_ID
                }
            }
            torch.save(checkpoint, best_checkpoint_path)

        epoch_record = {
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "train_ppl": round(train_ppl, 2),
            "val_loss": round(val_loss, 4),
            "val_ppl": round(val_ppl, 2),
            "epoch_seconds": round(epoch_sec, 2),
            "is_best": is_best
        }
        history.append(epoch_record)

        print(
            f"[Epoch {epoch:02d}/{epochs:02d}] "
            f"Train Loss: {train_loss:.4f} (PPL: {train_ppl:.1f}) | "
            f"Val Loss: {val_loss:.4f} (PPL: {val_ppl:.1f}) | "
            f"Time: {epoch_sec:.1f}s "
            f"{'(*BEST*)' if is_best else ''}"
        )

    total_training_time = time.time() - start_total_time
    print(f"\n[Training Completed] Total time: {total_training_time:.1f}s ({total_training_time/60:.2f} mins)")
    print(f"[Training] Best validation loss: {best_val_loss:.4f}")
    print(f"[Training] Best checkpoint saved to: {best_checkpoint_path}")

    # Write metrics log
    metrics_summary = {
        "model_architecture": "Transformer Encoder-Decoder (Seq2Seq)",
        "total_parameters": total_params,
        "checkpoint_file": best_checkpoint_path,
        "total_training_time_seconds": round(total_training_time, 2),
        "best_val_loss": round(best_val_loss, 4),
        "best_val_ppl": round(math.exp(min(best_val_loss, 20.0)), 2),
        "epochs": epochs,
        "batch_size": batch_size,
        "device": str(device),
        "history": history
    }
    with open(metrics_log_path, "w", encoding="utf-8") as f:
        json.dump(metrics_summary, f, indent=2)

    return metrics_summary


if __name__ == "__main__":
    train_model(epochs=10, batch_size=64)
