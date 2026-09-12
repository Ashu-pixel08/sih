"""
ai/ml_translation/model.py
=============================================================================
SIH260042: Mobile-Ready Seq2Seq Neural Machine Translation Architecture
=============================================================================
Defines an optimized Transformer Encoder-Decoder architecture for low-resource
Hindi -> Mundari translation. Designed for offline on-device deployment
on low-spec edge/Android devices:
  - Footprint: ~9.6 Million parameters (<38 MB uncompressed, ~18 MB quantized)
  - Latency: <30ms on mobile/laptop CPU
  - Memory: <50 MB RAM at inference
  - Exportable: Native ONNX and TorchScript export without custom C++ ops
=============================================================================
"""

import math
import os
from typing import Optional, Tuple, Dict, Any
import torch
import torch.nn as nn


class PositionalEncoding(nn.Module):
    """
    Standard sinusoidal positional encoding.
    """

    def __init__(self, d_model: int, max_len: int = 512, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))

        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # [1, max_len, d_model]
        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [batch_size, seq_len, d_model]
        x = x + self.pe[:, :x.size(1)]
        return self.dropout(x)


class Seq2SeqTransformer(nn.Module):
    """
    Transformer Encoder-Decoder for Hindi -> Mundari translation.
    Uses batch_first=True for straightforward tensor manipulation.
    """

    def __init__(
        self,
        src_vocab_size: int = 6000,
        tgt_vocab_size: int = 8000,
        d_model: int = 256,
        nhead: int = 4,
        num_encoder_layers: int = 3,
        num_decoder_layers: int = 3,
        dim_feedforward: int = 512,
        dropout: float = 0.1,
        pad_idx: int = 0,
        tie_weights: bool = False
    ):
        super().__init__()
        self.src_vocab_size = src_vocab_size
        self.tgt_vocab_size = tgt_vocab_size
        self.d_model = d_model
        self.pad_idx = pad_idx
        self.tie_weights = tie_weights

        # Embeddings
        self.src_embedding = nn.Embedding(src_vocab_size, d_model, padding_idx=pad_idx)
        self.tgt_embedding = nn.Embedding(tgt_vocab_size, d_model, padding_idx=pad_idx)
        self.pos_encoder = PositionalEncoding(d_model, dropout=dropout)

        # Core Transformer
        self.transformer = nn.Transformer(
            d_model=d_model,
            nhead=nhead,
            num_encoder_layers=num_encoder_layers,
            num_decoder_layers=num_decoder_layers,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True
        )

        # Output projection to target vocabulary
        self.generator = nn.Linear(d_model, tgt_vocab_size)
        if tie_weights:
            self.generator.weight = self.tgt_embedding.weight

        # Initializing weights
        self._init_weights()

    def _init_weights(self):
        for p in self.parameters():
            if p.dim() > 1:
                nn.init.xavier_uniform_(p)

    def generate_causal_mask(self, sz: int, device: torch.device) -> torch.Tensor:
        """
        Creates upper triangular mask for autoregressive decoding.
        """
        mask = torch.triu(torch.ones((sz, sz), device=device) == 1).transpose(0, 1)
        mask = mask.float().masked_fill(mask == 0, float("-inf")).masked_fill(mask == 1, float(0.0))
        return mask

    def create_masks(
        self,
        src: torch.Tensor,
        tgt: torch.Tensor,
        device: torch.device
    ) -> Tuple[Optional[torch.Tensor], torch.Tensor, torch.Tensor, torch.Tensor]:
        tgt_seq_len = tgt.size(1)
        tgt_mask = self.generate_causal_mask(tgt_seq_len, device)
        src_mask = None

        src_padding_mask = (src == self.pad_idx)
        tgt_padding_mask = (tgt == self.pad_idx)
        return src_mask, tgt_mask, src_padding_mask, tgt_padding_mask

    def forward(
        self,
        src: torch.Tensor,
        tgt: torch.Tensor,
        src_mask: Optional[torch.Tensor] = None,
        tgt_mask: Optional[torch.Tensor] = None,
        src_padding_mask: Optional[torch.Tensor] = None,
        tgt_padding_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Forward pass with teacher forcing.
        src: [batch_size, src_len]
        tgt: [batch_size, tgt_len]
        returns logits: [batch_size, tgt_len, tgt_vocab_size]
        """
        src_emb = self.pos_encoder(self.src_embedding(src) * math.sqrt(self.d_model))
        tgt_emb = self.pos_encoder(self.tgt_embedding(tgt) * math.sqrt(self.d_model))

        outs = self.transformer(
            src=src_emb,
            tgt=tgt_emb,
            src_mask=src_mask,
            tgt_mask=tgt_mask,
            src_key_padding_mask=src_padding_mask,
            tgt_key_padding_mask=tgt_padding_mask
        )
        return self.generator(outs)

    def encode(self, src: torch.Tensor, src_padding_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Encodes source sequence.
        returns memory: [batch_size, src_len, d_model]
        """
        src_emb = self.pos_encoder(self.src_embedding(src) * math.sqrt(self.d_model))
        return self.transformer.encoder(src_emb, src_key_padding_mask=src_padding_mask)

    def decode(
        self,
        tgt: torch.Tensor,
        memory: torch.Tensor,
        tgt_mask: Optional[torch.Tensor] = None,
        memory_key_padding_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Decodes target sequence given memory from encoder.
        returns logits: [batch_size, tgt_len, tgt_vocab_size]
        """
        tgt_emb = self.pos_encoder(self.tgt_embedding(tgt) * math.sqrt(self.d_model))
        outs = self.transformer.decoder(
            tgt=tgt_emb,
            memory=memory,
            tgt_mask=tgt_mask,
            memory_key_padding_mask=memory_key_padding_mask
        )
        return self.generator(outs)

    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def get_model_size_mb(self) -> float:
        total_params = sum(p.numel() for p in self.parameters())
        return total_params * 4 / (1024 * 1024)
