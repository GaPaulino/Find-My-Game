import io
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from embeddings import FakeEmbedder
from models import Game
from pipeline import IngestionPipeline
from recommender import Recommender
from sources import GameSource
from storage import LocalStorage, S3Storage, Storage


class ListSource(GameSource):
    def __init__(self, rows):
        self.rows = rows

    def fetch(self, limit):
        return self.rows[:limit]


ROWS = [
    {"id": 1, "name": "Dragon Quest", "summary": "RPG medieval com dragoes", "genres": ["RPG"], "total_rating": 80.5},
    {"id": 2, "name": "Sem Resumo", "summary": None, "genres": [], "total_rating": None},
    {"id": 3, "name": "Forza", "summary": "Corrida de carros", "genres": ["Racing"]},
]


def test_storage_abstrato_nao_instancia():
    with pytest.raises(TypeError):
        Storage()


def test_roundtrip_local_preserva_dados_e_embedding(tmp_path):
    st = LocalStorage(tmp_path)
    original = [Game("A", "resumo", ["RPG"], 70.0, 7, np.array([0.1, 0.2], dtype=np.float32)),
                Game("B")]
    st.save_games(original)
    loaded = st.load_games()
    assert loaded[0].name == "A" and loaded[0].id == 7 and loaded[0].genres == ["RPG"]
    assert loaded[0].rating == 70.0
    assert np.allclose(loaded[0].embedding, [0.1, 0.2])
    assert loaded[1].rating is None and loaded[1].embedding is None


def test_s3_storage_usa_put_e_get_object():
    class FakeS3:
        def __init__(self):
            self.objs = {}

        def put_object(self, Bucket, Key, Body):
            self.objs[(Bucket, Key)] = Body

        def get_object(self, Bucket, Key):
            return {"Body": io.BytesIO(self.objs[(Bucket, Key)])}

    st = S3Storage("meu-bucket", client=FakeS3())
    st.save_games([Game("A", "x", embedding=np.array([1.0], dtype=np.float32))])
    assert st.load_games()[0].name == "A"


def test_pipeline_descarta_sem_resumo_gera_embeddings_e_salva(tmp_path):
    st = LocalStorage(tmp_path)
    games = IngestionPipeline(ListSource(ROWS), FakeEmbedder(), st).run(limit=10)
    assert [g.name for g in games] == ["Dragon Quest", "Forza"]
    assert all(g.embedding is not None for g in games)
    assert len(st.load_games()) == 2


def test_pipeline_respeita_limit(tmp_path):
    games = IngestionPipeline(ListSource(ROWS), FakeEmbedder(), LocalStorage(tmp_path)).run(limit=1)
    assert len(games) == 1


def test_fluxo_completo_pipeline_storage_recommender(tmp_path):
    st = LocalStorage(tmp_path)
    IngestionPipeline(ListSource(ROWS), FakeEmbedder(), st).run()
    rec = Recommender(FakeEmbedder()).fit(st.load_games())
    assert rec.recommend("corrida de carros", top_k=1)[0][0].name == "Forza"
