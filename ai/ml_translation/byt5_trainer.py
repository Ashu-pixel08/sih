"""
ai/ml_translation/byt5_trainer.py
=============================================================================
SIH260042: ByT5 (Byte-Level Transformer) Fine-Tuning Pipeline
=============================================================================
Alternative fine-tuning pipeline leveraging Google's ByT5 (Apache 2.0)
byte-level sequence-to-sequence model for Hindi -> Mundari translation.
Operates directly on UTF-8 bytes, requiring zero subword vocabulary engineering,
and provides native robustness to morphological inflections and rare dialect forms.
=============================================================================
"""

import os
import sys
import json
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    DataCollatorForSeq2Seq
)
from ai.ml_translation.dataset import HindiMundariDataset


def train_byt5(
    model_id: str = "google/byt5-small",
    train_tsv: str = "data/processed/nmt/train.tsv",
    val_tsv: str = "data/processed/nmt/val.tsv",
    output_dir: str = "models/nmt/byt5_hindi_mundari",
    epochs: int = 3,
    batch_size: int = 8,
    learning_rate: float = 3e-4,
    fp16: bool = False
):
    """
    Fine-tunes ByT5-small on Hindi-Mundari parallel corpus.
    """
    os.makedirs(output_dir, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[ByT5 Trainer] Initializing {model_id} on {device}...")

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_id)

    train_dataset = HindiMundariDataset(train_tsv, tokenizer, max_source_len=128, max_target_len=128)
    val_dataset = HindiMundariDataset(val_tsv, tokenizer, max_source_len=128, max_target_len=128)

    training_args = Seq2SeqTrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=learning_rate,
        weight_decay=0.01,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        logging_steps=50,
        fp16=fp16 and torch.cuda.is_available(),
        predict_with_generate=True,
        report_to="none"
    )

    data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        tokenizer=tokenizer,
        data_collator=data_collator
    )

    print("[ByT5 Trainer] Starting training...")
    trainer.train()
    print(f"[ByT5 Trainer] Training complete. Saving model to {output_dir}...")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    print("[ByT5 Trainer] Model saved successfully.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=8)
    args = parser.parse_args()
    train_byt5(epochs=args.epochs, batch_size=args.batch_size)
