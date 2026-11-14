import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from api import create_app
from config import Settings
from embeddings import FakeEmbedder
from models import Game
from recommender import Recommender
from storage import LocalStorage, S3Storage


@pytest.fixture
def client():
    games = [
        Game("Dragon Quest", "RPG medieval com dragoes e magia", ["RPG"], 80.0, 1),
        Game("Forza", "Simulador de corrida com carros esportivos", ["Racing"], 90.0, 2),
    ]
    rec = Recommender(FakeEmbedder()).fit(games)
    return TestClient(create_app(lambda: rec))


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_recommend_retorna_ordenado_com_score(client):
    r = client.post("/recommend", json={"query": "corrida de carros", "top_k": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["results"][0]["name"] == "Forza"
    assert body["results"][0]["score"] >= body["results"][1]["score"]
    assert set(body["results"][0]) == {"id", "name", "summary", "genres", "rating", "score"}


def test_top_k_padrao_e_limites(client):
    assert len(client.post("/recommend", json={"query": "magia"}).json()["results"]) == 2
    assert client.post("/recommend", json={"query": "magia", "top_k": 0}).status_code == 422
    assert client.post("/recommend", json={"query": "magia", "top_k": 99}).status_code == 422


def test_consulta_vazia_ou_so_espacos_da_422(client):
    assert client.post("/recommend", json={"query": "   "}).status_code == 422
    assert client.post("/recommend", json={}).status_code == 422


def test_catalogo_indisponivel_da_503():
    def falha():
        raise FileNotFoundError("sem parquet")

    r = TestClient(create_app(falha)).post("/recommend", json={"query": "x"})
    assert r.status_code == 503


def test_erro_do_embedder_da_502():
    class Quebrado(FakeEmbedder):
        def embed_query(self, text):
            raise RuntimeError("gemini fora do ar")

    rec = Recommender(Quebrado()).fit([Game("A", "resumo")])
    r = TestClient(create_app(lambda: rec)).post("/recommend", json={"query": "x"})
    assert r.status_code == 502


def test_settings_escolhe_storage(tmp_path):
    assert isinstance(Settings(local_data_dir=str(tmp_path)).build_storage(), LocalStorage)
    with pytest.raises(ValueError):
        Settings().build_storage()
