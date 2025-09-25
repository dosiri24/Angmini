"""Smoke test for building a FAISS index with Qwen3 embeddings."""

from __future__ import annotations

import os

import numpy as np
import pytest

torch = pytest.importorskip("torch")
transformers = pytest.importorskip("transformers")
faiss = pytest.importorskip("faiss")

from torch import Tensor  # noqa: E402  (import guarded by importorskip)
from transformers import AutoModel, AutoTokenizer  # noqa: E402  (import guarded by importorskip)

_MODEL_ENV = "QWEN3_EMBEDDING_PATH"
_DEFAULT_MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"
_MODEL_SOURCE = os.getenv(_MODEL_ENV, _DEFAULT_MODEL_ID)


def _last_token_pool(last_hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
    left_padding = (attention_mask[:, -1].sum() == attention_mask.shape[0])
    if left_padding:
        return last_hidden_states[:, -1]
    sequence_lengths = attention_mask.sum(dim=1) - 1
    batch_indices = torch.arange(last_hidden_states.size(0), device=last_hidden_states.device)
    return last_hidden_states[batch_indices, sequence_lengths]


def _instruct(task_description: str, query: str) -> str:
    return f"Instruct: {task_description}\nQuery:{query}"


@pytest.fixture(scope="session")
def qwen3_components():
    try:
        tokenizer = AutoTokenizer.from_pretrained(_MODEL_SOURCE, trust_remote_code=True)
    except OSError as exc:
        pytest.skip(f"Qwen3 토크나이저 로딩 실패 ({exc}). 모델을 다운로드 후 {_MODEL_ENV}를 설정해 주세요.")

    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None and tokenizer.eos_token:
        tokenizer.pad_token = tokenizer.eos_token

    try:
        model = AutoModel.from_pretrained(_MODEL_SOURCE, trust_remote_code=True)
    except OSError as exc:
        pytest.skip(f"Qwen3 모델 로딩 실패 ({exc}). 모델을 다운로드 후 {_MODEL_ENV}를 설정해 주세요.")

    model.eval()
    return model, tokenizer


def _embed_texts(model, tokenizer, texts: list[str]) -> np.ndarray:
    batch_dict = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=8192,
        return_tensors="pt",
    )
    batch_dict = batch_dict.to(model.device)

    with torch.no_grad():
        outputs = model(**batch_dict)

    sentence_embeddings = _last_token_pool(outputs.last_hidden_state, batch_dict["attention_mask"])
    normalised = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)
    return normalised.cpu().numpy().astype(np.float32)


def test_qwen3_embeddings_build_vector_index(qwen3_components):
    model, tokenizer = qwen3_components

    task = "Given a web search query, retrieve relevant passages that answer the query"
    queries = [
        _instruct(task, "사과 사는 가장 좋은 방법은?"),
    ]
    documents = [
        "사과는 장보기 목록에 추가하면 신선한 상태로 구매하기 좋습니다.",
        "오늘 날씨는 맑고 화창합니다.",
    ]

    combined = queries + documents
    embeddings = _embed_texts(model, tokenizer, combined)

    query_embeddings = embeddings[: len(queries)]
    doc_embeddings = embeddings[len(queries) :]

    dimension = doc_embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(doc_embeddings)

    scores, neighbours = index.search(query_embeddings, k=1)

    # 첫 번째 문서가 가장 유사해야 한다.
    assert neighbours[0][0] == 0
    assert scores[0][0] > 0.5
