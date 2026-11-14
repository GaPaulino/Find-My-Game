import logging

from embeddings import EmbeddingProvider
from genres import GenreMapper
from models import Game
from sources import GameSource
from storage import DEFAULT_KEY, Storage

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Orquestra: fonte -> gêneros -> limpeza -> embeddings -> storage.

    Não sabe COMO cada etapa funciona; só chama os colaboradores recebidos no
    construtor (injeção de dependência). Trocar IGDB por outra fonte, ou S3
    por disco, não exige mexer aqui.
    """

    def __init__(self, source: GameSource, embedder: EmbeddingProvider,
                 storage: Storage, genre_mapper: GenreMapper | None = None):
        self.source = source
        self.embedder = embedder
        self.storage = storage
        self.genre_mapper = genre_mapper

    def run(self, limit: int = 500, key: str = DEFAULT_KEY) -> list[Game]:
        raw = self.source.fetch(limit)
        if self.genre_mapper:
            raw = self.genre_mapper.add_to_games(raw)

        games = [Game.from_dict(r) for r in raw]
        # Sem resumo não há o que embedar de útil: descarta.
        games = [g for g in games if g.summary.strip()]
        logger.info("%d jogos recebidos, %d com resumo", len(raw), len(games))

        if games:
            vectors = self.embedder.embed_documents([g.embedding_text() for g in games])
            for game, vec in zip(games, vectors):
                game.embedding = vec

        self.storage.save_games(games, key)
        return games
