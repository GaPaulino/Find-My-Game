from abc import ABC, abstractmethod


class GameSource(ABC):
    """De onde vêm os jogos brutos (lista de dicts). A IGDB é uma implementação."""

    @abstractmethod
    def fetch(self, limit: int) -> list[dict]:
        """Retorna até `limit` jogos com campos id, name, summary, genres, total_rating."""
