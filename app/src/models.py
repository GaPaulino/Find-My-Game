from dataclasses import dataclass, field

import numpy as np


@dataclass
class Game:
    """Um jogo do catálogo. @dataclass gera __init__, __repr__ e __eq__ sozinho."""

    name: str
    summary: str = ""
    genres: list[str] = field(default_factory=list)
    rating: float | None = None
    id: int | None = None
    embedding: np.ndarray | None = field(default=None, repr=False, compare=False)

    def embedding_text(self) -> str:
        """Texto que será transformado em vetor: nome + gêneros + resumo."""
        parts = [self.name]
        if self.genres:
            parts.append("Gêneros: " + ", ".join(self.genres))
        if self.summary:
            parts.append(self.summary)
        return ". ".join(parts)

    @classmethod
    def from_dict(cls, data: dict) -> "Game":
        """Constrói um Game a partir de um dict da IGDB (campos podem faltar)."""
        rating = data.get("total_rating")
        summary = data.get("summary")
        genres = data.get("genres")
        return cls(
            name=data.get("name", ""),
            summary=summary if isinstance(summary, str) else "",  # None/NaN -> ""
            genres=[] if genres is None else list(genres),  # aceita list ou array numpy
            rating=None if rating is None or rating != rating else float(rating),  # rating != rating => NaN
            id=data.get("id"),
        )

    def to_dict(self) -> dict:
        """Versão serializável (sem o embedding), usada nas respostas da API."""
        return {
            "id": self.id,
            "name": self.name,
            "summary": self.summary,
            "genres": self.genres,
            "rating": self.rating,
        }
