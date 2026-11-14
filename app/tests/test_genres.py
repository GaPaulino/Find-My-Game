import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from genres import GenreMapper


def make_mapper(tmp_path):
    f = tmp_path / "genres.json"
    f.write_text(json.dumps([{"id": 1, "name": "RPG"}, {"id": 2, "name": "Shooter"}]))
    return GenreMapper(f)


def test_map_ids_converte_e_ignora_desconhecidos(tmp_path):
    assert make_mapper(tmp_path).map_ids([1, 99, 2]) == ["RPG", "Shooter"]


def test_map_ids_aceita_none(tmp_path):
    assert make_mapper(tmp_path).map_ids(None) == []


def test_add_to_games_trata_jogo_sem_genres(tmp_path):
    games = [{"name": "A", "genres": [1]}, {"name": "B"}]
    result = make_mapper(tmp_path).add_to_games(games)
    assert result[0]["genres"] == ["RPG"]
    assert result[1]["genres"] == []


def test_arquivo_inexistente_gera_mapper_vazio(tmp_path):
    assert GenreMapper(tmp_path / "nao_existe.json").map_ids([1]) == []
