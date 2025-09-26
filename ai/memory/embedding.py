"""Utilities for generating embeddings using Hugging Face models."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Sequence

import numpy as np

from ai.core.exceptions import EngineError

try:  # pragma: no cover - runtime import guard
    import torch
    import torch.nn.functional as F
except Exception as exc:  # pragma: no cover
    raise EngineError("torch 패키지가 필요합니다. requirements.txt를 확인하세요.") from exc

try:  # pragma: no cover
    from transformers import AutoModel, AutoTokenizer
except Exception as exc:  # pragma: no cover
    raise EngineError("transformers 패키지가 필요합니다. requirements.txt를 확인하세요.") from exc


_MODEL_ENV = "QWEN3_EMBEDDING_PATH"
_DEFAULT_MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"


def _last_token_pool(last_hidden_states, attention_mask):
    left_padding = (attention_mask[:, -1].sum() == attention_mask.shape[0])
    if left_padding:
        return last_hidden_states[:, -1]
    sequence_lengths = attention_mask.sum(dim=1) - 1
    batch_indices = torch.arange(last_hidden_states.size(0), device=last_hidden_states.device)
    return last_hidden_states[batch_indices, sequence_lengths]


@dataclass
class EmbeddingBatch:
    """Hold embedding results."""

    vectors: list[list[float]]


class QwenEmbeddingModel:
    """Thin wrapper around the Qwen3 embedding model."""

    def __init__(
        self,
        *,
        model_path: str | None = None,
        max_length: int = 8192,
        instruction: str | None = None,
    ) -> None:
        model_source = model_path or os.getenv(_MODEL_ENV, _DEFAULT_MODEL_ID)

        try:
            tokenizer = AutoTokenizer.from_pretrained(model_source, trust_remote_code=True)
        except Exception as exc:
            raise EngineError(f"Qwen 토크나이저를 불러오지 못했습니다: {exc}") from exc

        if tokenizer.pad_token is None and tokenizer.eos_token:
            tokenizer.pad_token = tokenizer.eos_token
        tokenizer.padding_side = "left"

        attn_impl = os.getenv("QWEN_ATTENTION_IMPL", "eager")
        dtype_name = os.getenv("QWEN_DTYPE", "float32")
        torch_dtype = getattr(torch, dtype_name, torch.float32)

        try:
            model = AutoModel.from_pretrained(
                model_source,
                trust_remote_code=True,
                attn_implementation=attn_impl,
                dtype=torch_dtype,
            )
        except Exception as exc:
            raise EngineError(f"Qwen 임베딩 모델을 불러오지 못했습니다: {exc}") from exc

        model.eval()
        self._model = model
        self._tokenizer = tokenizer
        self._device = model.device
        self._max_length = max_length
        self._instruction = instruction
        self._embedding_size = getattr(model.config, "hidden_size", None)

    def embed(self, texts: Sequence[str]) -> EmbeddingBatch:
        if self._instruction:
            texts = [self._format_instruction(text) for text in texts]

        batch_dict = self._tokenizer(
            list(texts),
            padding=True,
            truncation=True,
            max_length=self._max_length,
            return_tensors="pt",
        )
        batch_dict = batch_dict.to(self._device)

        with torch.no_grad():
            outputs = self._model(**batch_dict)

        sentence_embeddings = _last_token_pool(outputs.last_hidden_state, batch_dict["attention_mask"])
        normalised = F.normalize(sentence_embeddings, p=2, dim=1)
        vectors = normalised.cpu().numpy().astype(np.float32)
        return EmbeddingBatch(vectors=[vec.tolist() for vec in vectors])

    def embed_single(self, text: str) -> list[float]:
        return self.embed([text]).vectors[0]

    @property
    def embedding_size(self) -> int | None:
        return self._embedding_size

    def _format_instruction(self, query: str) -> str:
        instruction = self._instruction or ""
        if instruction:
            return f"Instruct: {instruction}\nQuery:{query}"
        return query
