import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_GENRES_FILE = Path(__file__).resolve().parent / "data" / "list_genres.json"


class GenreMapper:
    """Converte IDs de gênero da IGDB em nomes (ex.: 12 -> 'Role-playing (RPG)').

    O arquivo de gêneros é lido uma única vez, na criação do objeto, e fica
    guardado em um dicionário {id: nome} (estado da instância).
    """

    def __init__(self, genres_file: Path | str | None = None):
        path = Path(genres_file) if genres_file else DEFAULT_GENRES_FILE
        self._by_id: dict[int, str] = self._load(path)

    @staticmethod
    def _load(path: Path) -> dict[int, str]:
        if not path.exists():
            logger.warning("Arquivo de gêneros não encontrado em %s", path)
            return {}
        with open(path, encoding="utf-8") as f:
            return {g["id"]: g["name"] for g in json.load(f)}

    def map_ids(self, ids: list[int] | None) -> list[str]:
        """Devolve os nomes dos gêneros; IDs desconhecidos são ignorados."""
        return [self._by_id[i] for i in (ids or []) if i in self._by_id]

    def add_to_games(self, games: list[dict]) -> list[dict]:
        """Troca, em cada jogo, a lista de IDs em 'genres' pelos nomes."""
        for game in games:
            game["genres"] = self.map_ids(game.get("genres"))
        return games
