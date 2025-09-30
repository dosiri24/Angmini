"""Smoke test for building a FAISS index with Qwen embeddings."""

from __future__ import annotations

import os

import numpy as np
import pytest

pytest.importorskip("torch")
pytest.importorskip("transformers")
faiss = pytest.importorskip("faiss")
pytest.importorskip("huggingface_hub")

from huggingface_hub import snapshot_download  # noqa: E402

from ai.memory.embedding import QwenEmbeddingModel

_MODEL_ENV = "QWEN3_EMBEDDING_PATH"
_DEFAULT_MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"
_MODEL_SOURCE = os.getenv(_MODEL_ENV, _DEFAULT_MODEL_ID)


def _instruct(task_description: str, query: str) -> str:
    return f"Instruct: {task_description}\nQuery:{query}"


@pytest.fixture(scope="session")
def cached_repo_path():
    try:
        return snapshot_download(repo_id=_MODEL_SOURCE)
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Qwen3 모델 다운로드에 실패했습니다: {exc}")


@pytest.fixture(scope="session")
def qwen_embedder(cached_repo_path):
    try:
        return QwenEmbeddingModel(model_path=cached_repo_path, max_length=512)
    except Exception as exc:
        pytest.skip(f"Qwen3 임베딩 모델 초기화 실패: {exc}")


def _embed_texts(embedder: QwenEmbeddingModel, texts: list[str]) -> np.ndarray:
    batch = embedder.embed(texts)
    return np.asarray(batch.vectors, dtype=np.float32)


def test_qwen3_embeddings_build_vector_index(qwen_embedder):
    task = "Given a web search query, retrieve relevant passages that answer the query"
    queries = [_instruct(task, "사과 사는 가장 좋은 방법은?")]
    documents = [
        "사과는 장보기 목록에 추가하면 신선한 상태로 구매하기 좋습니다.",
        "오늘 날씨는 맑고 화창합니다.",
    ]

    combined = queries + documents
    embeddings = _embed_texts(qwen_embedder, combined)

    query_embeddings = embeddings[: len(queries)]
    doc_embeddings = embeddings[len(queries) :]

    dimension = doc_embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(doc_embeddings)

    scores, neighbours = index.search(query_embeddings, k=1)

    assert neighbours[0][0] == 0
    assert scores[0][0] > 0.5
