"""
ai/ml_translation/finetune_continuation.py
=============================================================================
SIH260042: Controlled Model B Fine-Tuning Continuation
=============================================================================
Continues training from best_transformer.pt for 3 additional epochs:
  - Single controlled intervention: reduced label smoothing (0.05 vs 0.10)
    and lowered learning rate with cosine decay (2e-4 -> 5e-5).
  - Keeps exact same architecture, dataset splits, and tokenizers.
  - Logs epoch metrics and saves checkpoint to models/nmt/checkpoints/model_b.pt.
=============================================================================
"""

import os
import sys
import time
import math
import json
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from ai.ml_translation.tokenizer import NMTTokenizer, PAD_ID
from ai.ml_translation.dataset import NativeSeq2SeqDataset, collate_seq2seq
from ai.ml_translation.model import Seq2SeqTransformer


def run_continuation(
    initial_checkpoint: str = "models/nmt/checkpoints/best_transformer.pt",
    train_tsv: str = "data/processed/nmt/train.tsv",
    val_tsv: str = "data/processed/nmt/val.tsv",
    tokenizer_dir: str = "models/nmt/tokenizer",
    output_checkpoint: str = "models/nmt/checkpoints/model_b.pt",
    metrics_output: str = "models/nmt/checkpoints/model_b_metrics.json",
    additional_epochs: int = 3,
    batch_size: int = 64,
    learning_rate: float = 2e-4,
    label_smoothing: float = 0.05
):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[Model B] Initializing continuation on {device}...")

    # Load Tokenizers
    hi_tok_path = os.path.join(tokenizer_dir, "hindi_bpe.json")
    unr_tok_path = os.path.join(tokenizer_dir, "mundari_bpe.json")
    hi_tokenizer = NMTTokenizer(hi_tok_path)
    unr_tokenizer = NMTTokenizer(unr_tok_path)

    # Load Datasets
    train_dataset = NativeSeq2SeqDataset(train_tsv, hi_tokenizer, unr_tokenizer)
    val_dataset = NativeSeq2SeqDataset(val_tsv, hi_tokenizer, unr_tokenizer)

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        collate_fn=lambda b: collate_seq2seq(b, pad_id=PAD_ID)
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=lambda b: collate_seq2seq(b, pad_id=PAD_ID)
    )

    # Load Base Checkpoint
    checkpoint = torch.load(initial_checkpoint, map_location=device, weights_only=False)
    cfg = checkpoint.get("config", {})

    model = Seq2SeqTransformer(
        src_vocab_size=cfg.get("src_vocab_size", hi_tokenizer.vocab_size),
        tgt_vocab_size=cfg.get("tgt_vocab_size", unr_tokenizer.vocab_size),
        d_model=cfg.get("d_model", 256),
        nhead=cfg.get("nhead", 4),
        num_encoder_layers=cfg.get("num_encoder_layers", 3),
        num_decoder_layers=cfg.get("num_decoder_layers", 3),
        dim_feedforward=cfg.get("dim_feedforward", 512),
        dropout=cfg.get("dropout", 0.1),
        pad_idx=cfg.get("pad_idx", PAD_ID)
    ).to(device)

    model.load_state_dict(checkpoint["model_state_dict"])
    base_epoch = checkpoint.get("epoch", 10)
    base_val_loss = checkpoint.get("val_loss", 5.5359)
    print(f"[Model B] Loaded base checkpoint from epoch {base_epoch} with val_loss={base_val_loss:.4f}")

    # Criterion & Optimizer
    criterion = nn.CrossEntropyLoss(ignore_index=PAD_ID, label_smoothing=label_smoothing)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, betas=(0.9, 0.98), eps=1e-9, weight_decay=0.01)

    total_steps = additional_epochs * len(train_loader)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=total_steps, eta_min=5e-5)

    history = []
    best_val_loss = base_val_loss

    for ep in range(1, additional_epochs + 1):
        current_epoch = base_epoch + ep
        model.train()
        train_loss_accum = 0.0
        train_tokens = 0
        t0 = time.time()

        for src, tgt_in, tgt_out in train_loader:
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

            loss = criterion(logits.reshape(-1, model.tgt_vocab_size), tgt_out.reshape(-1))
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            scheduler.step()

            non_pad = (tgt_out.reshape(-1) != PAD_ID).sum().item()
            train_loss_accum += loss.item() * non_pad
            train_tokens += non_pad

        train_loss = train_loss_accum / max(1, train_tokens)

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
                loss = criterion(logits.reshape(-1, model.tgt_vocab_size), tgt_out.reshape(-1))
                non_pad = (tgt_out.reshape(-1) != PAD_ID).sum().item()
                val_loss_accum += loss.item() * non_pad
                val_tokens += non_pad

        val_loss = val_loss_accum / max(1, val_tokens)
        elapsed = time.time() - t0
        is_best = val_loss < best_val_loss

        if is_best:
            best_val_loss = val_loss
            torch.save({
                "epoch": current_epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_loss": val_loss,
                "val_ppl": math.exp(min(val_loss, 20.0)),
                "config": cfg
            }, output_checkpoint)
            print(f"[Model B] Epoch {current_epoch}: train_loss={train_loss:.4f}, val_loss={val_loss:.4f} *BEST* ({elapsed:.1f}s)")
        else:
            print(f"[Model B] Epoch {current_epoch}: train_loss={train_loss:.4f}, val_loss={val_loss:.4f} ({elapsed:.1f}s)")

        history.append({
            "epoch": current_epoch,
            "train_loss": round(train_loss, 4),
            "train_ppl": round(math.exp(min(train_loss, 20.0)), 2),
            "val_loss": round(val_loss, 4),
            "val_ppl": round(math.exp(min(val_loss, 20.0)), 2),
            "seconds": round(elapsed, 1),
            "is_best": is_best
        })

    # Save metrics
    payload = {
        "model_name": "Model B (Continued Transformer)",
        "base_checkpoint": initial_checkpoint,
        "additional_epochs": additional_epochs,
        "best_val_loss": round(best_val_loss, 4),
        "history": history
    }
    with open(metrics_output, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"[Model B] Continuation finished. Best val loss: {best_val_loss:.4f}")
    return payload


if __name__ == "__main__":
    run_continuation()
