import hashlib
import logging
import os
import re
import time
from abc import ABC, abstractmethod

import numpy as np
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Contrato: qualquer classe que gere embeddings deve ter estes dois métodos.

    O resto do projeto (Recommender, pipeline) depende só deste contrato, sem
    saber se por trás está o Gemini, outro provedor ou um fake de teste.
    """

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> np.ndarray:
        """Embeddings dos jogos. Retorna matriz (len(texts), dimensão)."""

    @abstractmethod
    def embed_query(self, text: str) -> np.ndarray:
        """Embedding da consulta do usuário. Retorna vetor (dimensão,)."""


class GeminiEmbedder(EmbeddingProvider):
    """Implementação real, usando a API de embeddings do Gemini (google-genai)."""

    MAX_BATCH = 100  # limite da API por requisição

    def __init__(self, api_key: str | None = None,
                 model: str = "gemini-embedding-001",
                 max_retries: int = 5, client=None):
        self.model = model
        self.max_retries = max_retries
        if client is not None:  # permite injetar um cliente falso em testes
            self._client = client
        else:
            from google import genai
            self._client = genai.Client(api_key=api_key or os.getenv("GOOGLE_API_KEY"))

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), self.MAX_BATCH):
            batch = texts[i:i + self.MAX_BATCH]
            vectors.extend(self._embed(batch, "RETRIEVAL_DOCUMENT"))
            logger.info("Embeddings gerados: %d/%d", min(i + self.MAX_BATCH, len(texts)), len(texts))
        return np.array(vectors, dtype=np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        return np.array(self._embed([text], "RETRIEVAL_QUERY")[0], dtype=np.float32)

    def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        """Chama a API com retry e backoff exponencial (1s, 2s, 4s...)."""
        from google.genai import types

        for attempt in range(self.max_retries):
            try:
                resp = self._client.models.embed_content(
                    model=self.model,
                    contents=texts,
                    config=types.EmbedContentConfig(task_type=task_type),
                )
                return [e.values for e in resp.embeddings]
            except Exception:
                if attempt == self.max_retries - 1:
                    raise
                wait = 2 ** attempt
                logger.warning("Falha ao gerar embeddings, tentando de novo em %ss", wait, exc_info=True)
                time.sleep(wait)


class FakeEmbedder(EmbeddingProvider):
    """Embedder determinístico para testes: sem API, sem custo, sem rede.

    Usa 'bag of words com hash': textos que compartilham palavras ficam
    próximos, o suficiente para validar a lógica de busca.
    """

    def __init__(self, dim: int = 64):
        self.dim = dim

    def _vector(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        for word in re.findall(r"\w+", text.lower()):
            idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dim
            vec[idx] += 1.0
        return vec

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return np.array([self._vector(t) for t in texts], dtype=np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        return self._vector(text)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosseno entre dois vetores: 1 = mesma direção, 0 = sem relação."""
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0
