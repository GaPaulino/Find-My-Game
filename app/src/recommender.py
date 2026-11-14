import numpy as np

from embeddings import EmbeddingProvider
from models import Game


class Recommender:
    """Busca por similaridade semântica sobre um catálogo de jogos.

    Usa composição: recebe um EmbeddingProvider (Gemini em produção, Fake em
    teste) e delega a ele a geração de vetores. A classe só cuida da busca.
    """

    def __init__(self, embedder: EmbeddingProvider):
        self._embedder = embedder
        self._games: list[Game] = []
        self._matrix: np.ndarray = np.empty((0, 0), dtype=np.float32)

    def __len__(self) -> int:
        return len(self._games)

    @staticmethod
    def _normalize(m: np.ndarray) -> np.ndarray:
        """Deixa cada vetor com norma 1. Assim, produto escalar == cosseno."""
        norms = np.linalg.norm(m, axis=-1, keepdims=True)
        norms[norms == 0] = 1.0
        return m / norms

    def fit(self, games: list[Game]) -> "Recommender":
        """Carrega o catálogo. Gera embeddings só dos jogos que ainda não têm."""
        missing = [g for g in games if g.embedding is None]
        if missing:
            vectors = self._embedder.embed_documents([g.embedding_text() for g in missing])
            for game, vec in zip(missing, vectors):
                game.embedding = vec

        self._games = list(games)
        if self._games:
            self._matrix = self._normalize(np.vstack([g.embedding for g in self._games]))
        return self

    def recommend(self, query: str, top_k: int = 5) -> list[tuple[Game, float]]:
        """Retorna os top_k jogos mais parecidos com a consulta, com o score."""
        if not self._games or not query.strip():
            return []

        q = self._normalize(self._embedder.embed_query(query))
        scores = self._matrix @ q  # uma multiplicação matriz x vetor = cosseno com todos
        k = min(top_k, len(self._games))
        top = np.argsort(scores)[::-1][:k]
        return [(self._games[i], float(scores[i])) for i in top]
