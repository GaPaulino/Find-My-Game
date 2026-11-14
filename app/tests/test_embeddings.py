import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import embeddings
from embeddings import EmbeddingProvider, FakeEmbedder, GeminiEmbedder, cosine_similarity


def test_provider_abstrato_nao_instancia():
    with pytest.raises(TypeError):
        EmbeddingProvider()


def test_cosine_basico():
    assert cosine_similarity(np.array([1, 0]), np.array([1, 0])) == pytest.approx(1.0)
    assert cosine_similarity(np.array([1, 0]), np.array([0, 1])) == pytest.approx(0.0)
    assert cosine_similarity(np.zeros(2), np.array([1, 0])) == 0.0


def test_fake_textos_parecidos_ficam_mais_proximos():
    f = FakeEmbedder()
    rpg = f.embed_query("rpg medieval com dragoes")
    perto = f.embed_documents(["jogo de rpg medieval com dragoes e magia"])[0]
    longe = f.embed_documents(["simulador de corrida com carros esportivos"])[0]
    assert cosine_similarity(rpg, perto) > cosine_similarity(rpg, longe)


class FakeClient:
    """Imita client.models.embed_content; falha as primeiras `fail` vezes."""

    def __init__(self, fail=0):
        self.fail = fail
        self.calls = []
        self.models = self

    def embed_content(self, model, contents, config):
        self.calls.append((contents, config.task_type))
        if self.fail:
            self.fail -= 1
            raise RuntimeError("erro temporario")
        return SimpleNamespace(embeddings=[SimpleNamespace(values=[1.0, 2.0]) for _ in contents])


def test_gemini_divide_em_lotes_e_usa_task_type():
    client = FakeClient()
    g = GeminiEmbedder(client=client)
    out = g.embed_documents([f"t{i}" for i in range(250)])
    assert out.shape == (250, 2)
    assert [len(c) for c, _ in client.calls] == [100, 100, 50]
    assert {t for _, t in client.calls} == {"RETRIEVAL_DOCUMENT"}
    g.embed_query("x")
    assert client.calls[-1][1] == "RETRIEVAL_QUERY"


def test_gemini_retry_recupera(monkeypatch):
    monkeypatch.setattr(embeddings.time, "sleep", lambda s: None)
    client = FakeClient(fail=2)
    assert GeminiEmbedder(client=client).embed_query("x").shape == (2,)
    assert len(client.calls) == 3


def test_gemini_retry_esgota(monkeypatch):
    monkeypatch.setattr(embeddings.time, "sleep", lambda s: None)
    with pytest.raises(RuntimeError):
        GeminiEmbedder(client=FakeClient(fail=99), max_retries=3).embed_query("x")
