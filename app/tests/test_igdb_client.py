import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sources import IGDBClient


class Resp:
    def __init__(self, status=200, data=None):
        self.status_code = status
        self._data = data if data is not None else []

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")


class FakeSession:
    """Responde conforme uma fila de respostas e registra as chamadas."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def games(start, n):
    return [{"id": i, "name": f"g{i}"} for i in range(start, start + n)]


def client(session, **kw):
    return IGDBClient("cid", access_token="tok", session=session, min_interval=0, **kw)


def test_exige_secret_ou_token():
    with pytest.raises(ValueError):
        IGDBClient("cid")


def test_pagina_ate_atingir_o_limit():
    s = FakeSession([Resp(data=games(0, 500)), Resp(data=games(500, 200))])
    out = client(s).fetch(700)
    assert len(out) == 700
    bodies = [c[1]["data"] for c in s.calls]
    assert "limit 500; offset 0" in bodies[0]
    assert "limit 200; offset 500" in bodies[1]


def test_para_quando_catalogo_acaba():
    s = FakeSession([Resp(data=games(0, 30))])
    assert len(client(s).fetch(500)) == 30
    assert len(s.calls) == 1


def test_remove_duplicados_por_id():
    s = FakeSession([Resp(data=games(0, 3) + games(0, 2))])
    assert len(client(s).fetch(500)) == 3


def test_query_filtra_resumo_e_ordena_por_popularidade():
    s = FakeSession([Resp(data=[])])
    client(s, min_rating_count=10).fetch(5)
    body = s.calls[0][1]["data"]
    assert "summary != null" in body and "total_rating_count > 10" in body
    assert "sort total_rating_count desc" in body


def test_renova_token_no_401_e_repete():
    s = FakeSession([Resp(401), Resp(data={"access_token": "novo"}), Resp(data=games(0, 2))])
    c = IGDBClient("cid", client_secret="sec", access_token="velho", session=s, min_interval=0)
    assert len(c.fetch(500)) == 2
    assert s.calls[1][0] == IGDBClient.TOKEN_URL
    assert s.calls[2][1]["headers"]["Authorization"] == "Bearer novo"


def test_401_sem_secret_falha():
    with pytest.raises(RuntimeError):
        client(FakeSession([Resp(401)])).fetch(5)


def test_429_espera_e_tenta_de_novo(monkeypatch):
    import sources
    monkeypatch.setattr(sources.time, "sleep", lambda s: None)
    s = FakeSession([Resp(429), Resp(data=games(0, 1))])
    assert len(client(s).fetch(500)) == 1
